# Підсумок ночі 1

Режим нагляду: `attended` (файла `mode` немає). Увімкнути `unattended` мені не дозволив класифікатор
дозволів (самомодифікація), тож повертати було нічого. Нічого не відкочувалось і не push-илось; усі
commit-и нові, через `commit_checkpoint.sh`. Час — UTC.

## Що зроблено

| Частина | Гілка | Результат | Звіт |
|---|---|---|---|
| Пункт 0.1–0.2: сцени 02/04/10 як записані ходи, перевірка перед стартом | `unattended/2026-10-02-package-2b` (`371e02c`, `6408954`) | зроблено; `test_audit_turn_fixture` 53 | `docs/plan/night-1-item0-report.md` |
| Пакет А: єдиний скрипт воріт `gate.py` (4 шари, лічильник Stop → ескалація, захист від обходу, евали, еталон) | `unattended/2026-10-03-package-7` (`4d3f83f`…`0e2b0fa`) | 39 наборів зелені; золотий 87 тотожних + 9 нових; евали 12/12, 0 хибних блоків; ruff і mypy --strict чисті | `docs/plan/package-7-report.md` |
| Пакет Б: пам'ять (черга уроків, збирачі, розбір, просування правил через наглядача, застряг, витяжка, прибирання) | `unattended/2026-10-03-package-memory` (`449072d`…`d6b9947`) | 41 набір зелений; золотий 105/105 (96 + 9 нових); критик знайшов 2 блокуючі — виправлено | `docs/plan/package-memory-report.md` |

Гілки йдуть ланцюжком: 2б → package-7 (від `371e02c`) → package-memory (від `0e2b0fa`).

## Що відкладено (є в `.engine/overseer/parked.md` відповідних гілок)

1. **Пункт 0.3, повний платний аудит — не виконано.** Сесії Claude Code на цій машині не залогінені
   (`claude auth status`: `loggedIn: false`); спроба коштувала $0.00. Команда (на гілці 2б, після логіну):
   `python3 evals/run_audit_scenarios.py --engine-ref HEAD --runs 3 --out evals/baseline/Laos-MacBook-Pro/audit-v0.12.0-candidate.json --label "night 1 item 0.3"` (`--resume` після обриву; ≈ $20, ліміт $35),
   далі `python3 evals/compare_audits.py --before evals/baseline/Laos-MacBook-Pro/audit-v0.11.0.json --after evals/baseline/Laos-MacBook-Pro/audit-v0.12.0-candidate.json --must-fix 01,08`.
   Тому вердикти 02/04/10 проти очікуваних досі не виміряні.
2. **Лічильник «застряг» на результатах Bash** потребує запису в `.claude/settings.json`:
   `python3 docs/tasks/apply-lesson-hooks.py --dry-run`, потім без `--dry-run`, перезапуск Claude Code
   (гілка package-memory; тест `tests/test_lesson_hooks_proposal.py`).

## Що перевірити першим

1. Залогінитись і запустити аудит 0.3 (вище) — це єдина невиконана вимога програми.
2. Поведінку живого Stop-хука на пакеті А: `verify-on-stop.sh` тепер тонкий виклик `gate.py`; Stop став
   **інкрементальним** (оголошена різниця: помилка типів у незміненому залежному файлі — справа
   `pre_commit`/`ci`), а зміна lint/type-налаштувань чи новий `# type: ignore`/`# noqa`/skip/xfail
   блокується без `gate-allow: <причина>`. Подивіться `docs/plan/package-7-report.md`, розділ D4–D7.
3. Рішення D5: прапор `stop_hook_active` завершує роботу воріт лише поки лічильник сесії = 0 (інакше
   ескалація недосяжна). Записано AUTONOMOUS у `escalations.md`.
4. Пакет Б: носії замість нових записів у settings (SessionStart-витяжка живе в `env-check.sh`);
   «наглядач перевіряє пропозиції» — детермінована брама в `promote`, не новий текст наглядача.
   Існуючі проєкти не отримають `@.engine/rules.md` у CLAUDE.md автоматично.
5. `ruff`/`mypy` не встановлені: запускав через `uvx` (ефемерно, нічого не додано в маніфести).
