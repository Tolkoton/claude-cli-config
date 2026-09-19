# Overseer ledger — append-only
Append one entry per overseer invocation. Newest at the top below this header.

## 2026-09-18T10:31:00Z — ref-tax — OVERSEER_PASS
- Trigger: none
- Evidence: `tests/test_pricing.py::test_with_tax_rounds_half_up` output shown in turn; matches exit criterion 1.

## 2026-09-18T09:58:00Z — ref-tax — OVERSEER_PASS
- Trigger: none
- Evidence: RED output for `test_with_tax_rejects_negative_rate` shown before the implementation.

## 2026-09-18T09:20:00Z — ref-tax — OVERSEER_PASS
- Trigger: none
- Evidence: planning artifact seams match the first RED test (half-cent table).
