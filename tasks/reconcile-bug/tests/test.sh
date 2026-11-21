#!/bin/bash
# No set -e: every case must run and a reward must always be written.

LOG_DIR=/logs/verifier
mkdir -p "$LOG_DIR"
echo 0.0 > "$LOG_DIR/reward.txt"

declare -A WEIGHT=([case1]=20 [case2]=30 [case3]=50)
declare -A EARNED=()

out=$(mktemp)
points=0

for case in case1 case2 case3; do
    EARNED[$case]=0
    timeout 10 python3 /app/reconcile.py "/tests/$case.csv" > "$out" 2>/dev/null
    status=$?
    if [ "$status" -ne 0 ]; then
        echo "$case: FAIL (reconcile.py exited with code $status)"
        continue
    fi
    if reason=$(python3 /tests/compare.py "$out" "/tests/$case.expected.json" 2>&1 >/dev/null); then
        echo "$case: PASS"
        EARNED[$case]=${WEIGHT[$case]}
        points=$((points + WEIGHT[$case]))
    else
        echo "$case: FAIL ($reason)"
    fi
done

rm -f "$out"

echo "points:"
for case in case1 case2 case3; do
    echo "  $case: ${EARNED[$case]}/${WEIGHT[$case]}"
done
echo "  total: $points/100"

reward=$(printf "%d.%02d" $((points / 100)) $((points % 100)))
echo "reward: $reward"
echo "$reward" > "$LOG_DIR/reward.txt"

rm -f "$LOG_DIR/reward.json"
