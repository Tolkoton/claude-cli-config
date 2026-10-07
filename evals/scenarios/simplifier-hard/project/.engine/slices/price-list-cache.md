# Slice price-list-cache

## Goal
Keep the parsed price list in `.cache/prices.pickle`, keyed by the list's modification time, and
load it from there when the list has not changed.

## Why now
The list is read and parsed on every order. It holds a few dozen SKUs today; when a shop
carries thousands the parse will be felt at the counter, and a cache is easier to add while
`load_price_list` has one caller.

## Exit criterion
A second order against an unchanged list does not parse it; an edited list is parsed again.
