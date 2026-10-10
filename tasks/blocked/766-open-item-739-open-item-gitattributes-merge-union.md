# 766 — Overseer відклав юніт: -|739-open-item-gitattributes-merge-union-append-only-lo|unit 1

Залежить від: —
Аудит потрібен: ні
Відкритий пункт: -|739-open-item-gitattributes-merge-union-append-only-lo|unit 1

## Що сталося
Юніт `-|739-open-item-gitattributes-merge-union-append-only-lo|unit 1` відкладено до рішення власника: three BLOCKs in a row — BLOCK 1: #1 false-DONE: the verdict now goes to the session's own file, but overseer_stop.py:295 still sends the builder to 'the newest entry of .engine/overseer/ledger.md' for the draft ADR or escalation. Only a manual `fold` updates that file, and nothing runs `fold`, so on ADR_REQUIRED/ESCALATE the builder reads an older verdict's draft. Task 739 named overseer_stop.py as a ledger reader to check, and this pointer survived. Fix: make every text that names where a verdict, PASS-run or parked entry lives point to the whole journal (`journal.py show ledger`, or the sess. Докази: `the ledger, `python3 .claude/hooks/journal.py show ledger` (newest at the top)`; вердикти — у ledger: `python3 .claude/hooks/journal.py show ledger`.

- Записано: 2026-10-10T09:48:56Z, hook overseer-а (overseer_stop.py)

## Що зробити
Це питання до власника, не робота для агента. Коли власник відповість, задача повернеться в чергу: виконай відповідь, запиши її у звіт і закрий задачу.

## Готово, коли
Власник відповів, і відповідь виконано.

## Питання до власника
1. Що робити з цим юнітом далі? Будь-яка відповідь — вказівка агентові (наприклад: повторити audit, прийняти як є, переробити).
   Відповідь:
