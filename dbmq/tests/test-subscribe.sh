#/bin/bash

export DESCRIPTION="Subscription should be registered and unsubscription should be unregistered."
export FIXTURE="single"

run() {
    local CHANNEL="test"
    local URL1="http://localhost:8091/hook1"
    local URL2="http://localhost:8092/hook2"
    local TOKEN1="$TOKEN"
    local TOKEN2="b"
    local SECRET1="$SECRET"
    local SECRET2="bs"

    # Subscribing with TOKEN1
    subscribe "$CHANNEL" topic "$URL1"
    assert equal "$HTTP_STATUS" 201 $LINENO

    JSON=$(subscriptions "$CHANNEL")
    log JSON "$JSON"
    echo "$JSON" | ./assert_json \
        "json['a']['token'] == '$TOKEN1'" \
        "json['a']['channel'] == '$CHANNEL'" \
        "json['a']['type'] == 'topic'" \
        "json['a']['url'] == '$URL1'" \
    || fail "Subscription list should contain a" $LINENO


    # Subscribing with TOKEN2
    TOKEN="$TOKEN2"
    SECRET="$SECRET2"
    
    subscribe "$CHANNEL" topic "$URL2"
    assert equal "$HTTP_STATUS" 201 $LINENO

    JSON=$(subscriptions "$CHANNEL")
    log JSON "$JSON"
    echo "$JSON" | ./assert_json \
        "json['a']['token'] == '$TOKEN1'" \
        "json['a']['channel'] == '$CHANNEL'" \
        "json['a']['type'] == 'topic'" \
        "json['a']['url'] == '$URL1'" \
        "json['b']['token'] == '$TOKEN2'" \
        "json['b']['channel'] == '$CHANNEL'" \
        "json['b']['type'] == 'topic'" \
        "json['b']['url'] == '$URL2'" \
    || fail "Subscription list should contain a and b" $LINENO

    # Unsubscribe with TOKEN2
    unsubscribe "$CHANNEL"
    assert equal "$HTTP_STATUS" 204 $LINENO

    JSON=$(subscriptions "$CHANNEL")
    log JSON "$JSON"
    echo "$JSON" | ./assert_json \
        "len(json) == 1" \
        "json['a']['token'] == '$TOKEN1'" \
        "json['a']['channel'] == '$CHANNEL'" \
        "json['a']['type'] == 'topic'" \
        "json['a']['url'] == '$URL1'" \
    || fail "Subscription list should only contain a" $LINENO

    # Unsubscribe with TOKEN1
    TOKEN="$TOKEN1"
    SECRET="$SECRET1"

    unsubscribe "$CHANNEL"
    assert equal "$HTTP_STATUS" 204 $LINENO

    JSON=$(subscriptions "$CHANNEL")
    log JSON "$JSON"
    echo "$JSON" | ./assert_json \
        "len(json) == 0" \
    || fail "Subscription list should be empty" $LINENO

}
