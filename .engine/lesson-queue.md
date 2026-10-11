# Lesson queue

One line per candidate: `- <date UTC> | <source> | <slice> | <essence> #<id>`. Filled by hooks (gate, overseer, parked, escalation) and by the agent. Triaged with `python3 .claude/hooks/lesson_queue.py resolve <id> --to memory|rule|engine|discard`; a resolved line is removed. Never loaded into the persistent context.

- 2026-10-11 | parked | check-close-pass-from-another-clone | check-close-pass-from-another-clone: check-close не бачить PASS overseer-а, записаний в іншому клоні, і commit, який потім змінив commit власника #7c6bdc78
