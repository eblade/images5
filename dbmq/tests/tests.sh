#!/bin/bash

FILTER="$1"

echo "Test run $(date), filter was '$FILTER'" > report.txt
echo >> report.txt

TESTS_COUNT=0
TESTS_PASSED=0
TESTS_FAILED=0
TESTS_SKIPPED=0

for TEST in test-*; do
    if $(echo "$TEST" | grep --quiet "$FILTER"); then
        TESTS_COUNT=$(($TESTS_COUNT+1))
        ./run.sh $TEST
        if [ $? == 0 ]; then
            echo "PASS $TEST" >> report.txt
            TESTS_PASSED=$(($TESTS_PASSED+1))
        else
            echo "FAIL $TEST" >> report.txt
            TESTS_FAILED=$(($TESTS_FAILED+1))
        fi
    else
        #echo "SKIP $TEST" >> report.txt
        TESTS_SKIPPED=$(($TESTS_SKIPPED+1))
    fi
done

echo >> report.txt
echo "Ran $TESTS_COUNT tests. $TESTS_PASSED passed, $TESTS_FAILED failed and $TESTS_SKIPPED were skipped." >> report.txt

echo
cat report.txt
