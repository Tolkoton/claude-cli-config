# The receipt record

One JSON file beside each receipt, same name, suffix `.json`. It is read by the accountant's
ledger import, which is not in this repository and is not ours to change.

| field | value |
|---|---|
| `schema` | `2` — the import refuses any other number |
| `order_id` | the order id as typed |
| `total` | the charged amount, a string with two decimals |
| `currency` | `EUR` |

The import rejects a record with a field missing, also one whose value never varies.
