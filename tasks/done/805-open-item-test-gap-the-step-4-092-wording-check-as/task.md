# 805 — Брак тесту (overseer): the 'step 4 (092)' wording check asserts the third case 'a commit that says less than the rule claims', that «Could not check» stays written next to its reference, and that the profile's second line c

Залежить від: —
Аудит потрібен: ні
Відкритий пункт: test-gap-the-step-4-092-wording-check-asserts-the-third-case-a-commit

## Що сталося
Overseer прийняв юніт `-|092-onboard-unattended-and-fresh-reader|unit 1` (PASS, запит `20261011T121803Z-a3aa5d`) і знайшов брак тесту: each of the three sentences can be deleted from .claude/commands/onboard.md with the suite at 81/0; the commit case is the one the task's «Звідки» names from the trial of board 057 Де: `tests/test_onboard.py`. Вердикт — у ledger: `python3 .claude/hooks/journal.py show ledger`.

- Записано: 2026-10-11T12:30:22Z, overseer (overseer_verdict.py)

## Що зробити
Дописати перевірку «the 'step 4 (092)' wording check asserts the third case 'a commit that says less than the rule claims', that «Could not check» stays written next to its reference, and that the profile's second line c»: тест червоніє на тому, що описано вище (each of the three sentences can be deleted from .claude/commands/onboard.md with the suite at 81/0; the commit case is the one the task's «Звідки» names from the trial of board 057), і зелений на коді, як він є (покажи обидва прогони); код не міняти, якщо тест не знайде справжньої вади; швидкий набір тестів зелений.

## Готово, коли
Описане вище зроблено і перевірено, або на нього є відповідь власника.

## Питання до власника
