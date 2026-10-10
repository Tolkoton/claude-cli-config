# 603 — Хмарна сесія: push своєї гілки і web без підтвердження

Залежить від: —
Потрібна присутність власника: так
Аудит потрібен: ні

## Що зробити
- Рішення власника: хмарна сесія має працювати без зупинок на підтвердження. Зараз її зупиняють два правила в .claude/settings.json: `permissions.ask` містить `Bash(git push:*)` і `Bash(git push)`, а WebFetch і WebSearch немає в `permissions.allow`. Ні prompt, ні hook цього не обходять (документація Claude Code: рішення PreToolUse hook не скасовує ask rule), тож міняти треба сам файл налаштувань.
- Пропозиція налаштувань у docs/tasks/settings.json (перевірка — settings_check.py; питання до власника з рядком дії apply-settings): прибрати `Bash(git push:*)` і `Bash(git push)` з `ask`; додати `WebFetch` і `WebSearch` в `allow`. Решту файла не міняти.
- Правило push переходить у PreToolUse hook для Bash (park-ask-gated.py або block-dangerous.sh — обери сам і поясни у звіті):
  - хмарна сесія (CLAUDE_CODE_REMOTE=true) з CLOUD_COMMIT_POLICY="session-branch": push поточної гілки, якщо її назва починається з claude/, в origin — без підтвердження; будь-який інший push із хмари (інша гілка чи remote, unattended/*, main, stable, --all, теги) — відмова з причиною;
  - локальна сесія з власником — hook повертає «ask»: підтвердження лишається, як зараз;
  - runner, тобто сесія без нагляду, — відмова, як зараз: гілку надсилає сам runner;
  - push усередині bash -c, sh -c чи eval оцінюється так само, як прямий; forced push і видалення гілок — відмова скрізь, як зараз.
- Онови дзеркальний список у park-ask-gated.py і документацію правил push.

## Готово, коли
- Є тести на кожен випадок вище, разом із негативними; golden set і швидкий набір тестів зелені.
- У blocked/ лежить задача з питанням до власника, рядком дії apply-settings і точним sha256 пропозиції.

## Питання до власника
1. Застосувати пропозицію налаштувань `docs/tasks/settings.json`? Вона змінює в чинному `.claude/settings.json` рівно два списки, решта файла та сама (diff — 6 рядків): з `permissions.ask` прибирає `Bash(git push:*)` і `Bash(git push)`, у `permissions.allow` додає `WebFetch` і `WebSearch`. Після цього хмарна сесія з `CLOUD_COMMIT_POLICY="session-branch"` надсилає свою гілку `claude/…` в `origin` і користується web без підтвердження. Будь-який інший push із хмари hook `park-ask-gated.py` відмовляє, пояснюючи причину. Локально push і далі питає підтвердження (тепер його показує hook), а runner, як і раніше, push не робить. Перевірено: `python3 .claude/unattended/settings_check.py` — «is sound», відрізняється лише в `permissions.allow` і `permissions.ask`; `python3 tests/test_settings_proposal.py` — 25 з 25; `tests/test_push_by_environment.py` — 103 з 103. Варто знати: `.claude/settings.json` належить двигуну, тож після наступного release WebFetch і WebSearch будуть дозволені без запитання і в кожному встановленому проєкті. Коментар `_comment_philosophy` у файлі досі каже, що вони живуть в особистому шарі: я його не міняв, бо ви просили решту файла лишити. Команда, якщо робити руками: `cp docs/tasks/settings.json .claude/settings.json && python3 tests/test_settings_proposal.py`, потім перезапустити Claude Code. sha256 пропозиції: `fefd8e1baec85de37cf1649383a9266b88e9952f259f04bf29f28b281f8a8cdf`. Звіт — `tasks/blocked/report-603-cloud-push-own-branch-and-web.md`.
Дію виконано (2026-10-09T20:40:46Z, runner): apply-settings — застосовано за відповіддю власника «так», перевірка після застосування зелена. Агентові: переконайся і закрий задачу звітом.
   Відповідь: так
