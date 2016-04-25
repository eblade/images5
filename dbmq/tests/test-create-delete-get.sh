#/bin/bash

export DESCRIPTION="Getting a message after deleting it should return 404 Not Found."
export FIXTURE="single"

run() {
    local CHANNEL="test"
    local KEY="create-delete"
    local ORIGINAL="data"

    create "$CHANNEL" "$KEY" "$ORIGINAL"
    assert_equal "$HTTP_STATUS" 201 $LINENO

    delete "$CHANNEL" "$KEY" "1"
    assert_equal "$HTTP_STATUS" 204 $LINENO

    get "$CHANNEL" "$KEY"
    assert_equal "$HTTP_STATUS" 404 $LINENO

    # The deletion should result in a 404 Not Found
}

