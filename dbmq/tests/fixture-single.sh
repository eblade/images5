#!/bin/bash

export SERVER="localhost"
export PORT=8080
export TOKEN="a"
export SECRET="as"

setup-fixture() {
    HERE="$(pwd)"
    cd "../.."
    python dbmq &
    FIXTURE_PID=$!
    cd "$HERE"
    if [ -e "/proc/$FIXTURE_PID" ]; then
        log FIXTURE "Fixture started ok (PID=$FIXTURE_PID)." OK
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
    teardown-fixture

}

teardown-fixture() {
    log FIXTURE "Tearing down fixture (PID=$FIXTURE_PID)."
    kill "$FIXTURE_PID"
    log FIXTURE "Tore down fixture." OK
}
