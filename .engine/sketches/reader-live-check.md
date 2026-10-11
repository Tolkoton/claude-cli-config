# Ескіз reader-live-check

## Питання
Чи підключено в чинному `.claude/settings.json` обидва hook-и агента-читача — `reader.py guard` і `reader.py record`?

## Що пробували
Коду під `sketches/` немає: питання про один файл налаштувань, і відповідає на нього один пошук рядків
`reader.py` у чинному `.claude/settings.json` (задача 099, жива перевірка після застосування пропозиції налаштувань).

## Команда і вивід
```
$ grep -n 'reader.py' .claude/settings.json
186:            "command": "python3 \"$CLAUDE_PROJECT_DIR/.claude/hooks/reader.py\" guard",
297:            "command": "python3 \"$CLAUDE_PROJECT_DIR/.claude/hooks/reader.py\" record",
```

## Відповідь
так
Рядок 186 виводу — команда `reader.py guard`, рядок 297 — команда `reader.py record`: обидва hook-и є у файлі.
