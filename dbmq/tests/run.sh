#!/bin/bash

set -u

TEST="$1"

source "utils.sh"

FIXTURE=""
source "$TEST"

if [ -n "$FIXTURE" ]; then
    FIXTURE="fixture-${FIXTURE}.sh"
    source "$FIXTURE"
    
    log FIXTURE "Setting up fixture ${FIXTURE}..."
    setup-fixture
    log FIXTURE "Done setting up fixture ${FIXTURE}." OK
    trap teardown-fixture EXIT
fi

log RUN "Running test ${TEST}..."
run
log RUN "Done with test ${TEST}." OK

exit 0
