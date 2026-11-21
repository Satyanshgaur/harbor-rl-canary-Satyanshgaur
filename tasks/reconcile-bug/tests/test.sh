#!/bin/bash
# No set -e: every case must run and a reward must always be written.

LOG_DIR=/logs/verifier
mkdir -p "$LOG_DIR"
echo 0.0 > "$LOG_DIR/reward.txt"

out=$(mktemp)
passed=0

for case in case1 case2 case3; do
    timeout 10 python3 /app/reconcile.py "/tests/$case.csv" > "$out" 2>/dev/null
    status=$?
    if [ "$status" -ne 0 ]; then
        echo "$case: FAIL (reconcile.py exited with code $status)"
        continue
    fi
    if reason=$(python3 /tests/compare.py "$out" "/tests/$case.expected.json" 2>&1 >/dev/null); then
        echo "$case: PASS"
        passed=$((passed + 1))
    else
        echo "$case: FAIL ($reason)"
    fi
done

rm -f "$out"

echo "$passed/3 cases passed"
if [ "$passed" -eq 3 ]; then
    echo 1.0 > "$LOG_DIR/reward.txt"
fi

rm -f "$LOG_DIR/reward.json"
