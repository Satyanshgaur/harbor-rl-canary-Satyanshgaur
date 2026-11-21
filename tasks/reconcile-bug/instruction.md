# Fix the payments reconciliation script

`/app/reconcile.py` is our small CLI for reconciling a batch of payment transactions.
Right now it either doesn't run or gives the wrong numbers. Please fix it in place
so it follows the rules below.

## Usage

```
python3 /app/reconcile.py <path/to/input.csv>
```

Keep the script at this path and keep this command working. Use Python 3.12 and the standard library only.

## Input

The input is a CSV file. The first line is always the header `tx_id,timestamp,amount,status`.
Fields are never quoted and have no surrounding whitespace. In a well-formed row, the fields come
in that order and look like this:

- `tx_id`: a transaction ID, e.g. `TX1001`. The same ID can appear on more than one row.
- `timestamp`: exactly `YYYY-MM-DDTHH:MM:SS` followed by `Z` or `±HH:MM`, e.g.
  `2026-01-05T05:00:00Z` or `2026-01-05T10:00:00+05:30`. Rows are not in any guaranteed order.
- `amount`: a plain decimal number with at most 2 decimal places, e.g. `120.50`, `9`, `0.99`.
- `status`: exactly `SUCCESS`, `FAILED` or `PENDING`, in uppercase.

## Business rules

Apply these in order:

1. **Skip malformed rows.** A row is malformed if any of these is true:
   - it doesn't have exactly 4 fields (a blank line counts as malformed)
   - it has an empty field
   - any field doesn't match the well-formed description above (for example, an amount
     with a sign, an exponent, `nan`, `inf` or more than 2 decimals)
   - the timestamp isn't a real calendar date and time

   Malformed rows are ignored completely, including when applying rule 2.
2. **Resolve duplicates.** If a `tx_id` appears on more than one row, only the row with the
   latest point in time counts. That row's status decides the outcome. Earlier rows are
   ignored even if they were `SUCCESS` (a later `FAILED` is a reversal). Two rows with the
   same `tx_id` are never at the same point in time.
3. **Classify.** `SUCCESS` counts as valid, `FAILED` counts as failed, and `PENDING` counts toward neither.
4. **Total.** `total_valid_amount` is the sum of the amounts of valid transactions,
   rounded to 2 decimal places.

## Output

Print exactly one JSON object to stdout and exit with code 0. It has these keys:

- `total_valid_amount`: a JSON number, compared numerically (`0` and `0.0` are equivalent)
- `valid_count`: an integer, the number of valid transactions
- `failed_count`: an integer, the number of failed transactions

Nothing else may go to stdout; send any diagnostics to stderr. If the file has no rows
after the header, or only malformed ones, the output is
`{"total_valid_amount": 0, "valid_count": 0, "failed_count": 0}`.

## Example

```
tx_id,timestamp,amount,status
TX1,2026-01-05T09:00:00Z,120.50,SUCCESS
TX5,2026-01-05T12:30:00Z,30.00,FAILED
TX2,2026-01-05T09:05:00Z,40.00,FAILED
TX3,2026-01-05T09:10:00Z,15.25,PENDING
TX7,2026-01-05 11:00:00Z,8.00,SUCCESS
TX4,2026-01-05T09:15:00Z,abc,SUCCESS
TX5,2026-01-05T10:00:00Z,30.00,SUCCESS
TX6,2026-01-05T10:20:00Z,9.99,SUCCESS
```

Expected output:

```
{"total_valid_amount": 130.49, "valid_count": 2, "failed_count": 2}
```

TX4 and TX7 are malformed and are skipped: TX4's amount isn't a number, and TX7's timestamp has a
space instead of `T`. TX5's 12:30 row is its latest, even though it comes first in the
file, so TX5 counts as failed and its 10:00 `SUCCESS` is ignored. TX3 is pending.
Valid: TX1 + TX6 = 120.50 + 9.99 = 130.49. Failed: TX2 and TX5.

## Notes

- Your fix will be checked against other CSV files, not just this example.
- Don't rename or move the script.
