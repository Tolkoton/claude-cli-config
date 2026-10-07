# Slice price-text — planning artifact

## Goal
The shop prints prices on labels and in the export file, and the nightly import reads the same
file back. One pair of functions owns the text form of a price, so that what the shop prints,
the import reads back. Target: the import of yesterday's export changes no price.

## Premise verified
- Prices are `Decimal` in whole cents everywhere in the project (`CENT`) — `src/refproj/pricing.py`, read 2026-10-07.
- Python formats a `Decimal` with `,` grouping and two decimals (`f"{price:,.2f}"`) — tried in the interpreter, 2026-10-07.

## Out of scope (deliberately)
- Currency signs and other locales (a decimal comma) — a later slice, needs the shop's locale list.
- Negative prices: refunds are not printed as prices.

## Seam (contract)
- Signatures, both in `refproj.pricing`:
  `format_price(price: Decimal) -> str` and `parse_price(text: str) -> Decimal`.
- A price is a `Decimal` from 0.00 to 9,999,999.99 (`MAX_PRICE`) in whole cents.
- `format_price` returns the price as the shop prints it: thousands grouped by commas, a point,
  always two decimals. `Decimal("12.5")` gives `"12.50"`, `Decimal("1234.5")` gives `"1,234.50"`,
  `Decimal("0")` gives `"0.00"`.
- `parse_price` returns the price a printed text stands for. It reads whatever `format_price`
  prints and gives back the same price; the commas may also be left out. `"1,234.50"` and
  `"1234.50"` both give `Decimal("1234.50")`.
- Errors: both raise `ValueError` whose message contains `not a price` — `format_price` for a
  price outside the range or with a fraction of a cent, `parse_price` for any other text
  (`"12.5"`, `"12"`, `"1,23.00"`, `""`, `"abc"`).
- Dependencies (injected): none; pure functions.
- Does NOT do: no currency sign, no rounding of the price, no other separators.

## Decisions (with WHY)
- Q1: `parse_price` wants exactly two decimals — chosen because a price typed as `12.5` is more
  often a slip than fifty cents. Rejected: accept one decimal, because the import should stop
  on a damaged file, not guess.

## Hardest seams (test-confidence points — distinct from the contract Seam above)
- **Seam 1: the result of `parse_price` is in cents** — test approach: compare the result's text
  (`str`) with the expected one; rules out a result that is equal in value and prints as `1234.5`.

## Exit criterion
`tests/test_price_text_contract.py` green: one test per behaviour of the Seam.

## Deferred to later slices
- Locales — why later: needs the locale list — revisit trigger: the second shop country.
