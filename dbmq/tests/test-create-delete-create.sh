#/bin/bash

export DESCRIPTION="Creating a message with same key as a deleted message should be possible."
export FIXTURE="single"

run() {
    local CHANNEL="test"
    local KEY="create-delete-create"
    local ORIGINAL="data1"
    local NEWDATA="data2"

    create "$CHANNEL" "$KEY" "$ORIGINAL"
    assert equal "$HTTP_STATUS" 201 $LINENO

    delete "$CHANNEL" "$KEY" "1"
    assert equal "$HTTP_STATUS" 204 $LINENO

    # The deletion should result in a 204 No Content

    create "$CHANNEL" "$KEY" "$ORIGINAL"
    assert equal "$HTTP_STATUS" 201 $LINENO

}

