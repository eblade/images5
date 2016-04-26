#/bin/bash

export DESCRIPTION="Update message should not be possible after deletion."
export FIXTURE="single"

run() {
    local CHANNEL="test"
    local KEY="create-delete-update"
    local ORIGINAL="data1"
    local NEWDATA="data2"

    create "$CHANNEL" "$KEY" "$ORIGINAL"
    assert equal "$HTTP_STATUS" 201 $LINENO

    delete "$CHANNEL" "$KEY" "1"
    assert equal "$HTTP_STATUS" 204 $LINENO

    update "$CHANNEL" "$KEY" "1" "$NEWDATA"
    assert equal "$HTTP_STATUS" 404 $LINENO
}

