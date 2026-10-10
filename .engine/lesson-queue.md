# Lesson queue

One line per candidate: `- <date UTC> | <source> | <slice> | <essence> #<id>`. Filled by hooks (gate, overseer, parked, escalation) and by the agent. Triaged with `python3 .claude/hooks/lesson_queue.py resolve <id> --to memory|rule|engine|discard`; a resolved line is removed. Never loaded into the persistent context.

- 2026-10-10 | parked | test-gap-item-text-after-a-block | test-gap-item-text-after-a-block: Пункт браку тесту з BLOCK-у пише «Overseer прийняв юніт (PASS…)» #d5b27b65
- 2026-10-10 | overseer | - | BLOCK no.1 false-DONE: the quarantine's sketch/reference check misses literal paths into a named sketch, which contradicts the turn's claim («такий шлях у скрипті») and the «Готово, коли» line «робочи #a3e25cd9
- 2026-10-10 | parked | test-gap-a-task-whose-owner-line-is-and-which-carries-a-section-to-mo | test-gap-a-task-whose-owner-line-is-and-which-carries-a-section-to-mo: Брак тесту (overseer): a task whose owner line is «Режим: ескіз» and which carries a `no.no. Режим піднято` section to соло (mode #58966405
- 2026-10-10 | overseer | - | BLOCK no.1 false-DONE: after a reader-blocks park, the owner's answer does not give the record three new readings. The new park question (board.py:1018-1021) promises «запис отримає три нові читання», #3ebfcb74
- 2026-10-10 | overseer | - | BLOCK no.1 false-DONE: both earlier BLOCKs are fixed and the full set is green, but I reproduced two cases where the quarantine is wrong. (a) In a documented configuration, an empty CODE_EXTENSIONS, s #e8c954e2
- 2026-10-10 | parked | --099-modes-sketch-unit-1 | -/099-modes-sketch/unit 1: Overseer відклав юніт: -/099-modes-sketch/unit 1 #eac2de08
