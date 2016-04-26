#/bin/bash

export DESCRIPTION="Deletion should return 204 No Content."
export FIXTURE="single"

run() {
    local CHANNEL="test"
    local KEY="create-delete"
    local ORIGINAL="data"

    create "$CHANNEL" "$KEY" "$ORIGINAL"
    assert equal "$HTTP_STATUS" 201 $LINENO

    delete "$CHANNEL" "$KEY" "1"
    assert equal "$HTTP_STATUS" 204 $LINENO

    # The deletion should result in a 204 No Content
}

