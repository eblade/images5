#/bin/bash

log() {
    local KEYWORD="$1"
    local MESSAGE="$2"
    local STATUS="${3-}"

    KWSIZE=$((15-${#KEYWORD}))
    KWPAD=$(printf "%${KWSIZE}s" " ")

    if [ "$KEYWORD" == "ASSERT" ]; then
        KEYWORD="\e[35m$KEYWORD"
    elif [ "$KEYWORD" == "DESCRIPTION" ]; then
        KEYWORD="\e[34m$KEYWORD"
    elif [ "$KEYWORD" == "TEST" ]; then
        KEYWORD="\e[34m$KEYWORD"
    fi

    if [ "$STATUS" == "OK" ]; then
        STATUS="\e[32m$STATUS"
    elif [ "$STATUS" == "FAILED" ]; then
        STATUS="\e[31m$STATUS"
    elif [ "$STATUS" == "ERROR" ]; then
        STATUS="\e[31m$STATUS"
    fi

    if [ -n "$STATUS" ]; then
        STATUS="[\e[1m$STATUS\e[0m] "
    fi

    (>&2 echo -e "\e[0m:: \e[1m$KWPAD$KEYWORD \e[0m:: $STATUS$MESSAGE\e[0m")
}

assert() {
    local WHAT="$1"
    local E_PARAM_ERR=98
    local E_ASSERT_FAILED=99

    if [ -z ${4-} ]; then
        log ASSERT " $0 :: Missing LINENO" ERROR
        exit $E_PARAM_ERR
    fi

    lineno=$3

    if [ "$WHAT" == "equal" ]; then
        if [ "$2" != "$3" ]; then
            log ASSERT "$0 +$lineno :: Assertion failed:  \"$2\" == \"$3\"" FAILED
            exit $E_ASSERT_FAILED
        else
            log ASSERT "$2 == $3" OK
        fi  

    else
        log ASSERT "$0 +$lineno:: Unrecognized operator \"$1\"" ERROR
        exit $E_PARAM_ERR
    fi
}

fail() {
    local E_ASSERT_FAILED=99

    if [ -z ${2-} ]; then
        log ASSERT " $0 :: Missing LINENO" WARNING
        exit $E_PARAM_ERR
    fi

    lineno=$2

    log FAIL " $0 +$lineno :: $1" FAILED
    exit $E_ASSERT_FAILED
}

check() {
    log HEAD "/"

    exec 3>&1

    HTTP_STATUS=$(curl -X HEAD \
        --silent \
        -w "%{http_code}" -o >(cat >&3) \
        -X HEAD \
        --silent \
        "$SERVER:$PORT/"
    )
}

create() {
    local CHANNEL=$1
    local KEY=$2
    local DATA=$3

    log CREATE "$CHANNEL/$KEY \"$DATA\""

    exec 3>&1

    HTTP_STATUS=$(curl \
        --silent \
        -w "%{http_code}" -o >(cat >&3) \
        -X POST \
        --header "Client-Token: $TOKEN" \
        --header "Client-Secret: $SECRET" \
        --data "$DATA" \
        "$SERVER:$PORT/$CHANNEL/$KEY"
    )
}

update() {
    local CHANNEL=$1
    local KEY=$2
    local SOURCE_VERSION=$3
    local DATA=$4

    log UPDATE "$CHANNEL/$KEY/$SOURCE_VERSION \"$DATA\""

    exec 3>&1

    HTTP_STATUS=$(curl \
        --silent \
        -w "%{http_code}" -o >(cat >&3) \
        -X PUT \
        --header "Client-Token: $TOKEN" \
        --header "Client-Secret: $SECRET" \
        --header "Source-Version: $SOURCE_VERSION" \
        --data "$DATA" \
        "$SERVER:$PORT/$CHANNEL/$KEY"
    )
}

get() {
    local CHANNEL=$1
    local KEY=$2

    log GET "$CHANNEL/$KEY"

    exec 3>&1

    HTTP_STATUS=$(curl \
        --silent \
        -w "%{http_code}" -o >(cat >&3) \
        -X GET \
        --header "Client-Token: $TOKEN" \
        --header "Client-Secret: $SECRET" \
        "$SERVER:$PORT/$CHANNEL/$KEY"
    )
}

delete() {
    local CHANNEL=$1
    local KEY=$2
    local SOURCE_VERSION=$3

    log DELETE "$CHANNEL/$KEY/$SOURCE_VERSION"

    exec 3>&1

    HTTP_STATUS=$(curl \
        --silent \
        -w "%{http_code}" -o >(cat >&3) \
        -X DELETE \
        --header "Client-Token: $TOKEN" \
        --header "Client-Secret: $SECRET" \
        --header "Source-Version: $SOURCE_VERSION" \
        "$SERVER:$PORT/$CHANNEL/$KEY"
    )
}

subscribe() {
    local CHANNEL=$1
    local TYPE=$2
    local HOOK=$3

    log SUBSCRIBE "$CHANNEL [$TYPE] -> $HOOK"

    exec 3>&1

    HTTP_STATUS=$(curl \
        --silent \
        -w "%{http_code}" -o >(cat >&3) \
        -X POST \
        --header "Client-Token: $TOKEN" \
        --header "Client-Secret: $SECRET" \
        --header "Subscription-Type: $TYPE" \
        --header "Hook: $HOOK" \
        "$SERVER:$PORT/$CHANNEL"
    )
}

unsubscribe() {
    local CHANNEL=$1

    log UNSUBSCRIBE "$CHANNEL"

    exec 3>&1

    HTTP_STATUS=$(curl \
        --silent \
        -w "%{http_code}" -o >(cat >&3) \
        -X DELETE \
        --header "Client-Token: $TOKEN" \
        --header "Client-Secret: $SECRET" \
        "$SERVER:$PORT/$CHANNEL"
    )
}

subscriptions() {
    local CHANNEL=$1

    log SUBSCRIPTIONS "$CHANNEL"

    exec 3>&1

    HTTP_STATUS=$(curl \
        --silent \
        -w "%{http_code}" -o >(cat >&3) \
        -X GET \
        --header "Client-Token: $TOKEN" \
        --header "Client-Secret: $SECRET" \
        "$SERVER:$PORT/$CHANNEL"
    )
}

expect() {
    local WHAT="$1"

    if [ "$WHAT" == "hook" ]; then
        local URL="$2"
        local FILENAME="$3"

        hookee "$URL" "$FILENAME" &
        local PID="$!"
        KILLME="$KILLME $PID"

        sleep 0.1
        log EXPECT "HTTP hook on [$PID] $URL"

    elif [ "$WHAT" == "file" ]; then
        local FILENAME="$2"
        log EXPECT "File with name \"$FILENAME\""

        for X in 1 2 3 4 5; do
            if [ -e "$FILENAME" ]; then
                log EXPECT "$FILENAME" OK
                local DATA=$(cat "$FILENAME")
                echo "$DATA"
                rm -f "$FILENAME"
                return
            fi
            sleep 0.1
        done
        fail "File with name \"$FILENAME\" never showed up" $LINENO
        rm -f "$FILENAME"
    
    else
        fail "Don't know what \"$WHAT\"" $LINENO
        rm -f "$FILENAME"
    fi
}

start_server() {
    local CONFIG="$1"
    local HERE="$(pwd)"
    cd "../.."

    log SERVER "Starting server $CONFIG starter." OK
    if [ ! -e "testdata/$CONFIG" ]; then
        log SERVER "Server $CONFIG does not exist. Exiting." FAILED
        exit 96
    fi

    python3 -m dbmq "testdata/$CONFIG" &
    cd "$HERE"
    local PID=$!
    KILLME="$KILLME $PID"
    if [ -e "/proc/$PID" ]; then
        log SERVER "Server $CONFIG started ok (PID=$PID)." OK
    else
        log SERVER "Server $CONFIG crashed. Exiting." FAILED
        exit 97
    fi
}

wait_for_server() {
    local CONFIG="$1"

    select_server "$CONFIG"

    for X in 1 2 3 4 5; do
        sleep 0.2
        check
        if [ "$HTTP_STATUS" == "204" ]; then
            log SERVER "Server responds ok." OK
            return 0
        fi
    done
    log SERVER "Server does not respond." FAILED
    fail "Server $CONFIG does not respond." $LINENO
}

select_server() {
    local CONFIG="$1"
    
    if [ ! -e "../../testdata/$CONFIG" ]; then
        log SERVER "Server $CONFIG does not exist. Exiting." FAILED
        exit 96
    fi

    export SERVER=$(readini "../../testdata/$CONFIG" "Server" "interface")
    export PORT=$(readini "../../testdata/$CONFIG" "Server" "port")

    log SERVER "Select $SERVER:$PORT"
}

select_client() {
    local CONFIG="$1"
    
    if [ ! -e "../../testdata/$CONFIG" ]; then
        log CLIENT "Client $CONFIG does not exist. Exiting." FAILED
        exit 96
    fi

    log WORKING $(pwd)
    export TOKEN=$(readini "../../testdata/$CONFIG" "Client" "token")
    export SECRET=$(readini "../../testdata/$CONFIG" "Client" "secret")

    log CLIENT "Select $TOKEN:$SECRET"
}
