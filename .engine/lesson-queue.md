# Lesson queue

One line per candidate: `- <date UTC> | <source> | <slice> | <essence> #<id>`. Filled by hooks (gate, overseer, parked, escalation) and by the agent. Triaged with `python3 .claude/hooks/lesson_queue.py resolve <id> --to memory|rule|engine|discard`; a resolved line is removed. Never loaded into the persistent context.

- 2026-10-04 | parked | --076-maintain-build-unit-1 | -/076-maintain-build/unit 1: audit request 20261004T224257Z-02b9cc got no valid verdict in 3 requests: the agent left no verdict #4e3abbcb
- 2026-10-05 | analyst | 052-engine-goals-document | dynamic framing: пропонувати 'Поки що не робимо' з умовою повернення замість статичних постійних заборон #a1b2c3d4
- 2026-10-05 | analyst | 052-engine-goals-document | repository boundary: верифікувати межі репозиторію; ізольовані зовнішні проєкти (Decana) виключати з цілей #e5f6a7b8
- 2026-10-05 | simplifier | - | duplication /home/lao/engine/AGENTS.md:32-33: The sentence 'Unattended work goes through the task board only: board-runner.sh takes one task at a time, each in a fresh session' repeats, inside the sam #66feba2a
- 2026-10-05 | parked | 044-validator-absolute-path | 044-validator-absolute-path: Валідатор спрощувача: абсолютний шлях у target обходить захищені зони і виводить за межі проєкту #0f931ec3
- 2026-10-05 | parked | 044-applied-finding-stays-open | 044-applied-finding-stays-open: Знахідка спрощувача, яку архітектор уже врахував, лишається у звіті власника як «confirm» #70a7af4f
- 2026-10-05 | parked | 044-vulture-public-api-noise | 044-vulture-public-api-noise: Сигнал «мертвий код» позначає публічну функцію бібліотеки, якою користуються лише тести #6843a85a
- 2026-10-05 | parked | --045-cleanup-when-board-idle-unit-1 | -/045-cleanup-when-board-idle/unit 1: Наглядач відклав юніт: -/045-cleanup-when-board-idle/unit 1 #aeb3ea2a
- 2026-10-06 | parked | 049-doing-two-sides | 049-doing-two-sides: Після 049: два місця ще вважають, що в doing/ одна задача #077689b3
- 2026-10-06 | parked | 061-arm-a-real | 061-arm-a-real: Дослід тестувальника: плече «А-справжнє» #f8cdfcad
- 2026-10-06 | agent | 001-verdict-handback | a test was missing: the SubagentStop envelope was probed only with an agent that called no tool, so the premise 'the reply is in last_assistant_message' was never checked for the shape every real over #34d4ada7
- 2026-10-06 | agent | 002-overseer-bash-edit | a test was missing: every case of the Stop hook's trigger wrote code with an edit tool, so the assumption 'a file is written only by Edit/Write' was never put against a file written by a shell command #cec0d28f
- 2026-10-06 | agent | 003-validator-absolute-path | A path a model writes is checked against path rules only after it is resolved to the file it names (relative to the project root, links and .. resolved): every validator case wrote the path one way, s #23830893
- 2026-10-06 | parked | 707-trigger-check-half-untested | 707-trigger-check-half-untested: Половина «перевірка» у спусковому гачку наглядача не має тесту #7fd4fb37
- 2026-10-06 | parked | 708-symlink-loop-traceback | 708-symlink-loop-traceback: Валідатор спрощувача: петля символьних посилань дає traceback замість відмови #e54c40a3
