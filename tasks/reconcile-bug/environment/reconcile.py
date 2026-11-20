#!/usr/bin/env python3
"""Reconcile a batch of payment transactions from a CSV file."""
import json
import re
import sys
from datetime import datetime, timedelta
from decimal import Decimal

TIMESTAMP_RE = re.compile(r"([0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2})(Z|[+-][0-9]{2}:[0-9]{2})")
AMOUNT_RE = re.compile(r"[0-9]+(\.[0-9]+)?")
STATUSES = {"SUCCESS", "FAILED", "PENDING"}
EPOCH = datetime(1970, 1, 1)


def parse_timestamp(value):
    """Return seconds since the epoch in UTC, or None if invalid."""
    m = TIMESTAMP_RE.fullmatch(value)
    if not m:
        return None
    try:
        local = datetime.strptime(m.group(1), "%Y-%m-%dT%H:%M:%S")
    except ValueError:
        return None
    seconds = (local - EPOCH) // timedelta(seconds=1)
    offset = m.group(2)
    if offset == "Z":
        return seconds
    sign = 1 if offset[0] == "+" else -1
    hours, minutes = int(offset[1:3]), int(offset[4:6])
    if hours > 23 or minutes > 59:
        return None
    return seconds + sign * (hours * 3600 + minutes * 60)


def parse_row(line):
    fields = line.split(",")
    if len(fields) != 4 or any(f == "" for f in fields):
        return None
    tx_id, timestamp, amount, status = fields
    ts = parse_timestamp(timestamp)
    if ts is None or not AMOUNT_RE.fullmatch(amount) or status not in STATUSES:
        return None
    return tx_id, ts, Decimal(amount), status


def reconcile(path):
    latest = {}
    with open(path, encoding="utf-8") as f:
        next(f, None)
        for line in f:
            row = parse_row(line.rstrip("\n"))
            if row is None:
                print(f"skipping malformed row: {line!r}", file=sys.stderr)
                continue
            current = latest.get(row[0])
            if current is None or row[1] > current[1]:
                latest[row[0]] = row

    total = Decimal(0)
    valid = failed = 0
    for _, _, amount, status in latest.values():
        if status == "SUCCESS":
            total += amount
            valid += 1
        elif status == "FAILED":
            failed += 1
    return {
        "total_valid_amount": float(round(total, 2)),
        "valid_count": valid,
        "failed_count": failed,
    }


def main():
    if len(sys.argv) != 3:
        print("usage: reconcile.py <input.csv>", file=sys.stderr)
        sys.exit(2)
    print(json.dumps(reconcile(sys.argv[1])))


if __name__ == "__main__":
    main()
