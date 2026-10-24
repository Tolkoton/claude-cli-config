# 1762 — settings.local.json.example: stale comment after board 302

Залежить від: —
Аудит потрібен: ні

## Що сталося
.claude/settings.local.json.example:11 says npm/yarn/pnpm add/remove are in .claude/settings.json's ask list; since board 302 (b21bfa3) they are not — only the global -g forms are.

- Записано: 2026-10-24T13:03:10Z, агент
- Це пропозиція, а не задача в черзі: runner із `tasks/proposed/` нічого не бере. У роботу її ставить власник — файлом із цим номером в inbox.

## Що зробити
Reword the _javascript _comment: the project's own manager adds/removes packages without asking; global installs (npm install -g, pnpm add -g, yarn global) are in ask.

## Готово, коли
Описане вище зроблено і перевірено, або на нього є відповідь власника.

## Питання до власника
