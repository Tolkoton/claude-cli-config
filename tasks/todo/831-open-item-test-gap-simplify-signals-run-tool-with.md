# 831 — Брак тесту (overseer): simplify_signals.run_tool with another version of vulture (and of pylint) on PATH and a recording uvx stand-in at hand: the argv uvx receives starts with `--quiet vulture@<VERSIONS['vulture']>` (and `

Залежить від: —
Аудит потрібен: ні
Відкритий пункт: test-gap-simplify-signals-run-tool-with-another-version-of-vulture-an

## Що сталося
Overseer прийняв юніт `-|108-overseer-audit-four-tasks-closed-without-one|unit 1` (PASS, запит `20261011T212337Z-0ec3d0`) і знайшов брак тесту: run_tool that puts `['uvx', tool]` in front again when uvx is on PATH — the pre-107 form `[*prefix, tool, *args]` — takes the latest vulture and pylint, and test_tool_versions (19/0), test_simplify_signals (40/0), test_maintain (62/0) and test_simplifier (96/0) stay green: the UNPINNED pattern at tests/test_tool_versions.py:71 only sees a tool's name written as a literal after uvx, the only behavioural case (:146-156) has no uvx, and the 'callers take the versions from the module' check (:83) is satisfied by the word `tool_versions` anywhere in the file Де: `tests/test_tool_versions.py`. Вердикт — у ledger: `python3 .claude/hooks/journal.py show ledger`.

- Записано: 2026-10-11T21:27:38Z, overseer (overseer_verdict.py)

## Що зробити
Дописати перевірку «simplify_signals.run_tool with another version of vulture (and of pylint) on PATH and a recording uvx stand-in at hand: the argv uvx receives starts with `--quiet vulture@<VERSIONS['vulture']>` (and `»: тест червоніє на тому, що описано вище (run_tool that puts `['uvx', tool]` in front again when uvx is on PATH — the pre-107 form `[*prefix, tool, *args]` — takes the latest vulture and pylint, and test_tool_versions (19/0), test_simplify_signals (40/0), test_maintain (62/0) and test_simplifier (96/0) stay green: the UNPINNED pattern at tests/test_tool_versions.py:71 only sees a tool's name written as a literal after uvx, the only behavioural case (:146-156) has no uvx, and the 'callers take the versions from the module' check (:83) is satisfied by the word `tool_versions` anywhere in the file), і зелений на коді, як він є (покажи обидва прогони); код не міняти, якщо тест не знайде справжньої вади; швидкий набір тестів зелений.

## Готово, коли
Описане вище зроблено і перевірено, або на нього є відповідь власника.

## Питання до власника
