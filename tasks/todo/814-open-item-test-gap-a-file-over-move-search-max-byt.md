# 814 — Брак тесту (overseer): a file over MOVE_SEARCH_MAX_BYTES that names an old path is not searched, and a symlink that points at such a file is not followed

Залежить від: —
Аудит потрібен: ні
Відкритий пункт: test-gap-a-file-over-move-search-max-bytes-that-names-an-old-path-is-

## Що сталося
Overseer прийняв юніт `-|094-install-moves-and-onboard-dirty-tree|unit 1` (PASS, запит `20261011T131917Z-0f4956`) і знайшов брак тесту: deleting `or path.stat().st_size > MOVE_SEARCH_MAX_BYTES` or `or path.is_symlink()` at engine.py:298 leaves the suite at 16/0; the 1 MB limit is documented in docs/TEMPLATE-SETUP.md and held by nothing Де: `tests/test_install_move_notes.py`. Вердикт — у ledger: `python3 .claude/hooks/journal.py show ledger`.

- Записано: 2026-10-11T13:31:37Z, overseer (overseer_verdict.py)

## Що зробити
Дописати перевірку «a file over MOVE_SEARCH_MAX_BYTES that names an old path is not searched, and a symlink that points at such a file is not followed»: тест червоніє на тому, що описано вище (deleting `or path.stat().st_size > MOVE_SEARCH_MAX_BYTES` or `or path.is_symlink()` at engine.py:298 leaves the suite at 16/0; the 1 MB limit is documented in docs/TEMPLATE-SETUP.md and held by nothing), і зелений на коді, як він є (покажи обидва прогони); код не міняти, якщо тест не знайде справжньої вади; швидкий набір тестів зелений.

## Готово, коли
Описане вище зроблено і перевірено, або на нього є відповідь власника.

## Питання до власника
