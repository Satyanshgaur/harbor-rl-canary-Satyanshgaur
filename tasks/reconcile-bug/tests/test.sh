#!/bin/bash
# No set -e: every step must run and a reward must always be written.

LOG_DIR=/logs/verifier
mkdir -p "$LOG_DIR"
echo 0.00 > "$LOG_DIR/reward.txt"

# Fixtures, reference and generator stay unreadable to the candidate.
chmod -R go-rwx /tests

PY="python3 -I -S"
AS_NOBODY="setpriv --reuid=65534 --regid=65534 --clear-groups"

declare -A WEIGHT=([1]=20 [2]=30 [3]=50)
declare -A EARNED=([1]=0 [2]=0 [3]=0)

work=$(mktemp -d)      # candidate script and inputs, readable by nobody
results=$(mktemp -d)   # expected and actual outputs, root only
chmod 755 "$work"
chmod 700 "$results"
cd "$work"

seed=$(od -An -N4 -tu4 /dev/urandom | tr -d ' ')
echo "seed: $seed"

if [ -f /app/reconcile.py ] && [ ! -L /app/reconcile.py ]; then
    cp /app/reconcile.py "$work/reconcile.py"

    $PY /tests/gen.py "$work" "$seed" || echo "ERROR: gen.py failed"
    for g in 1 2 3; do
        cp "/tests/case$g.csv" "$work/"
        cp "/tests/case$g.expected.json" "$results/"
    done
    chmod 644 "$work"/*

    for f in "$work"/group*_random*.csv; do
        name=$(basename "$f" .csv)
        if ! timeout 10 $PY /tests/reference.py "$f" > "$results/$name.expected.json" 2>/dev/null; then
            echo "ERROR: reference.py failed on $name.csv"
            rm -f "$results/$name.expected.json"
        fi
    done

    for g in 1 2 3; do
        group_ok=1
        for name in "case$g" "group${g}_random"{1..5}; do
            label="group$g $name"
            if [ ! -f "$results/$name.expected.json" ]; then
                echo "$label: FAIL (no expected output)"
                group_ok=0
                continue
            fi
            timeout 10 $AS_NOBODY $PY "$work/reconcile.py" "$work/$name.csv" \
                > "$results/$name.out.json" 2>/dev/null
            status=$?
            if [ "$status" -ne 0 ]; then
                echo "$label: FAIL (reconcile.py exited with code $status)"
                group_ok=0
                continue
            fi
            if reason=$($PY /tests/compare.py "$results/$name.out.json" "$results/$name.expected.json" 2>&1 >/dev/null); then
                echo "$label: PASS"
            else
                echo "$label: FAIL ($reason)"
                group_ok=0
            fi
        done
        if [ "$group_ok" -eq 1 ]; then
            EARNED[$g]=${WEIGHT[$g]}
        fi
    done

    # Kill anything the candidate left running in the background.
    $AS_NOBODY $PY -c 'import os, signal; os.kill(-1, signal.SIGKILL)' 2>/dev/null
else
    echo "FAIL: /app/reconcile.py is missing or not a regular file"
fi

cd /
rm -rf "$work" "$results"

points=0
echo "points:"
for g in 1 2 3; do
    echo "  group$g: ${EARNED[$g]}/${WEIGHT[$g]}"
    points=$((points + EARNED[$g]))
done
echo "  total: $points/100"

reward=$(printf "%d.%02d" $((points / 100)) $((points % 100)))
echo "reward: $reward"
echo "$reward" > "$LOG_DIR/reward.txt"

rm -f "$LOG_DIR/reward.json"
