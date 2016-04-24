#/bin/bash

export FIXTURE="single"

run() {
    local CHANNEL="test"
    local KEY="create-delete"
    local ORIGINAL="data1"
    local UPDATED="data2"

    create "$CHANNEL" "$KEY" "$ORIGINAL"
    assert_equal "$HTTP_STATUS" 201 $LINENO

    BACK=$(get "$CHANNEL" "$KEY")
    assert_equal "$BACK" "$ORIGINAL" $LINENO

    update "$CHANNEL" "$KEY" 1 "$UPDATED"
    assert_equal "$HTTP_STATUS" 202 $LINENO

    # The update is never syncronouos and should return 202 Accepted

    # Let's poll the key and see if we can get updated value soon
    for X in 1 2 3 4 5; do
        BACK=$(get "$CHANNEL" "$KEY")
        if [ "$BACK" == "$UPDATED" ]; then
            log  "Key is updated." OK
            break
        fi
        sleep 0.1
    done
    assert_equal "$BACK" "$UPDATED" $LINENO
}
