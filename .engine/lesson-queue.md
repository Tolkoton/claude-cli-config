# Lesson queue

One line per candidate: `- <date UTC> | <source> | <slice> | <essence> #<id>`. Filled by hooks (gate, overseer, parked, escalation) and by the agent. Triaged with `python3 .claude/hooks/lesson_queue.py resolve <id> --to memory|rule|engine|discard`; a resolved line is removed. Never loaded into the persistent context.

- 2026-10-04 | parked | --076-maintain-build-unit-1 | -/076-maintain-build/unit 1: audit request 20261004T224257Z-02b9cc got no valid verdict in 3 requests: the agent left no verdict #4e3abbcb
- 2026-10-05 | analyst | 052-engine-goals-document | dynamic framing: пропонувати 'Поки що не робимо' з умовою повернення замість статичних постійних заборон #a1b2c3d4
- 2026-10-05 | analyst | 052-engine-goals-document | repository boundary: верифікувати межі репозиторію; ізольовані зовнішні проєкти (Decana) виключати з цілей #e5f6a7b8
- 2026-10-05 | simplifier | - | duplication /home/lao/engine/AGENTS.md:32-33: The sentence 'Unattended work goes through the task board only: board-runner.sh takes one task at a time, each in a fresh session' repeats, inside the sam #66feba2a
