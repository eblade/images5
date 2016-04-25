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
    fi

    if [ -n "$STATUS" ]; then
        STATUS="[\e[1m$STATUS\e[0m] "
    fi

    (>&2 echo -e "\e[0m:: \e[1m$KEYWORD$KWPAD \e[0m:: $STATUS$MESSAGE\e[0m")
}

assert_equal() {
    local E_PARAM_ERR=98
    local E_ASSERT_FAILED=99

    if [ -z ${3-} ]; then
        log ASSERT " $0 :: Missing LINENO" WARNING
        return $E_PARAM_ERR
    fi

    lineno=$3

    if [ "$1" != "$2" ]; then
        log ASSERT "$0 +$lineno :: Assertion failed:  \"$1\" == \"$2\"" FAILED
        exit $E_ASSERT_FAILED
    else
        log ASSERT "$1 == $2" OK
    fi  
}

fail() {
    local E_ASSERT_FAILED=99

    if [ -z ${2-} ]; then
        log ASSERT " $0 :: Missing LINENO" WARNING
        return $E_PARAM_ERR
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
        --header "Client-Token: $TOKEN" \
        --header "Client-Secret: $SECRET" \
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

    log DELETE "$CHANNEL/$KEY"

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
