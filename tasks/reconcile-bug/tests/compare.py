#!/usr/bin/env python3
"""Compare reconcile.py output against an expected JSON file.

Usage: compare.py <output.json> <expected.json>
Exits 0 on match, 1 otherwise, with the reason on stderr.
"""
import json
import math
import sys

TOLERANCE = 0.005
COUNT_KEYS = ("valid_count", "failed_count")
TOTAL_KEY = "total_valid_amount"


def fail(reason):
    print(reason, file=sys.stderr)
    sys.exit(1)


def is_int(value):
    return type(value) is int


def is_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def main():
    if len(sys.argv) != 3:
        fail("usage: compare.py <output.json> <expected.json>")

    with open(sys.argv[2], encoding="utf-8") as f:
        expected = json.load(f)

    try:
        with open(sys.argv[1], encoding="utf-8") as f:
            actual = json.load(f)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as e:
        fail(f"output is not valid JSON: {e}")

    if not isinstance(actual, dict):
        fail(f"output is not a JSON object: {type(actual).__name__}")

    missing = [k for k in (TOTAL_KEY, *COUNT_KEYS) if k not in actual]
    if missing:
        fail(f"output is missing keys: {', '.join(missing)}")

    for key in COUNT_KEYS:
        value = actual[key]
        if not is_int(value):
            fail(f"{key} is not an integer: {value!r}")
        if value != expected[key]:
            fail(f"{key} is {value}, expected {expected[key]}")

    total = actual[TOTAL_KEY]
    if not is_number(total):
        fail(f"{TOTAL_KEY} is not a number: {total!r}")
    try:
        diff = abs(float(total) - float(expected[TOTAL_KEY]))
    except OverflowError:
        fail(f"{TOTAL_KEY} is out of range: {total!r}")
    if not math.isfinite(diff) or diff > TOLERANCE:
        fail(f"{TOTAL_KEY} is {total!r}, expected {expected[TOTAL_KEY]}")


if __name__ == "__main__":
    main()
