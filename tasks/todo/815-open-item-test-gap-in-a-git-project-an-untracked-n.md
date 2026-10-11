# 815 — Брак тесту (overseer): in a git project an untracked, not ignored file that names an old path is reported, and an ignored one is not

Залежить від: —
Аудит потрібен: ні
Відкритий пункт: test-gap-in-a-git-project-an-untracked-not-ignored-file-that-names-an

## Що сталося
Overseer прийняв юніт `-|094-install-moves-and-onboard-dirty-tree|unit 1` (PASS, запит `20261011T131917Z-0f4956`) і знайшов брак тесту: `git ls-files -z -c` instead of `-co --exclude-standard` leaves the suite at 16/0: every file of the git fixture is committed, so 'what git tracks or would track' is tried only for tracked files, and nothing shows that an ignored directory stays out Де: `tests/test_install_move_notes.py`. Вердикт — у ledger: `python3 .claude/hooks/journal.py show ledger`.

- Записано: 2026-10-11T13:31:37Z, overseer (overseer_verdict.py)

## Що зробити
Дописати перевірку «in a git project an untracked, not ignored file that names an old path is reported, and an ignored one is not»: тест червоніє на тому, що описано вище (`git ls-files -z -c` instead of `-co --exclude-standard` leaves the suite at 16/0: every file of the git fixture is committed, so 'what git tracks or would track' is tried only for tracked files, and nothing shows that an ignored directory stays out), і зелений на коді, як він є (покажи обидва прогони); код не міняти, якщо тест не знайде справжньої вади; швидкий набір тестів зелений.

## Готово, коли
Описане вище зроблено і перевірено, або на нього є відповідь власника.

## Питання до власника
