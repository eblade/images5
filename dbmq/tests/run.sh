#!/bin/bash

set -u

TEST="$1"

source "utils.sh"

FIXTURE=
DESCRIPTION=
KILLME=""
source "$TEST"

log TEST "$TEST"
log DESCRIPTION "$DESCRIPTION"

if [ -n "$FIXTURE" ]; then
    FIXTURE="fixture-${FIXTURE}.sh"
    source "$FIXTURE"
    
    log FIXTURE "Setting up fixture ${FIXTURE}..."
    PATH=".:$PATH" setup-fixture
    log FIXTURE "Done setting up fixture ${FIXTURE}." OK
fi

teardown() {
    log TEARDOWN "Tearing down [$KILLME ]."
    kill $KILLME
    log TEARDOWN "Tore down." OK
}

trap teardown EXIT

log TEST "Running test ${TEST}..."
PATH=".:$PATH" run
log TEST "Done with test ${TEST}." OK

exit 0
