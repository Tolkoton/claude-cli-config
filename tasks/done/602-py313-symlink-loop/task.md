# 602 — Symlink loop під Python 3.13

Залежить від: —
Потрібна присутність власника: ні
Аудит потрібен: ні
Платні прогони: ні

## Що зробити
- /bugfix, продовження записів .engine/bugs/004-symlink-loop-traceback.md і .engine/bugs/005-resolve-loop-other-scripts.md (задачі 716 і 718). Ті виправлення зроблено й перевірено на сервері з Python 3.12.13. А з Python 3.13 Path.resolve() без strict на symlink loop нічого не кидає (зі strict=True кидає OSError з errno ELOOP), тоді як до 3.12 кидав RuntimeError, — тож код, що розпізнає loop за RuntimeError, на 3.13 вважає loop звичайним шляхом.
- Наслідок: під Python 3.13 швидкий набір тестів червоний — у tests/test_second_opinion.py падають дві перевірки board 716 про symlink loop, — і Stop gate не пускає жодну хмарну задачу (там Python 3.13), що змінює .py або .sh.
- Перевір кожне місце з тих двох виправлень (точно .claude/hooks/simplifier.py, _project_ref; також bugfix.py, lesson_queue.py, goals.py, board.py і решта зі списку запису 005) і зроби так, щоб symlink loop розпізнавався однаково на всіх версіях Python, які підтримує двигун, а поведінка для решти шляхів не змінилась.
- Місця поза тими двома виправленнями (doc_audit.py, evals/…) — це задача 719: не чіпай їх, у звіті лише скажи, чи підійде їй той самий спосіб.
- Гілка wip/718-… на origin — старий checkpoint уже закритої задачі 718; за основу її не бери.

## Готово, коли
- Тест на symlink loop однаково перевіряє і Python 3.13, і старіші версії та живе не лише в tests/test_second_opinion.py (задача 732 прибирає другу думку Gemini разом із її тестами).
- Під Python 3.13 bash tests/run_all.sh --fast зелений повністю.
- У звіті — усі перевірені місця і що з кожним зроблено.
