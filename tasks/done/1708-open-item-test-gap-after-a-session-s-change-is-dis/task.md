# 1708 — Брак тесту (overseer): after a session's change is discarded with a blob whose content was altered on disk, the restored file equals the content the snapshot's sha256 names (or the restore refuses and says so)

Залежить від: —
Аудит потрібен: ні
Відкритий пункт: test-gap-after-a-session-s-change-is-discarded-with-a-blob-whose-cont-3a17f63c

## Що сталося
Overseer прийняв юніт `-|724-open-item-717-protected-file-guard-build|unit 1` (PASS, запит `20261012T030239Z-df119a`) і знайшов брак тесту: put() copies whatever lies at blobs/<sha>; a session that overwrites the blob makes the gate or the runner 'restore' the session's own content Де: `tests/test_protected_guard.py`. Вердикт — у ledger: `python3 .claude/hooks/journal.py show ledger`.

- Записано: 2026-10-12T03:16:11Z, overseer (overseer_verdict.py)

## Що зробити
Дописати перевірку «after a session's change is discarded with a blob whose content was altered on disk, the restored file equals the content the snapshot's sha256 names (or the restore refuses and says so)»: тест червоніє на тому, що описано вище (put() copies whatever lies at blobs/<sha>; a session that overwrites the blob makes the gate or the runner 'restore' the session's own content), і зелений на коді, як він є (покажи обидва прогони); код не міняти, якщо тест не знайде справжньої вади; швидкий набір тестів зелений.

## Готово, коли
Описане вище зроблено і перевірено, або на нього є відповідь власника.

## Питання до власника
