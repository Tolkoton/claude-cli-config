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
