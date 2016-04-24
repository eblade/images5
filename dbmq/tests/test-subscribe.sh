#/bin/bash

export FIXTURE="single"

run() {
    local CHANNEL="test"
    local KEY="create-delete"

    subscribe "$CHANNEL" topic "http://localhost:8091/hook"
    assert_equal "$HTTP_STATUS" 200 $LINENO
}
