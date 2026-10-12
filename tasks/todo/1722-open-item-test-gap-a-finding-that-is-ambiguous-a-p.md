# 1722 — Брак тесту (overseer): a finding that is ambiguous (a planted item and a trap of its own file) and also names a trap of another file is not in trap_named_elsewhere while unread, and is listed with that other trap once read_

Залежить від: —
Аудит потрібен: ні
Відкритий пункт: test-gap-a-finding-that-is-ambiguous-a-planted-item-and-a-trap-of-its-95efe241

## Що сталося
Overseer прийняв юніт `-|730-open-item-059-scorer-residuals|unit 1` (PASS, запит `20261012T070427Z-7abc4e`) і знайшов брак тесту: a scorer that computes the list before applying the reading (so a finding read as planted is never listed for the other file's trap) passes: the read-by-hand negative uses a finding that names no trap outside its own file Де: `tests/test_simplifier_evals.py`. Вердикт — у ledger: `python3 .claude/hooks/journal.py show ledger`.

- Записано: 2026-10-12T07:14:32Z, overseer (overseer_verdict.py)

## Що зробити
Дописати перевірку «a finding that is ambiguous (a planted item and a trap of its own file) and also names a trap of another file is not in trap_named_elsewhere while unread, and is listed with that other trap once read_by_hand says «planted»»: тест червоніє на тому, що описано вище (a scorer that computes the list before applying the reading (so a finding read as planted is never listed for the other file's trap) passes: the read-by-hand negative uses a finding that names no trap outside its own file), і зелений на коді, як він є (покажи обидва прогони); код не міняти, якщо тест не знайде справжньої вади; швидкий набір тестів зелений.

## Готово, коли
Описане вище зроблено і перевірено, або на нього є відповідь власника.

## Питання до власника
