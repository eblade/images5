#/bin/bash

export DESCRIPTION="Create and get should return what was created."
export FIXTURE="single"

run() {
    local CHANNEL="test"
    local KEY="create-get"
    local ORIGINAL="data"

    create "$CHANNEL" "$KEY" "$ORIGINAL"
    assert equal "$HTTP_STATUS" 201 $LINENO

    local BACK=$(get "$CHANNEL" "$KEY")
    assert equal "$BACK" "$ORIGINAL" $LINENO
}

