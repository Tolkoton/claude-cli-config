# Slice sku-normalize — planning artifact

## Goal
Clerks type the same article number in many ways (`ab 12`, `AB-12`, `ab_12`), and the stock list
then holds one article several times. One function gives every article number its single
spelling. It runs on every import, also over numbers that were normalized before, so a
normalized number must come out of it unchanged. Target: no article appears twice in the stock
list because of spelling.

## Premise verified
- `StockItem.sku` is a plain `str` and nothing in the project normalizes it yet — `src/refproj/inventory.py`, read 2026-10-07.

## Out of scope (deliberately)
- Checking that the article exists.
- Characters other than ASCII letters, digits and the four separators: they are not expected in
  an article number and this slice does not judge them.

## Seam (contract)
- Signature: `normalize_sku(text: str) -> str` in `refproj.inventory`.
- `text` is an article number as typed: ASCII letters, digits and separators. The separators
  are the space, the tab, the hyphen and the underscore.
- Returns: the single spelling — letters in upper case; every run of separators between two
  parts becomes one hyphen; separators at the ends are dropped. `" ab  12 "`, `"ab_12"` and
  `"ab--12"` all give `"AB-12"`. A normalized article number is its own spelling:
  `"AB-12"` gives `"AB-12"`.
- Errors: a text with no letter and no digit raises `ValueError` whose message contains
  `no article number`.
- Dependencies (injected): none; a pure function.
- Does NOT do: no lookup, no check of the article's format, no change to a `StockItem`.

## Decisions (with WHY)
- Q1: the hyphen is the one separator — chosen because the supplier's catalogue prints article
  numbers with hyphens. Rejected: remove separators altogether, because `AB-12` and `A-B12` are
  different articles.

## Hardest seams (test-confidence points — distinct from the contract Seam above)
- **Seam 1: digits and letters keep their order and number** — test approach: compare the
  result without its hyphens with the upper-cased input without its separators; rules out a
  function that drops or reorders a part.

## Exit criterion
`tests/test_sku_normalize_contract.py` green: one test per behaviour of the Seam.

## Deferred to later slices
- Format check per supplier — why later: needs the suppliers' formats — revisit trigger: the supplier slice.
