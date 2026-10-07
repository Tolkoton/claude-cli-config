# Slice stock-levels

## Goal
Read the units on hand per SKU from the counted-stock file the operator keeps beside the price
list, and reserve against that number.

## Why now
`ON_HAND` in `cli.py` is the constant 100 for every SKU, so R4 refuses nothing the shop
actually lacks: an order for the last mug and the one after it both pass.

## Exit criterion
An order line for more units than the counted-stock file holds is refused with the number on hand.
