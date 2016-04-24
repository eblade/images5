#/bin/bash

export FIXTURE="single"

run() {
    local CHANNEL="test"
    local KEY="create-delete"
    local ORIGINAL="data1"
    local UPDATED="data2"

    create "$CHANNEL" "$KEY" "$ORIGINAL"
    assert_equal "$HTTP_STATUS" 201 $LINENO

    update "$CHANNEL" "$KEY" 1 "$UPDATED"
    assert_equal "$HTTP_STATUS" 202 $LINENO

    # The update is never syncronouos and should return 202 Accepted

    BACK=$(get "$CHANNEL" "$KEY")
    assert_equal "$BACK" "$UPDATED" $LINENO

    # With no replicators, the value gets approved immediately.
}
