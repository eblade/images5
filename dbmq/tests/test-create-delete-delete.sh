#/bin/bash

export DESCRIPTION="Deleting a deleted message should retuen 404 Not Found."
export FIXTURE="single"

run() {
    local CHANNEL="test"
    local KEY="create-delete-delete"
    local ORIGINAL="data"

    create "$CHANNEL" "$KEY" "$ORIGINAL"
    assert_equal "$HTTP_STATUS" 201 $LINENO

    delete "$CHANNEL" "$KEY" "1"
    assert_equal "$HTTP_STATUS" 204 $LINENO

    delete "$CHANNEL" "$KEY" "1"
    assert_equal "$HTTP_STATUS" 404 $LINENO
}

