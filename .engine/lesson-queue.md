# Lesson queue

One line per candidate: `- <date UTC> | <source> | <slice> | <essence> #<id>`. Filled by hooks (gate, overseer, parked, escalation) and by the agent. Triaged with `python3 .claude/hooks/lesson_queue.py resolve <id> --to memory|rule|engine|discard`; a resolved line is removed. Never loaded into the persistent context.

- 2026-10-04 | parked | --076-maintain-build-unit-1 | -/076-maintain-build/unit 1: audit request 20261004T224257Z-02b9cc got no valid verdict in 3 requests: the agent left no verdict #4e3abbcb
- 2026-10-05 | analyst | 052-engine-goals-document | dynamic framing: пропонувати 'Поки що не робимо' з умовою повернення замість статичних постійних заборон #a1b2c3d4
- 2026-10-05 | analyst | 052-engine-goals-document | repository boundary: верифікувати межі репозиторію; ізольовані зовнішні проєкти (Decana) виключати з цілей #e5f6a7b8
- 2026-10-05 | simplifier | - | duplication /home/lao/engine/AGENTS.md:32-33: The sentence 'Unattended work goes through the task board only: board-runner.sh takes one task at a time, each in a fresh session' repeats, inside the sam #66feba2a
- 2026-10-05 | parked | 044-verdict-handback | 044-verdict-handback: Вердикт наглядача не записується: відповідь підагента приходить через SubagentHandback (причина для 705) #a3ae0de9
- 2026-10-05 | parked | 044-overseer-bash-edit | 044-overseer-bash-edit: Наглядач не запитується, коли код юніта записано командою оболонки, а не Edit/Write #fd9c2734
- 2026-10-05 | parked | 044-validator-absolute-path | 044-validator-absolute-path: Валідатор спрощувача: абсолютний шлях у target обходить захищені зони і виводить за межі проєкту #0f931ec3
- 2026-10-05 | parked | 044-applied-finding-stays-open | 044-applied-finding-stays-open: Знахідка спрощувача, яку архітектор уже врахував, лишається у звіті власника як «confirm» #70a7af4f
- 2026-10-05 | parked | 044-vulture-public-api-noise | 044-vulture-public-api-noise: Сигнал «мертвий код» позначає публічну функцію бібліотеки, якою користуються лише тести #6843a85a
