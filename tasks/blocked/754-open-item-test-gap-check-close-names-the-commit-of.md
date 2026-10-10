# 754 — Брак тесту (overseer): check-close names the commit of unit 1 when unit 1 (src/a.py) was committed with no audit and only unit 2 (src/b.py, uncommitted at its request) got a PASS

Залежить від: —
Аудит потрібен: ні
Відкритий пункт: test-gap-check-close-names-the-commit-of-unit-1-when-unit-1-src-a-py-

## Що сталося
Overseer прийняв юніт `-|098-modes-check-close|unit 1` (PASS, запит `20261010T015728Z-02fe05`) і знайшов брак тесту: _seen falls back to the request's HEAD (mode.py:375). Any later PASS whose HEAD already holds the unaudited commit counts as having seen it; today this exits 0 (reproduced). Whether 'saw' should mean 'was in the audited diff' may need a decision Де: `tests/test_mode.py`. Вердикт — у `.engine/overseer/ledger.md`.

- Записано: 2026-10-10T02:16:58Z, overseer (overseer_verdict.py)

## Що зробити
Дописати перевірку «check-close names the commit of unit 1 when unit 1 (src/a.py) was committed with no audit and only unit 2 (src/b.py, uncommitted at its request) got a PASS»: тест червоніє на тому, що описано вище (_seen falls back to the request's HEAD (mode.py:375). Any later PASS whose HEAD already holds the unaudited commit counts as having seen it; today this exits 0 (reproduced). Whether 'saw' should mean 'was in the audited diff' may need a decision), і зелений на коді, як він є (покажи обидва прогони); код не міняти, якщо тест не знайде справжньої вади; швидкий набір тестів зелений.

## Готово, коли
Описане вище зроблено і перевірено, або на нього є відповідь власника.

## Питання до власника
1. Що вважати «PASS бачив цей commit» у `mode.py check-close` (задача 098)? Зараз так: commit задачі з робочим
   кодом покрито, якщо якийсь PASS цієї задачі (або без задачі — так записано audit у ході назад) бачив **той самий
   вміст** кожного його файла — як незакомічений або як у HEAD свого запиту. Звідси два наслідки:
   - **пізніший PASS покриває раніший commit без audit-у**, якщо запит уже мав цей commit у HEAD: вердикт говорить
     за все, що змінилось від останнього прийнятого PASS (`gate_allows.unit_files`). Це закріплено тестом
     (`tests/test_mode.py`, «a later PASS whose request already held the earlier commit covers it»);
   - **commit, на який був BLOCK, а потім виправлення з PASS, лишається «без PASS» назавжди**: PASS бачив новий
     вміст, а не той, що в commit-і. Runner паркує таку задачу з причиною `minimum`, і жодна відповідь не допоможе,
     поки ви не перенесете її руками (знайшов другий overseer задачі 098).
   Варіанти: (а) лишити, як є — суворо, але commit «до audit-у» з неправильним кодом тоді зупиняє задачу назавжди;
   (б) commit покрито ще й тоді, коли кожен його файл пізніше в тій самій задачі змінив commit, який сам покрито
   (виправлення замінило код, на який був BLOCK, — у гілці лишається лише перевірене); (в) вимагати PASS саме
   на диф кожного commit-у (лише файли, незакомічені в момент запиту) — найсуворіше: тоді й пізніший PASS не
   покриває раніший commit, а хід назад не зможе виправити commit без audit-у. Раджу (б): G2 — щоб у гілку не
   потрапив неперевірений код, а за (б) у кінцевому стані задачі лишається лише код, який бачив PASS; (в) зробило б
   хід назад марним. Що обираєте: (а), (б) чи (в)?
   Відповідь: (б).
