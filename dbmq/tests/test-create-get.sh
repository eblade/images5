#/bin/bash

export FIXTURE="single"

run() {
    local CHANNEL="test"
    local KEY="create-get"
    local ORIGINAL="data"

    create "$CHANNEL" "$KEY" "$ORIGINAL"
    assert_equal "$HTTP_STATUS" 201 $LINENO

    local BACK=$(get "$CHANNEL" "$KEY")
    assert_equal "$BACK" "$ORIGINAL" $LINENO
}

