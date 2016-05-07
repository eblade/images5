#/bin/bash

export DESCRIPTION="Several messages are created and updated on the same channel."
export FIXTURE="single"

run() {
    local CHANNEL="test"
    local URL="http://localhost:8090/hook"
    local KEY1="key1"
    local KEY2="key2"
    local KEY3="key3"
    local DATA1="testdata1"
    local DATA2="testdata2"
    local DATA3="testdata3"
    local DATA4="testdata4"
    local DATA5="testdata5"
    local DATA6="testdata6"
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
    expect hook "$URL" "$RESULTFILE"

    # Creating a message with TOKEN2
    TOKEN="$TOKEN2"
    SECRET="$SECRET2"
    
    create "$CHANNEL" "$KEY1" "$DATA1"
    assert equal "$HTTP_STATUS" 201 $LINENO

    local JSON=$(expect file "$RESULTFILE")
    log JSON "$JSON"
    echo "$JSON" | assert_json \
        "json['headers']['Event-Type'] == 'create'" \
        "json['headers']['Key'] == '$KEY1'" \
        "json['body'] == '$DATA1'" \
    || fail "Bad hook data" $LINENO

    # Creating another message with TOKEN2
    TOKEN="$TOKEN2"
    SECRET="$SECRET2"
    
    create "$CHANNEL" "$KEY2" "$DATA2"
    assert equal "$HTTP_STATUS" 201 $LINENO

    local JSON=$(expect file "$RESULTFILE")
    log JSON "$JSON"
    echo "$JSON" | assert_json \
        "json['headers']['Event-Type'] == 'create'" \
        "json['headers']['Key'] == '$KEY2'" \
        "json['body'] == '$DATA2'" \
    || fail "Bad hook data" $LINENO

    # Creating a third message with TOKEN2
    TOKEN="$TOKEN2"
    SECRET="$SECRET2"
    
    create "$CHANNEL" "$KEY3" "$DATA3"
    assert equal "$HTTP_STATUS" 201 $LINENO

    local JSON=$(expect file "$RESULTFILE")
    log JSON "$JSON"
    echo "$JSON" | assert_json \
        "json['headers']['Event-Type'] == 'create'" \
        "json['headers']['Key'] == '$KEY3'" \
        "json['body'] == '$DATA3'" \
    || fail "Bad hook data" $LINENO

    # Updating the third message with TOKEN1
    TOKEN="$TOKEN1"
    SECRET="$SECRET1"
    
    update "$CHANNEL" "$KEY3" 1 "$DATA6"
    assert equal "$HTTP_STATUS" 202 $LINENO

    local JSON=$(expect file "$RESULTFILE")
    log JSON "$JSON"
    echo "$JSON" | assert_json \
        "json['headers']['Event-Type'] == 'update'" \
        "json['headers']['Key'] == '$KEY3'" \
        "json['body'] == '$DATA6'" \
    || fail "Bad hook data" $LINENO

    # Updating the second message with TOKEN1
    TOKEN="$TOKEN1"
    SECRET="$SECRET1"
    
    update "$CHANNEL" "$KEY2" 1 "$DATA5"
    assert equal "$HTTP_STATUS" 202 $LINENO

    local JSON=$(expect file "$RESULTFILE")
    log JSON "$JSON"
    echo "$JSON" | assert_json \
        "json['headers']['Event-Type'] == 'update'" \
        "json['headers']['Key'] == '$KEY2'" \
        "json['body'] == '$DATA5'" \
    || fail "Bad hook data" $LINENO

    # Updating the first message with TOKEN1
    TOKEN="$TOKEN1"
    SECRET="$SECRET1"
    
    update "$CHANNEL" "$KEY1" 1 "$DATA4"
    assert equal "$HTTP_STATUS" 202 $LINENO

    local JSON=$(expect file "$RESULTFILE")
    log JSON "$JSON"
    echo "$JSON" | assert_json \
        "json['headers']['Event-Type'] == 'update'" \
        "json['headers']['Key'] == '$KEY1'" \
        "json['body'] == '$DATA4'" \
    || fail "Bad hook data" $LINENO

    # Delete the first message with TOKEN2
    TOKEN="$TOKEN2"
    SECRET="$SECRET2"
    
    delete "$CHANNEL" "$KEY1" 2
    assert equal "$HTTP_STATUS" 204 $LINENO

    local JSON=$(expect file "$RESULTFILE")
    log JSON "$JSON"
    echo "$JSON" | assert_json \
        "json['headers']['Event-Type'] == 'delete'" \
        "json['headers']['Key'] == '$KEY1'" \
    || fail "Bad hook data" $LINENO
}
