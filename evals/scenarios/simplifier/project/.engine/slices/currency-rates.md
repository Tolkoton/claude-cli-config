# Slice currency-rates

## Goal
Add a `rates` module with a currency table and `convert(amount, from_currency, to_currency)`,
and thread a `currency` argument through `total` and the receipt.

## Why now
The shop sells in one currency today. Once it sells abroad every price path will need a
currency, and adding it later would touch every module — so the table and the conversion
layer go in before the code grows around a single currency.

## Exit criterion
`convert` round-trips EUR -> USD -> EUR within one cent; `total` accepts `currency`.
