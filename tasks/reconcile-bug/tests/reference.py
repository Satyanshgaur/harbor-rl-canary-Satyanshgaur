#!/usr/bin/env python3
"""Reconcile a batch of payment transactions from a CSV file."""
import json
import re
import sys
from datetime import datetime
from decimal import Decimal

AMOUNT_RE = re.compile(r"[0-9]+(\.[0-9]{1,2})?")
STATUSES = {"SUCCESS", "FAILED", "PENDING"}


def parse_timestamp(value):
    """Return the timestamp as an aware datetime, or None if invalid."""
    if not re.fullmatch(
        r"[0-9]{4}-[0-9]{2}-[0-9]{2}T([01][0-9]|2[0-3]):[0-5][0-9]:[0-5][0-9]"
        r"(Z|[+-]([01][0-9]|2[0-3]):[0-5][0-9])",
        value,
    ):
        return None
    try:
        ts = datetime.fromisoformat(value)
    except ValueError:
        return None
    if ts.tzinfo is None:
        return None
    return ts


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
    if len(sys.argv) != 2:
        print("usage: reconcile.py <input.csv>", file=sys.stderr)
        sys.exit(2)
    print(json.dumps(reconcile(sys.argv[1])))


if __name__ == "__main__":
    main()
