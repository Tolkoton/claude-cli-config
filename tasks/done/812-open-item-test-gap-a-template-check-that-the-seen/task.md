# 812 — Брак тесту (overseer): a template check that the «Seen in the code» comment of section 3 of the profile names the majority exception (only the files that do not keep the habit, and the search command), in step with step 3 o

Залежить від: —
Аудит потрібен: ні
Відкритий пункт: test-gap-a-template-check-that-the-seen-in-the-code-comment-of-sectio

## Що сталося
Overseer прийняв юніт `-|093-onboard-rules-and-hot-places|unit 1` (PASS, запит `20261011T125309Z-aacb94`) і знайшов брак тесту: today .claude/references/onboard-profile.md:50 still says the files that keep the habit AND those that do not are listed, with no exception, and no check compares the two texts Де: `tests/test_onboard.py`. Вердикт — у ledger: `python3 .claude/hooks/journal.py show ledger`.

- Записано: 2026-10-11T12:54:27Z, overseer (overseer_verdict.py)

## Що зробити
Дописати перевірку «a template check that the «Seen in the code» comment of section 3 of the profile names the majority exception (only the files that do not keep the habit, and the search command), in step with step 3 o»: тест червоніє на тому, що описано вище (today .claude/references/onboard-profile.md:50 still says the files that keep the habit AND those that do not are listed, with no exception, and no check compares the two texts), і зелений на коді, як він є (покажи обидва прогони); код не міняти, якщо тест не знайде справжньої вади; швидкий набір тестів зелений.

## Готово, коли
Описане вище зроблено і перевірено, або на нього є відповідь власника.

## Питання до власника
