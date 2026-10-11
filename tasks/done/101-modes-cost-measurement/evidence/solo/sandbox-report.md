# Звіт — 010 Поділ суми на рівні частини

## Що змінилось для власника
У `refproj.pricing` з'явилась функція `split_evenly(amount: Decimal, parts: int) -> list[Decimal]`.
Вона ділить суму на `parts` частин із точністю до цента: сума частин точно дорівнює `amount`,
частини відрізняються щонайбільше на один цент, більші йдуть першими.
`parts` менше одного або від'ємний `amount` — `ValueError`.

## Демонстрація на хвилину
```
$ PYTHONPATH=src uv run python -c "from decimal import Decimal as D; from refproj.pricing import split_evenly as s; print(s(D('10.00'), 3)); print(s(D('0.05'), 7))"
[Decimal('3.34'), Decimal('3.33'), Decimal('3.33')]
[Decimal('0.01'), Decimal('0.01'), Decimal('0.01'), Decimal('0.01'), Decimal('0.01'), Decimal('0.00'), Decimal('0.00')]
```

Перевірки на фінальному коді:
- `uv run ruff check src tests` → `All checks passed!`
- `uv run mypy` → `Success: no issues found in 5 source files`
- `uv run pytest -q` → `17 passed` (було 4 тести `pricing`, додано 5 функцій-тестів, одна з них параметризована на 6 випадків)

RED перед кодом: `ImportError: cannot import name 'split_evenly'`.

Overseer: PASS на юніт 1, запит `20261011T162604Z-e3787b` (режим `соло`, один commit із робочим кодом).

## Витрати
Одна сесія builder-а і один запуск overseer-а (≈34 тис. токенів, 35 с). Суму в доларах сесія не бачить —
її рахує runner.

## Діапазон commit-ів
`49ebb0f..` цей commit: `bedbb0c` (код і тести) та commit закриття задачі (звіт, ledger, задача 700).

## Відкладене
- `tasks/todo/700-open-item-test-gap-…` — overseer знайшов брак тесту: відмова на `parts < 1` перевірена
  лише для `0`, а не для від'ємного числа. Код від'ємне `parts` відхиляє (overseer перевірив `-1` вручну);
  бракує лише тесту. Задачу відкрив скрипт overseer-а, вона чекає своєї черги.
- Поза умовою задачі, помічено overseer-ом, нічого не зроблено: `amount` `NaN` дає
  `decimal.InvalidOperation`, `Infinity` — `OverflowError` (не `ValueError`); для сум близько `1E+30`
  частини вже не точні до цента (межа 28 цифр контексту `Decimal`).

## Рішення, які я ухвалив сам
- **`amount`, дрібніший за цент (напр. `10.001`), — `ValueError`.** Задача цього випадку не описує.
  Частини з точністю до цента не можуть у сумі дати таку суму, тож відмова чесніша за мовчазне
  округлення. Змінити легко: одна перевірка у функції й один тест.
- Частини повертаються з двома знаками після коми (`Decimal('3.34')`), також коли `amount` передано як `Decimal('10')`.
- Тест на від'ємне `parts` у цей commit не дописував: код уже пройшов audit, а на цей брак є окрема задача 700.

## Які цілі вона просуває
Документ цілей `.engine/goals.md` ще порожній (версія 0, не затверджений), тож послатися нема на що.
