# Lesson queue

One line per candidate: `- <date UTC> | <source> | <slice> | <essence> #<id>`. Filled by hooks (gate, overseer, parked, escalation) and by the agent. Triaged with `python3 .claude/hooks/lesson_queue.py resolve <id> --to memory|rule|engine|discard`; a resolved line is removed. Never loaded into the persistent context.

- 2026-10-10 | agent | 007-testing-guard-resolve-loop | A hook that promises Python 3.11+ is tested only under 3.13, where resolve() no longer raises on a symlink loop: the guard's loop case broke on 3.12 unseen; a code path that differs between versions n #b4933b7b
