# 759 — Overseer відклав юніт: -|099-modes-sketch|unit 1

Залежить від: —
Аудит потрібен: ні
Відкритий пункт: -|099-modes-sketch|unit 1

## Що сталося
Юніт `-|099-modes-sketch|unit 1` відкладено до рішення власника: three BLOCKs in a row — BLOCK 1: #1 false-DONE: the quarantine's sketch/reference check misses literal paths into a named sketch, which contradicts the turn's claim («такий шлях у скрипті») and the «Готово, коли» line «робочий файл імпортує з sketches/ — блок». gate.py:1205 accepts one `./` or `../` prefix but not two, so a working-code JS import `from "../../sketches/rate/f.js"` and a shell line `bash ../../sketches/rate/run.sh` pass the stop layer, while `../sketches/…` blocks. Fix: make the prefix repeatable (e.g. `(?:\.{1,2}/)*`). Then either catch or document in docs/engine-limits.md the . Докази: `.engine/overseer/ledger.md`; вердикти — у `.engine/overseer/ledger.md`.

- Записано: 2026-10-10T05:54:34Z, hook overseer-а (overseer_stop.py)

## Що зробити
Це питання до власника, не робота для агента. Коли власник відповість, задача повернеться в чергу: виконай відповідь, запиши її у звіт і закрий задачу.

## Готово, коли
Власник відповів, і відповідь виконано.

## Питання до власника
1. Що робити з цим юнітом далі? Будь-яка відповідь — вказівка агентові (наприклад: повторити audit, прийняти як є, переробити).
   Відповідь:
