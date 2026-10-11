# Ескіз split-evenly

## Питання
Чи можна в `refproj.pricing` поділити суму на `parts` частин із точністю до цента так, щоб сума частин завжди точно дорівнювала `amount`, частини відрізнялися щонайбільше на один цент, а більші йшли першими — функцією `split_evenly(amount: Decimal, parts: int) -> list[Decimal]`, яка на `parts` менше одного або `amount` менше нуля дає `ValueError`?

## Що пробували
У `sketches/split-evenly/split_evenly.py` написано `split_evenly`: сума переводиться в цілі центи, `divmod(cents, parts)` дає базову частку й залишок, перші `залишок` частин отримують на один цент більше. Арифметика ціла, тож округлення немає взагалі — звідси точна сума. Функція бере `CENT` з `refproj.pricing`, тобто живе на тих самих `Decimal`, що й модуль.

`sketches/split-evenly/check.py` викликає її: друкує приклад 10.00 на 3; перебирає 2004 суми (кожен цент від 0.00 до 20.00, а також 999999999999.99, `Decimal("1E+3")` і `Decimal("7")`) на 1..40 частин і для кожної пари перевіряє п'ять властивостей (їх названо у виводі); друкує, що стається на `parts=0`, `parts=-2`, `amount=-0.01`. Невдачі збираються в список і друкуються — рядок `failures: 0 []` означає, що жодна пара не порушила жодної властивості.

Одна межа, яку ескіз виявив: сума з частками цента (10.005) не може дорівнювати сумі частин, кожна з яких — цілі центи. Ескіз на таку суму дає `ValueError` (останній рядок виводу); питання задачі про таку суму нічого не каже.

## Команда і вивід
```
$ PYTHONPATH=src uv run --offline python sketches/split-evenly/check.py
split_evenly(Decimal('10.00'), 3) = ['3.34', '3.33', '3.33']
inputs checked: 80160 (2004 amounts x parts 1..40)
per input: len == parts, sum == amount, max - min <= 0.01, descending, every share has 2 decimals
failures: 0 []
parts=0: ValueError: parts must be at least 1, got 0
parts=-2: ValueError: parts must be at least 1, got -2
amount=-0.01: ValueError: amount must not be negative, got -0.01
amount=10.005 (sub-cent): ValueError: amount must be a whole number of cents, got 10.005
```

## Відповідь
так
Рядок `failures: 0 []` після `inputs checked: 80160` каже, що сума частин дорівнює `amount`, різниця не більша за цент і більші частини перші на всіх перевірених входах; перший рядок дає 3.34, 3.33, 3.33; рядки `parts=0`, `parts=-2` і `amount=-0.01` показують обидві відмови. «Так» стосується сум у цілих центах — для суми з частками цента точна рівність неможлива за будь-якої реалізації.
