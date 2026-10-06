# 725 — Інші платні скрипти вимірювань: сесія, яку API не пустив, — помилка, а не результат

Залежить від: —
Аудит потрібен: ні
Відкритий пункт: eval-runners-failed-session-as-result

## Що сталося
Задача 014 виправила це в evals/run_audit_scenarios.py: сесія з is_error (401 «Failed to authenticate») записувалась як прогін без вердикту, файл — як complete. run_tester_evals.py, run_manager_evals.py, run_analyst_evals.py, run_simplifier_evals.py, run_second_opinion_evals.py на ту саму ваду не перевірено.

- Записано: 2026-10-06T18:56:02Z, агент

## Що зробити
Тест спершу на shim-і claude (відповідь з is_error і api_error_status 401): такий прогін — помилка, файл не complete. Потім найменша зміна в кожному скрипті, де тест червоний.

## Готово, коли
Описане вище зроблено і перевірено, або на нього є відповідь власника.

## Питання до власника
