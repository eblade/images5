#/bin/bash

export DESCRIPTION="After subscribing, a created message should spawn an event on the hook."
export FIXTURE="single"

run() {
    local CHANNEL="test"
    local URL="http://localhost:8090/hook"
    local KEY="subscribe-create-hook"
    local DATA="testdata"
    local TOKEN1="$TOKEN"
    local TOKEN2="b"
    local SECRET1="$SECRET"
    local SECRET2="bs"
    local RESULTFILE="/tmp/hook-data"

    # Subscribing with TOKEN1
    subscribe "$CHANNEL" topic "$URL"
    assert equal "$HTTP_STATUS" 201 $LINENO

    # Set up a listener for the given hook url
    rm -f "$RESULTFILE"
    expect hook "$URL" "$DATA" "$RESULTFILE"

    # Creating a message with TOKEN2
    TOKEN="$TOKEN2"
    SECRET="$SECRET2"
    
    create "$CHANNEL" "$KEY" "$DATA"
    assert equal "$HTTP_STATUS" 201 $LINENO

    local JSON=$(expect file "$RESULTFILE")
    log JSON "$JSON"
    echo "$JSON" | assert_json \
        "json['body'] == '$DATA'" \
    || fail "Bad hook data" $LINENO
}
