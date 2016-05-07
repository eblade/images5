#/bin/bash

export DESCRIPTION="Create a message, update is and get it should return the latest version on a single-node setup."
export FIXTURE="double"

run() {
    local CHANNEL="test"
    local KEY="create-delete"
    local ORIGINAL="data1"
    local UPDATED="data2"

    create "$CHANNEL" "$KEY" "$ORIGINAL"
    assert equal "$HTTP_STATUS" 201 $LINENO

    select_server "$SERVER_B"

    update "$CHANNEL" "$KEY" 1 "$UPDATED"
    assert equal "$HTTP_STATUS" 202 $LINENO

    # The update is never syncronouos and should return 202 Accepted

    BACK=$(get "$CHANNEL" "$KEY")
    assert equal "$BACK" "$UPDATED" $LINENO

    # With no replicators, the value gets approved immediately.
}
