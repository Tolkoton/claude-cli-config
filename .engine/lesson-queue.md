# Lesson queue

One line per candidate: `- <date UTC> | <source> | <slice> | <essence> #<id>`. Filled by hooks (gate, overseer, parked, escalation) and by the agent. Triaged with `python3 .claude/hooks/lesson_queue.py resolve <id> --to memory|rule|engine|discard`; a resolved line is removed. Never loaded into the persistent context.

- 2026-10-04 | parked | --076-maintain-build-unit-1 | -/076-maintain-build/unit 1: audit request 20261004T224257Z-02b9cc got no valid verdict in 3 requests: the agent left no verdict #4e3abbcb
- 2026-10-05 | analyst | 052-engine-goals-document | dynamic framing: пропонувати 'Поки що не робимо' з умовою повернення замість статичних постійних заборон #a1b2c3d4
- 2026-10-05 | analyst | 052-engine-goals-document | repository boundary: верифікувати межі репозиторію; ізольовані зовнішні проєкти (Decana) виключати з цілей #e5f6a7b8
- 2026-10-05 | simplifier | - | duplication /home/lao/engine/AGENTS.md:32-33: The sentence 'Unattended work goes through the task board only: board-runner.sh takes one task at a time, each in a fresh session' repeats, inside the sam #66feba2a
- 2026-10-05 | parked | 044-applied-finding-stays-open | 044-applied-finding-stays-open: Знахідка спрощувача, яку архітектор уже врахував, лишається у звіті власника як «confirm» #70a7af4f
- 2026-10-05 | parked | --045-cleanup-when-board-idle-unit-1 | -/045-cleanup-when-board-idle/unit 1: Наглядач відклав юніт: -/045-cleanup-when-board-idle/unit 1 #aeb3ea2a
- 2026-10-06 | parked | 049-doing-two-sides | 049-doing-two-sides: Після 049: два місця ще вважають, що в doing/ одна задача #077689b3
- 2026-10-06 | parked | 061-arm-a-real | 061-arm-a-real: Дослід тестувальника: плече «А-справжнє» #f8cdfcad
- 2026-10-06 | agent | 001-verdict-handback | a test was missing: the SubagentStop envelope was probed only with an agent that called no tool, so the premise 'the reply is in last_assistant_message' was never checked for the shape every real over #34d4ada7
- 2026-10-06 | agent | 002-overseer-bash-edit | a test was missing: every case of the Stop hook's trigger wrote code with an edit tool, so the assumption 'a file is written only by Edit/Write' was never put against a file written by a shell command #cec0d28f
- 2026-10-06 | agent | 003-validator-absolute-path | A path a model writes is checked against path rules only after it is resolved to the file it names (relative to the project root, links and .. resolved): every validator case wrote the path one way, s #23830893
- 2026-10-06 | agent | 004-symlink-loop-traceback | A test was missing: when fix 003 replaced is_file() with Path.resolve(), its cases had only links that lead somewhere; a call swapped for one with a different set of exceptions needs a case for each w #7ac596ba
- 2026-10-06 | agent | 005-resolve-loop-other-scripts | A test was missing: every script that judges a given path with resolve() then is_file() had a case for a missing file and none for a link to itself, where resolve() itself raises (RuntimeError up to P #4a47fe08
- 2026-10-06 | overseer | - | BLOCK no.1 false-DONE — the four named places are fixed and proved, but section 4 of the bug record (the contract) says the same-places search "named exactly these four, and they are all fixed here",  #93e1309e
- 2026-10-06 | overseer | - | BLOCK no.1 false-DONE — the six places are fixed and every quoted output reproduces, but section 4 of the bug record (the contract) again claims a complete same-places search ("the list below is the w #2e6cda37
- 2026-10-06 | parked | 718-resolve-loop-outside-hooks | 718-resolve-loop-outside-hooks: Петля символьних посилань дає traceback у doc_audit.py та в скриптах evals/ #7080258a
- 2026-10-06 | parked | 013-second-opinion-remove-or-keep | 013-second-opinion-remove-or-keep: Друга думка Gemini не пройшла пороги: прибрати збудоване чи лишити вимкненим #44a91037
- 2026-10-06 | parked | release-counts-zero-verdict-audit | release-counts-zero-verdict-audit: реліз приймає повний аудит без жодного вердикту #d74d85ad
- 2026-10-06 | parked | 076-maintain-build-unit-1-accept-or-reaudit | 076-maintain-build/unit 1/accept-or-reaudit: Юніт 1 задачі 076 лишився без записаного вердикту: прийняти чи повторити аудит #1ed407e9
- 2026-10-06 | parked | 045-anomaly-failed-untested | 045/anomaly-failed-untested: Подію anomaly-failed виконавця не тримає жоден тест (045) #93310a0d
- 2026-10-06 | parked | 717-protected-file-guard-build | 717-protected-file-guard-build: Охоронюваний файл змінився за хід: будівництво за проєктом 717 #b9cfd70d
