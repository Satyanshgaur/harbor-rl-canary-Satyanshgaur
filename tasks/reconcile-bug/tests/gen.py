#!/usr/bin/env python3
"""Generate random reconcile.py inputs.

Usage: gen.py <out_dir> <seed>
Writes group{1,2,3}_random{1..5}.csv into out_dir.

group1: well-formed rows only, with at least one cross-offset duplicate pair.
group2: group1 plus 1-2 SUCCESS rows on new ids with 3-4 decimal amounts.
group3: group1 plus 1-2 SUCCESS rows on new ids with lenient timestamps that
        datetime.fromisoformat accepts but the spec forbids, and sometimes a
        lenient FAILED row that would be the latest for an id that is
        otherwise SUCCESS.
"""
import random
import sys
from datetime import datetime, timedelta
from pathlib import Path

HEADER = "tx_id,timestamp,amount,status"
OFFSETS = ["Z", "+05:30", "-04:00", "+01:00", "-08:00"]
WHOLE_HOUR_OFFSETS = ["+01:00", "-04:00", "-08:00"]
STATUSES = ["SUCCESS", "FAILED", "PENDING"]
LENIENT_FORMS = [
    "space", "fraction", "compact_offset", "hour_offset",
    "no_seconds", "basic", "lowercase_t",
]
FILES_PER_GROUP = 5
WINDOW_MINUTES = 3 * 24 * 60


def offset_delta(offset):
    if offset == "Z":
        return timedelta(0)
    sign = 1 if offset[0] == "+" else -1
    return sign * timedelta(hours=int(offset[1:3]), minutes=int(offset[4:6]))


def strict_ts(utc, offset):
    local = utc + offset_delta(offset)
    return local.strftime("%Y-%m-%dT%H:%M:%S") + offset


def lenient_ts(rng, utc):
    form = rng.choice(LENIENT_FORMS)
    if form == "hour_offset":
        offset = rng.choice(WHOLE_HOUR_OFFSETS)
    elif form == "compact_offset":
        offset = rng.choice(OFFSETS[1:])
    else:
        offset = rng.choice(OFFSETS)
    local = utc + offset_delta(offset)
    compact = offset.replace(":", "")
    if form == "space":
        return local.strftime("%Y-%m-%d %H:%M:%S") + offset
    if form == "fraction":
        return local.strftime("%Y-%m-%dT%H:%M:%S") + f".{rng.randint(1, 999):03d}" + offset
    if form == "compact_offset":
        return local.strftime("%Y-%m-%dT%H:%M:%S") + compact
    if form == "hour_offset":
        return local.strftime("%Y-%m-%dT%H:%M:%S") + offset[:3]
    if form == "no_seconds":
        return local.strftime("%Y-%m-%dT%H:%M") + offset
    if form == "basic":
        return local.strftime("%Y%m%dT%H%M%S") + compact
    return local.strftime("%Y-%m-%dt%H:%M:%S") + offset


def amount(rng):
    whole = rng.randint(1, 500)
    kind = rng.random()
    if kind < 0.25:
        return str(whole)
    if kind < 0.45:
        return f"{whole}.{rng.randint(0, 9)}"
    return f"{whole}.{rng.randint(0, 99):02d}"


def long_amount(rng):
    places = rng.choice([3, 4])
    frac = rng.randint(1, 10**places - 1)
    if frac % 10 == 0:
        frac += 1
    return f"{rng.randint(1, 500)}.{frac:0{places}d}"


def random_utc(rng, start, taken=()):
    """A UTC time in the window at least a minute away from every time in taken."""
    while True:
        utc = start + timedelta(minutes=rng.randint(0, WINDOW_MINUTES), seconds=rng.randint(0, 59))
        if all(abs(utc - t) >= timedelta(minutes=1) for t in taken):
            return utc


def make_file(rng, group):
    ids = iter(f"TX{n}" for n in rng.sample(range(1000, 10000), 30))
    start = datetime(2026, rng.randint(1, 12), rng.randint(1, 28))
    rows = []  # (tx_id, utc, timestamp, amount, status)

    def add(tx_id, utc, timestamp, status, amt=None):
        rows.append((tx_id, utc, timestamp, amt or amount(rng), status))

    def times_of(tx_id):
        return [r[1] for r in rows if r[0] == tx_id]

    base_ids = [next(ids) for _ in range(rng.randint(5, 9))]
    for tx_id in base_ids:
        utc = random_utc(rng, start)
        add(tx_id, utc, strict_ts(utc, rng.choice(OFFSETS)), rng.choice(STATUSES))

    # Cross-offset pair whose wall-clock order is the reverse of its UTC order.
    pair_id = next(ids)
    early = random_utc(rng, start)
    late = early + timedelta(minutes=rng.randint(30, 9 * 60))
    first, second = rng.sample(STATUSES, 2)
    add(pair_id, early, strict_ts(early, "+05:30"), first)
    add(pair_id, late, strict_ts(late, rng.choice(["-04:00", "-08:00"])), second)
    base_ids.append(pair_id)

    for tx_id in rng.sample(base_ids, rng.randint(0, 3)):
        utc = random_utc(rng, start, times_of(tx_id))
        add(tx_id, utc, strict_ts(utc, rng.choice(OFFSETS)), rng.choice(STATUSES))

    if group == 2:
        for _ in range(rng.randint(1, 2)):
            utc = random_utc(rng, start)
            add(next(ids), utc, strict_ts(utc, rng.choice(OFFSETS)), "SUCCESS", long_amount(rng))

    if group == 3:
        for _ in range(rng.randint(1, 2)):
            utc = random_utc(rng, start)
            add(next(ids), utc, lenient_ts(rng, utc), "SUCCESS")
        if rng.random() < 0.5:
            latest = {}
            for row in rows:
                if row[0] in base_ids and (row[0] not in latest or row[1] > latest[row[0]][1]):
                    latest[row[0]] = row
            succeeded = [row for row in latest.values() if row[4] == "SUCCESS"]
            if succeeded:
                tx_id, utc = rng.choice(succeeded)[:2]
                utc += timedelta(minutes=rng.randint(2, 600))
                add(tx_id, utc, lenient_ts(rng, utc), "FAILED")

    rng.shuffle(rows)
    lines = [HEADER] + [f"{tx_id},{ts},{amt},{status}" for tx_id, _, ts, amt, status in rows]
    return "\n".join(lines) + "\n"


def main():
    if len(sys.argv) != 3:
        print("usage: gen.py <out_dir> <seed>", file=sys.stderr)
        sys.exit(2)
    out_dir = Path(sys.argv[1])
    rng = random.Random(int(sys.argv[2]))
    for group in (1, 2, 3):
        for i in range(1, FILES_PER_GROUP + 1):
            path = out_dir / f"group{group}_random{i}.csv"
            path.write_text(make_file(rng, group))


if __name__ == "__main__":
    main()
