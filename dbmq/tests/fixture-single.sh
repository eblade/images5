#!/bin/bash

export SERVER="localhost"
export PORT=8080
export TOKEN="a"
export SECRET="as"

setup-fixture() {
    HERE="$(pwd)"
    cd "../.."
    python dbmq &
    local PID=$!
    KILLME="$KILLME $PID"
    cd "$HERE"
    if [ -e "/proc/$PID" ]; then
        log FIXTURE "Fixture started ok (PID=$PID)." OK
    else
        log FIXTURE "Fixture crashed. Exiting." FAILED
        exit 97
    fi

    for X in 1 2 3 4 5; do
        sleep 0.2
        check
        if [ "$HTTP_STATUS" == "204" ]; then
            log FIXTURE "Fixture responds ok." OK
            return 0
        fi
    done
    log FIXTURE "Fixture does not respond." FAILED
    kill $PID
}
