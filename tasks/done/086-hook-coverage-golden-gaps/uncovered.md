# 086 — що досі не виконує жоден набір тестів і жоден сценарій golden set

Написав `evals/hook_coverage.py report … --json` після задачі 086, розклав за видами скрипт (кожне місце — рядок нижче, з назвою функції та першим рядком коду). Виконано 10279 рядків із 10706 (96.0 %) і 3341 гілок із 3568 (93.6 %). У shell-файлах рахуються лише рядки. Номери рядків — за станом коду на commit `293af67` (код hooks у задачі не мінявся).

| вид | місць | рядків | гілок | що це |
|---|---|---|---|---|
| environment | 84 | 173 | 0 | відмовила машина, а не код: файл не читається, інструмента немає або він не відповів за відведений час, модуля немає поруч (`except OSError`, `TimeoutExpired`, `ImportError` …). Гілка лише повертає «нічого» або пише попередження |
| root | 11 | 24 | 0 | у середовищі немає `CLAUDE_PROJECT_DIR`: скрипт питає git, далі бере поточну теку. Claude Code задає цю змінну кожному hook-у завжди |
| main-guard | 7 | 1 | 6 | рядок `if __name__ == "__main__"` модуля, який набори ще й імпортують: «не main» — це імпорт, а не поведінка |
| usage | 7 | 12 | 0 | підказка про використання для команди, яку набрали руками неправильно |
| bad-data | 21 | 47 | 0 | рядок файла стану, що не є JSON або має не ту форму, пропускається; читання йде далі |
| switched-off | 4 | 10 | 0 | налаштування, яке постачається вимкненим (`ALLOWED_FETCH_DOMAINS`, `FORCE_SEARCH_ALLOWED_DOMAINS` дорівнюють `None`) |
| one-way | 74 | 0 | 74 | умова, яку всі набори проходять лише з одного боку, а рядки по обидва боки виконано: інший бік — це цикл, що просто закінчився, або те саме рішення іншими словами |
| deferred | 48 | 71 | 0 | НЕ неважливе — відмова, відкат або гілка периметра, яка заслуговує власного тесту й не отримала його в задачі 086 (звіт, «Відкладене») |
| small | 75 | 89 | 0 | прочитано по одному: ранній вихід для порожнього чи відсутнього входу, примітка або відмова команди, яку набирають руками, гілка для другого інструмента (poetry, black, prettier), коли встановлено перший |

## .claude/hooks/auto-approve-web.py

- `host_of` lines 46-49 — **switched-off** — `try:`
- `emit` lines 57-58 — **environment** — `log(f"failed to serialize: {e}")`
- `handle_pre_tool_use` lines 92-94 — **switched-off** — `host = host_of(tool_input.get("url", ""))`
- `handle_pre_tool_use` lines 103-104 — **switched-off** — `updated_input = dict(tool_input)`
- `handle_pre_tool_use` lines 114 — **switched-off** — `result["hookSpecificOutput"]["updatedInput"] = updated_input`
- `main` lines 131-136 — **bad-data** — `except json.JSONDecodeError as e:`
- `<module>` line 159: перехід до кінця не виконано жодного разу — **main-guard** — `if __name__ == "__main__":`

## .claude/hooks/baseline.py

- `parse` line 98: перехід до 94 не виконано жодного разу — **one-way** — `if kept:`
- `load` lines 112-113 — **environment** — `except (OSError, UnicodeDecodeError) as exc:`
- `sealed` lines 128 — **small** — `return False`
- `cmd_record` line 273: перехід до 277 не виконано жодного разу — **one-way** — `if not in_session():`
- `cmd_tighten` lines 295 — **small** — `continue`
- `cmd_show` lines 315-316 — **small** — `print(f"baseline: {problem or f'no {BASELINE_REL}: the gate asks for clean'}")`

## .claude/hooks/bugfix.py

- `Run.failed` lines 70 — **small** — `return self.code is not None and self.code != 0 and self.code not in CANNOT_RUN`
- `project_root` lines 88 — **root** — `raise CannotCheck(f"{start} is not inside a git repository")`
- `base_of_record` lines 95-96 — **environment** — `except OSError as exc:`
- `base_of_record` lines 100 — **deferred** — `raise CannotCheck(f"{record} has no base_commit in its '## Complexity budget' section")`
- `checkout` lines 141 — **deferred** — `raise CannotCheck(f"the code of {sha[:7]} could not be checked out into a temporary copy")`
- `<module>` line 272: перехід до кінця не виконано жодного разу — **main-guard** — `if __name__ == "__main__":`

## .claude/hooks/complexity_budget.py

- `active_contract` line 199: перехід до 189 не виконано жодного разу — **one-way** — `if candidate and (root / candidate).is_file():`
- `active_contract` lines 201 — **small** — `return None`
- `function_metrics.measure.walk` lines 273 — **small** — `continue`
- `dependency_names` lines 345-346 — **bad-data** — `except tomllib.TOMLDecodeError:`
- `dependency_names` line 354: перехід до 353 не виконано жодного разу — **one-way** — `if isinstance(spec, str):  # {include-group = "..."} tables add no package`
- `parse_py` lines 364-365 — **bad-data** — `except (SyntaxError, ValueError):`
- `measure` line 375: перехід до 373 не виконано жодного разу — **one-way** — `if len(parts) == 2:`
- `measure` line 383: перехід до 381 не виконано жодного разу — **one-way** — `if added.isdigit() and deleted.isdigit():`
- `measure` lines 399 — **usage** — `usage.test_lines += net or 0`
- `measure` lines 406-407 — **environment** — `except OSError:`
- `measure` lines 421-422 — **usage** — `usage.unparseable.append(path)`
- `measure` lines 439-440 — **environment** — `except OSError:`
- `function_spans.visit` line 457: перехід до 460 не виконано жодного разу — **one-way** — `if not isinstance(child, ast.ClassDef):`
- `first_seen_limits` lines 518-519 — **environment** — `except OSError:`
- `accepted_overruns` lines 549 — **small** — `return []`
- `project_root` lines 717-718 — **root** — `top = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True, check=False)`
- `record_in_gate_format` lines 736-737 — **environment** — `except (ImportError, OSError):`
- `run_hook` lines 757-758 — **environment** — `except OSError:`
- `project_functions` lines 832-833 — **environment** — `except OSError:`
- `run_calibrate` lines 844-845 — **small** — `print("no production functions found: nothing to calibrate on")`
- `run_set_defaults` lines 868-869 — **usage** — `print("usage: complexity_budget.py set-defaults <max cyclomatic> <max nesting>", file=sys.stderr)`
- `main` lines 894-895 — **usage** — `print((__doc__ or "").split("\n\n")[0], file=sys.stderr)`

## .claude/hooks/contract_fingerprint.py

- `project_root` lines 38-39 — **root** — `top = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True, check=False)`
- `record_in_gate_format` lines 79-80 — **environment** — `except (ImportError, OSError):`
- `main` lines 105-106 — **usage** — `print((__doc__ or "").split("\n\n")[0], file=sys.stderr)`
- `<module>` line 117: перехід до кінця не виконано жодного разу — **main-guard** — `if __name__ == "__main__":`

## .claude/hooks/delete_guard.py

- `collect_change` lines 183-184 — **environment** — `except (OSError, UnicodeDecodeError):`
- `read_new` lines 195-196 — **environment** — `except (OSError, UnicodeDecodeError):`
- `definitions` lines 214 — **small** — `return None`
- `overlay` line 355: перехід до 352 не виконано жодного разу — **one-way** — `if text is not None:`
- `covered` lines 381 — **deferred** — `return ""`
- `covered` lines 385-386 — **deferred** — `unseen = unit.lines & entry["missing"] if entry["missing"] else unit.lines - entry["executed"]`
- `target_names` lines 418 — **deferred** — `return target, None`
- `target_names` lines 423-429 — **deferred** — `first, last = int(match["line"]), int(match["end"] or match["line"])`
- `tool_finding` lines 438-439 — **environment** — `except (OSError, ValueError) as exc:`
- `tool_finding` lines 442-443 — **deferred** — `known = ", ".join(f["id"] for f in result["findings"]) or "none"`

## .claude/hooks/gate.py

- `added_lines` lines 280 — **deferred** — `return None`
- `new_text` lines 306-307 — **environment** — `except (OSError, UnicodeDecodeError):`
- `tool_prefix` lines 336 — **small** — `return "poetry run "`
- `record_step` lines 361 — **deferred** — `break`
- `contract_grants` line 426: перехід до 425 не виконано жодного разу — **one-way** — `if valid_reason(match["reason"].strip()):`
- `guard_python` line 455: перехід до 452 не виконано жодного разу — **one-way** — `if added is None or line in added:`
- `toml_tools` lines 472 — **small** — `return {}`
- `toml_tools` lines 475-476 — **bad-data** — `except tomllib.TOMLDecodeError:`
- `guard_config` line 541: перехід до 548 не виконано жодного разу — **one-way** — `if old != new:`
- `guard_config` line 543: перехід до 548 не виконано жодного разу — **one-way** — `elif rel == ".claude/project.env":`
- `bypass_guard` line 621: перехід до 615 не виконано жодного разу — **one-way** — `if text is not None:`
- `check_steps` lines 676 — **small** — `return []`
- `write_report` lines 778-779 — **environment** — `except OSError as exc:`
- `write_count` lines 813-814 — **environment** — `except OSError:`
- `active_slice` line 831: перехід до 825 не виконано жодного разу — **one-way** — `if found:`
- `read_escalations` lines 843 — **small** — `data = {}`
- `open_escalation` lines 869-870 — **environment** — `except OSError as exc:`
- `board_question` lines 931-933 — **environment** — `except (ImportError, OSError, ValueError, TypeError, KeyError, AttributeError) as exc:`
- `ask_waiting` lines 954 — **small** — `continue`
- `ask_waiting` line 960: перехід до 964 не виконано жодного разу — **one-way** — `if asked:`
- `ask_waiting` lines 962-963 — **environment** — `except (ImportError, OSError, ValueError, TypeError, KeyError, AttributeError) as exc:`
- `park_escalation` lines 1000-1001 — **environment** — `except OSError as exc:`
- `lessons` line 1016: перехід до 1020 не виконано жодного разу — **one-way** — `elif action == "success":`
- `lessons` lines 1018-1019 — **environment** — `except (ImportError, OSError, ValueError, TypeError, KeyError, AttributeError):`
- `simplify_signals` lines 1039-1040 — **environment** — `except (ImportError, OSError, ValueError, TypeError, KeyError, AttributeError) as exc:`
- `layer_post_write` line 1076: перехід до 1085 не виконано жодного разу — **one-way** — `if tool_prefix(root) or shutil.which("ruff"):`
- `layer_post_write` lines 1089 — **deferred** — `notes.append(stuck)`
- `format_file` lines 1116-1118 — **small** — `elif shutil.which("black"):`
- `format_file` lines 1120 — **small** — `return False`
- `format_file` line 1125: перехід до 1129 не виконано жодного разу — **one-way** — `if proc.returncode == 0:`
- `format_file` lines 1128 — **small** — `quiet_run(["prettier", "--write", "--log-level", "silent", target])`
- `read_envelope` lines 1221 — **small** — `return {}`
- `emit_stop` lines 1249 — **small** — `print(extra["systemMessage"], file=sys.stderr)`
- `main` lines 1278 — **usage** — `parser.error("--layer is required")`
- `main` lines 1307 — **small** — `print(context)`

## .claude/hooks/gate_allows.py

- `added_since` lines 115 — **small** — `return None`
- `suppressions_by_line` lines 132-133 — **bad-data** — `except SyntaxError:`
- `suppressions_by_line` line 137: перехід до 134 не виконано жодного разу — **one-way** — `if kind not in found.setdefault(node.lineno, []):`
- `from_python` lines 145 — **small** — `return []`
- `default_base` line 224: перехід до 221 не виконано жодного разу — **one-way** — `if merge:`
- `default_base` lines 226 — **small** — `return "HEAD"`
- `collect` lines 245-246 — **environment** — `except (OSError, UnicodeDecodeError):`
- `collect` lines 255 — **small** — `found = [Allow(rel, 1, "contract", f"config change (granted by {grant[0]})", grant[1], True)]`
- `unit_files` lines 324 — **small** — `return set()`

## .claude/hooks/goals.py

- `unreconciled` lines 153 — **small** — `return []`
- `quote_error` lines 193 — **small** — `return "the answer names no 'Line:' or no 'Quote:'"`
- `project_root` lines 255-256 — **root** — `top = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True, check=False)`
- `cmd_check` lines 344-346 — **bad-data** — `except ValueError as exc:`
- `cmd_quote` lines 370-371 — **small** — `print(f"no such request: {rel}", file=sys.stderr)`
- `cmd_proposal` lines 385-386 — **small** — `print(f"no amendment is proposed ({PROPOSED_REL} absent)", file=sys.stderr)`
- `amend` line 421: перехід до 425 не виконано жодного разу — **one-way** — `if stale:`

## .claude/hooks/hotfix.py

- `declaration` lines 144 — **small** — `return f"{args.task} is not a file of this project"`
- `declaration` lines 153 — **small** — `return "--declared takes the owner's own words, as they were said"`
- `cmd_start` lines 175 — **deferred** — `return refuse(2, "no commit to measure the fix from: the hard limit is counted from HEAD")`
- `cmd_start` lines 178 — **deferred** — `return refuse(2, f"the card template {TEMPLATE} is missing")`
- `cmd_start` lines 197 — **deferred** — `print(f"  WARNING: .engine/PROGRESS.md marks another unit IN PROGRESS first ({active.name if active else 'unre`
- `cmd_debt` lines 250-251 — **environment** — `except budget.BudgetError as broken:`
- `cmd_debt` lines 259 — **deferred** — `return refuse(1, "the card does not say what is broken ('- Symptom:'): a reproduction, or the owner's words re`
- `cmd_debt` lines 264-266 — **deferred** — `commit = budget.git(root, "rev-parse", "--verify", "--quiet", f"{args.commit}^{{commit}}").strip()[:7]`
- `cmd_debt` line 272: перехід до 276 не виконано жодного разу — **one-way** — `if (tasks / "todo").is_dir():`
- `cmd_close` lines 300-301 — **small** — `print(f"ALREADY CLOSED: {debt.line}")`
- `cmd_close` line 310: перехід до 313 не виконано жодного разу — **one-way** — `if card_path.is_file():`

## .claude/hooks/lesson_queue.py

- `remember` line 159: перехід до 161 не виконано жодного разу — **one-way** — `if ident not in ids:`
- `current_slice` line 181: перехід до 178 не виконано жодного разу — **one-way** — `if match:`
- `add` lines 206 — **small** — `text += "\n"`
- `board_module` lines 376 — **small** — `return None`
- `owner_said_yes` lines 406 — **small** — `return False`
- `resolve` lines 439 — **small** — `return False, "engine feedback needs --text"`
- `resolve` lines 443 — **small** — `return False, "--to must be memory, rule, engine or discard"`
- `promote` lines 502 — **deferred** — `rules_path.unlink()`
- `journal` line 618: перехід до кінця не виконано жодного разу — **one-way** — `if board is not None:`
- `journal` lines 620-621 — **environment** — `except (ImportError, OSError, ValueError, TypeError, AttributeError):`
- `project_root` lines 692-693 — **root** — `top = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True, check=False)`
- `read_envelope` lines 698 — **small** — `return {}`
- `read_envelope` lines 701-702 — **bad-data** — `except ValueError:`
- `main` lines 740-741 — **small** — `for e in entries(root):`
- `main` line 767: перехід до 774 не виконано жодного разу — **one-way** — `elif args.command == "stuck":`
- `main` lines 771-773 — **environment** — `except OSError as exc:`

## .claude/hooks/maintain.py

- `_pairs` lines 92 — **small** — `continue`
- `_pairs` line 95: перехід до 90 не виконано жодного разу — **one-way** — `if row.get("name") and current and latest:`
- `run_command` lines 136-137 — **environment** — `except subprocess.TimeoutExpired:`
- `dependencies` line 162: перехід до 164 не виконано жодного разу — **one-way** — `if ready:`
- `dependencies` line 164: перехід до 166 не виконано жодного разу — **one-way** — `if rest:`
- `dependencies` lines 167 — **small** — `lines += ["", "Жодної застарілої залежності у виводі не розпізнано. Кінець виводу:", "'''", tail(out), "'''"]`
- `previous_report` lines 208-209 — **bad-data** — `except ValueError:`
- `proposals` lines 288 — **small** — `out.append("Покликати simplifier-а на різке зростання: " + "; ".join(calls) + ".")`
- `proposals` lines 293 — **small** — `out.append(f"Прибрати пам'ять і розібрати чергу уроків ({due}).")`

## .claude/hooks/overseer_phase.py

- `project_root` lines 35 — **root** — `return Path(__file__).resolve().parent.parent.parent`
- `<module>` line 82: перехід до кінця не виконано жодного разу — **main-guard** — `if __name__ == "__main__":`

## .claude/hooks/overseer_stop.py

- `_get_project_dir` lines 118-120 — **root** — `except (OSError, subprocess.TimeoutExpired):`
- `_build_check_cmd_re` lines 155 — **small** — `print(`
- `_build_code_extensions` lines 192 — **small** — `print(`
- `_open_gate_escalation` line 390: перехід до 397 не виконано жодного разу — **one-way** — `if unit is None:`
- `_open_gate_escalation` lines 395-396 — **environment** — `except (ImportError, OSError, ValueError, TypeError, KeyError, AttributeError):`
- `_gate_allow_review` lines 411-412 — **environment** — `except (ImportError, OSError, ValueError, TypeError, KeyError, AttributeError) as exc:`
- `_drop_request` lines 423-424 — **environment** — `except (ImportError, OSError, ValueError, TypeError, KeyError, AttributeError):`
- `_read_envelope` lines 459-460 — **environment** — `except (json.JSONDecodeError, ValueError, OSError):`
- `_read_envelope` lines 462 — **small** — `return {}`
- `_same_continue_message` line 513: перехід до 517 не виконано жодного разу — **one-way** — `if sha_file.read_text(encoding="utf-8").strip() == digest:`
- `_same_continue_message` lines 520-521 — **environment** — `except OSError:`
- `_testing_block` lines 559-560 — **environment** — `except (ImportError, OSError, ValueError, KeyError, TypeError):`
- `_contract_changed` lines 583-584 — **environment** — `except (OSError, IndexError):`
- `_lesson_request` lines 598-599 — **environment** — `except (ImportError, OSError, ValueError, TypeError, KeyError, AttributeError):`
- `_code_changed_in_tree` lines 628-629 — **environment** — `except (ImportError, OSError, ValueError, TypeError, KeyError, AttributeError):`

## .claude/hooks/overseer_verdict.py

- `project_root` lines 108-110 — **root** — `except (OSError, subprocess.TimeoutExpired):`
- `tree_fingerprint` lines 153-154 — **environment** — `except (OSError, subprocess.TimeoutExpired):`
- `tree_fingerprint` lines 165-166 — **environment** — `except OSError:`
- `_result_text` lines 191-193 — **small** — `if isinstance(content, list):`
- `turn_events` lines 207-208 — **bad-data** — `except ValueError:`
- `turn_events` line 209: перехід до 204 не виконано жодного разу — **one-way** — `if isinstance(record, dict) and record.get("type") in ("user", "assistant"):`
- `turn_events` lines 218 — **small** — `continue`
- `rows` lines 305-306 — **bad-data** — `except ValueError:`
- `rows` line 307: перехід до 302 не виконано жодного разу — **one-way** — `if isinstance(row, dict):`
- `board_task` lines 364-365 — **environment** — `except (ImportError, OSError, ValueError, AttributeError):`
- `active_slice` lines 384-385 — **environment** — `except (ImportError, OSError, ValueError):`
- `guard` line 448: перехід до 450 не виконано жодного разу — **one-way** — `if request:`
- `open_gate_escalation` lines 558-559 — **environment** — `except (ImportError, OSError, ValueError, TypeError, KeyError, AttributeError):`
- `settle` lines 571-572 — **environment** — `except (ImportError, OSError, ValueError, TypeError, KeyError, AttributeError):`
- `settle` lines 579-580 — **environment** — `except (ImportError, OSError, ValueError, TypeError, KeyError, AttributeError):`
- `_handed_back` lines 596-597 — **environment** — `except OSError:`
- `park` lines 676-677 — **environment** — `except OSError:`
- `board_item` lines 694-695 — **environment** — `except (ImportError, OSError, ValueError, TypeError, KeyError, AttributeError):`
- `read_envelope` lines 719-720 — **environment** — `except (ValueError, OSError):`
- `manual_request` line 735: перехід до 737 не виконано жодного разу — **one-way** — `if not turn_file.is_absolute() and not turn_file.exists():`
- `manual_request` lines 739-741 — **environment** — `except OSError as exc:`
- `manual_request` lines 743-744 — **deferred** — `print(f"{turn_file} is empty — there is no turn to audit", file=sys.stderr)`
- `manual_request` lines 750-751 — **environment** — `except (ImportError, OSError, ValueError, TypeError, KeyError, AttributeError) as exc:`
- `main` lines 795-797 — **environment** — `except Exception as exc:  # noqa: BLE001 — gate-allow: a hook must never break a turn; it reports and decides `

## .claude/hooks/park-ask-gated.py

- `project_dir` lines 88-89 — **root** — `try:`
- `project_dir` lines 93-97 — **root** — `if r.returncode == 0:`
- `main` lines 115 — **environment** — `except Exception:  # noqa: BLE001 — cannot read the call: do not decide, never fail closed here`
- `main` lines 118 — **small** — `sys.exit(0)`
- `main` line 122: перехід до 124 не виконано жодного разу — **one-way** — `if isinstance(tool_input, dict):`
- `<module>` line 147: перехід до кінця не виконано жодного разу — **main-guard** — `if __name__ == "__main__":`

## .claude/hooks/second_opinion.py

- `read_lines` lines 116-117 — **environment** — `except OSError:`
- `names_of` line 140: перехід до 142 не виконано жодного разу — **one-way** — `if own not in ("__init__", "__main__"):`
- `collect` lines 189-190 — **small** — `rows = diff.splitlines()`
- `parsed` lines 231-232 — **bad-data** — `except (ValueError, AttributeError, TypeError):`
- `parsed` lines 236-237 — **environment** — `except (KeyError, IndexError, TypeError, AttributeError):`
- `checked` lines 257 — **small** — `continue`
- `main` lines 357 — **small** — `raise KeyError("id")`
- `main` lines 371 — **small** — `print(text, end="")`

## .claude/hooks/shell_paths.py

- `Splitter.on_close` line 139: перехід до кінця не виконано жодного разу — **one-way** — `if len(self.stack) > 1:`
- `Lists.exists` lines 192 — **deferred** — `path = self.home + path[1:]`
- `Lists.exists` lines 194 — **deferred** — `return False`
- `wrapped_for_a_write` line 269: перехід до 267 не виконано жодного разу — **one-way** — `if (seg.call in OPENERS and has_mode(seg.words())) or seg.call in PATH_TAKERS or seg.method in WRITE_CALLS:`
- `verdict` line 291: перехід до 294 не виконано жодного разу — **one-way** — `if lists.home:`

## .claude/hooks/shell_readonly.py

- `Places.resolve` line 97: перехід до 100 не виконано жодного разу — **one-way** — `if self.home:`
- `git_write` line 184: перехід до 186 не виконано жодного разу — **one-way** — `if args[index] == "-C" and index + 1 < len(args):`
- `git_write` lines 196 — **deferred** — `target = ""`
- `<module>` line 265: перехід до кінця не виконано жодного разу — **main-guard** — `if __name__ == "__main__":`

## .claude/hooks/simplifier.py

- `_project_paths` line 143: перехід до 147 не виконано жодного разу — **one-way** — `if isinstance(item.get("evidence"), list):`
- `reference_exists` lines 158-159 — **environment** — `except OSError:`
- `second_log` lines 253-254 — **bad-data** — `except ValueError:`
- `second_log` line 255: перехід до 250 не виконано жодного разу — **one-way** — `if isinstance(row, dict):`
- `known_signal_ids` lines 281-282 — **environment** — `except (OSError, json.JSONDecodeError, KeyError, TypeError, AttributeError):`
- `request` lines 310 — **deferred** — `files = sorted({*budget.git(root, "diff", "--name-only", "HEAD").splitlines(),`
- `request` lines 315-317 — **deferred** — `outcome = budget.evaluate(root)`
- `route` lines 354-355 — **deferred** — `lines.append(f"\n### rejected by the validator ({len(result['rejected'])})\n")`
- `accept` lines 427-428 — **environment** — `except (OSError, ValueError) as exc:`
- `accept` lines 430 — **deferred** — `return 1, f"the verdict has {len(result['rejected'])} finding(s) the validator rejects; get a clean answer fir`
- `accept` line 443: перехід до 445 не виконано жодного разу — **one-way** — `if data.get("base_commit") != outcome.base_commit:`

## .claude/hooks/simplify_signals.py

- `run_tool` lines 73-74 — **environment** — `except (OSError, subprocess.TimeoutExpired):`
- `complexity_signals` lines 123-124 — **environment** — `except OSError:`
- `complexity_signals` lines 126 — **small** — `continue`
- `dependency_signals` lines 145-146 — **environment** — `except OSError:`
- `unused_dependency_signals` lines 173-174 — **environment** — `except (OSError, tomllib.TOMLDecodeError):`
- `unused_dependency_signals` lines 178 — **small** — `continue`
- `unused_dependency_signals` lines 181-182 — **environment** — `except OSError:`
- `duplication_signals` line 210: перехід до 207 не виконано жодного разу — **one-way** — `if len(places) >= 2:`
- `totals` lines 222-223 — **environment** — `except OSError:`
- `collect` lines 282-283 — **environment** — `except OSError:`

## .claude/hooks/test_touch.py

- `TestIndex.text` lines 66 — **small** — `parts.append(read_old(self.root, self.ref, rel) or "")`
- `TestIndex.text` lines 69-70 — **environment** — `except OSError:`
- `measure` lines 117 — **small** — `return None`
- `measure` lines 124-125 — **environment** — `except (OSError, subprocess.TimeoutExpired):`
- `run_coverage` lines 135 — **small** — `return None`
- `run_coverage` lines 147-148 — **environment** — `except OSError:`

## .claude/hooks/testing.py

- `wired` line 162: перехід до 160 не виконано жодного разу — **one-way** — `if WIRING_MARK in (root / ".claude" / name).read_text(encoding="utf-8"):`
- `rows` lines 181-182 — **bad-data** — `except ValueError:`
- `ledger_rows` lines 213-214 — **bad-data** — `except ValueError:`
- `ledger_rows` line 215: перехід до 210 не виконано жодного разу — **one-way** — `if isinstance(row, dict):`
- `invariant_facts` lines 317 — **deferred** — `facts["problems"] = found["problems"]`
- `check_invariants` lines 324-325 — **environment** — `except OSError as exc:`
- `feature_of` line 385: перехід до 382 не виконано жодного разу — **one-way** — `if item is not None:`
- `named_code` line 440: перехід до 438 не виконано жодного разу — **one-way** — `if (root / rel).is_file() and is_working_code(env, rel):`
- `changed_code` line 455: перехід до 452 не виконано жодного разу — **one-way** — `if current:`
- `changed_code` line 459: перехід до 452 не виконано жодного разу — **one-way** — `if match:`
- `changed_code` lines 465-466 — **environment** — `except OSError:`
- `changed_code` lines 470 — **small** — `continue`
- `tree_overlay` lines 489-490 — **environment** — `except (OSError, UnicodeDecodeError):`
- `branching_functions` lines 592 — **small** — `continue`
- `branching_functions` lines 595-596 — **environment** — `except (OSError, UnicodeDecodeError):`
- `branching_functions` line 597: перехід до 590 не виконано жодного разу — **one-way** — `if tree is not None:`
- `debts_of` lines 614 — **small** — `continue`
- `mandatory` line 705: перехід до 704 не виконано жодного разу — **one-way** — `if debt.get("due"):`
- `request_manager` line 866: перехід до 869 не виконано жодного разу — **one-way** — `if last(root, slug, "opened") is None:`
- `park_slice` lines 890 — **deferred** — `subprocess.run(`
- `run_test` lines 998-999 — **environment** — `except subprocess.TimeoutExpired:`
- `parse_answer` line 1014: перехід до 1009 не виконано жодного разу — **one-way** — `if isinstance(obj, dict):`
- `record_tests` lines 1149 — **deferred** — `lines.append("FINDING — these tests fail against the code that exists; they go to the builder as one package: `
- `review_task` line 1202: перехід до 1217 не виконано жодного разу — **one-way** — `if board.is_file() and (root / "tasks").is_dir():`
- `decision_lines` lines 1241 — **deferred** — `lines.append(f"a large block ({facts.get('block')}) WITHOUT a mutation check: MUTATION_CMD is not set")`
- `handed_back` lines 1302-1303 — **environment** — `except (ImportError, OSError, ValueError, AttributeError):`
- `feature_close` lines 1405 — **small** — `return 2, f"no such feature artifact: {path.relative_to(root)}"`
- `mutation` lines 1439-1441 — **environment** — `except subprocess.TimeoutExpired as exc:`
- `read_envelope` lines 1488-1489 — **bad-data** — `except ValueError:`
- `finish` line 1531: перехід до 1533 не виконано жодного разу — **one-way** — `if text:`
- `cmd_validate` lines 1554 — **small** — `return finish((2, f"no facts in {path}"))`
- `cmd_validate` lines 1557-1558 — **environment** — `except (OSError, ValueError) as exc:`
- `main` lines 1594-1595 — **small** — `path = root / LEDGER_REL`

## .claude/hooks/protect-paths.sh

- `<module>` lines 55-56 — **environment** — `echo "$REASON" >&2`

## .claude/unattended/board.py

- `consents` lines 279 — **small** — `return is_word(answer, CONSENT)`
- `import_inbox` lines 504 — **small** — `continue`
- `duplicate_lines` line 557: перехід до 555 не виконано жодного разу — **one-way** — `if number is not None:`

## .claude/unattended/board_review.py

- `git` lines 93-94 — **environment** — `except subprocess.TimeoutExpired:`
- `runner_alive` lines 256-262 — **deferred** — `try:`
- `task_line` line 267: перехід до 273 не виконано жодного разу — **one-way** — `if entry:`
- `runner_lines` lines 300 — **deferred** — `lines.append("- Увага: процесу runner-а з файла 'lock' на цій машині немає — запис стану міг застаріти.")`
- `debt_line` lines 346 — **small** — `return [f"- Борги термінових виправлень ('{hotfix.DEBT_REL}'): відкритих немає."]`
- `done_section` line 382: перехід до 384 не виконано жодного разу — **one-way** — `if len(closed) == 3:`
- `done_section` lines 389 — **small** — `lines += ["Звіту 'report.md' у теці немає.", ""]`
- `question_lines` lines 425 — **small** — `continue`
- `goals_section` lines 509-510 — **bad-data** — `except ValueError as broken:`
- `goals_section` line 515: перехід до 520 не виконано жодного разу — **one-way** — `if not asked and not lessons:`
- `goals_section` line 529: перехід до 531 не виконано жодного разу — **one-way** — `if src.show(goals.PROPOSED_REL):`
- `testing_section` line 558: перехід до 566 не виконано жодного разу — **one-way** — `if named:`
- `old_failures` lines 663-664 — **bad-data** — `except (ValueError, AttributeError, TypeError):`
- `context_lines.walk` lines 705 — **small** — `return`
- `context_lines.walk` lines 709 — **small** — `return`
- `golden_line` lines 769-770 — **bad-data** — `except ValueError:`
- `golden_line` line 773: перехід до 766 не виконано жодного разу — **one-way** — `if isinstance(results, list) and (newest is None or recorded > newest[0]):`

## .claude/unattended/board_state.py

- `read_output` lines 86-87 — **environment** — `except OSError:`
- `main` lines 168-169 — **usage** — `print((__doc__ or "").strip(), file=sys.stderr)`

## .claude/unattended/owner_action.py

- `gate_check` lines 163-164 — **environment** — `except (OSError, ValueError, KeyError):`
- `roll_back` line 177: перехід до 179 не виконано жодного разу — **one-way** — `if changed:`
- `roll_back` lines 182 — **deferred** — `return "файли повернуто з git; 'DEPS_RESTORE_CMD' порожня — встановлені пакети команда оновлення могла лишити `
- `update_group` lines 197-198 — **environment** — `except subprocess.TimeoutExpired:`
- `update_group` line 199: перехід до 202 не виконано жодного разу — **one-way** — `if ok:`
- `update_group` lines 211-212 — **deferred** — `log.append(f"- {names} — команда пройшла, перевірки зелені, але жодного файла проєкту вона не змінила: commit-`
- `update_group` lines 216-218 — **deferred** — `restored = roll_back(root, before, env.get("DEPS_RESTORE_CMD", "").strip())`
- `update_deps` lines 253 — **deferred** — `return result(EXIT_FAILED, f"Нічого не оновлено: '{UPDATES}' не читається як перелік оновлень.")`

## .claude/unattended/board-runner.sh

- `<module>` lines 295 — **deferred** — `git switch -q -c "$BRANCH" --track "$REMOTE/$BRANCH" || finish error - branch "cannot create $BRANCH from $REM`
- `save_wip` lines 532 — **deferred** — `event "wip-failed $stem"; WIP=""; return 0`

## .claude/unattended/commit_checkpoint.sh

- `<module>` lines 80 — **deferred** — `git switch -q "$BRANCH_NAME" || { echo "[checkpoint] cannot switch to $BRANCH_NAME" >&2; exit 1; }`

## engine.py

- `EngineSource.history` line 500: перехід до 517 не виконано жодного разу — **one-way** — `if self._history is None:`
- `plan_sync` line 717: перехід до 719 не виконано жодного разу — **one-way** — `if path == SETTINGS:`
- `plan_root_file` line 859: перехід до 861 не виконано жодного разу — **one-way** — `if RULES_IMPORT not in text:`
- `plan_root_file` line 861: перехід до 863 не виконано жодного разу — **one-way** — `if runs:`
- `plan_root_file` line 863: перехід до кінця не виконано жодного разу — **one-way** — `if parts:`
- `plan_root_file` lines 866 — **small** — `plan.notes.append(`
- `overseer_groups` lines 881 — **deferred** — `raise ValueError(f"'hooks.{event}' is not a list")`
- `overseer_groups` lines 885 — **deferred** — `raise ValueError(f"a group of 'hooks.{event}' has no list of handlers")`
- `plan_wiring` lines 899-900 — **bad-data** — `except ValueError:`
- `plan_wiring` lines 909 — **deferred** — `raise ValueError("it does not hold a JSON object")`
- `apply_plan` lines 983 — **deferred** — `target.unlink()`
- `config_home` lines 1046 — **root** — `return Path.home() / ".claude"`
- `read_json_object` lines 1053 — **environment** — `raise EngineError(f"{what} {path} cannot be read: {exc}") from None`
- `read_json_object` lines 1059 — **main-guard** — `raise EngineError(f"{what} {path} must hold a JSON object, not {type(data).__name__}")`
- `parse_personal` lines 1066-1067 — **bad-data** — `except ValueError as exc:`
- `parse_personal` lines 1069 — **deferred** — `raise EngineError(f"{where} must hold a JSON object")`
- `plan_personal` lines 1126 — **deferred** — `raise EngineError(f"{ref} ({commit[:7]}) has no {PERSONAL}; pass --ref with a newer tag, branch or commit")`
- `plan_personal` lines 1131 — **deferred** — `raise EngineError(f"{target} is not a regular file")`
- `cmd_update` lines 1249-1250 — **small** — `print(f"no projects listed in {projects_file()}; 'engine.py install' lists each project it installs")`
- `cmd_update` lines 1259-1261 — **environment** — `except EngineError as exc:`
- `cmd_status` lines 1280-1282 — **environment** — `except EngineError as exc:`
- `cmd_status` lines 1286 — **small** — `print(f"  note    {note}")`
- `newest_baseline` lines 1361 — **deferred** — `raise EngineError(f"no golden-set baseline ({RELEASE_BASELINES}) in this repository; pass --baseline FILE")`
- `last_full_audit` lines 1377-1378 — **environment** — `except (OSError, ValueError):`
- `last_full_audit` line 1382: перехід до 1374 не виконано жодного разу — **one-way** — `if commit:`
- `audit_gap` lines 1403-1404 — **bad-data** — `except (ValueError, KeyError, TypeError):`
- `record_bypass` lines 1421 — **deferred** — `raise EngineError(f"--without-audit could not be written into {RELEASE_JOURNAL}; nothing was released\n  {res.`
- `cmd_release` lines 1462 — **deferred** — `raise EngineError("HEAD moved while the checks ran; nothing was released")`
- `cmd_release` lines 1474 — **deferred** — `journal.unlink(missing_ok=True)`
- `cmd_release` lines 1487-1488 — **environment** — `except EngineError as exc:`

## install.sh

- `main` lines 110-111 — **small** — `printf 'Nothing to deploy: %s does not exist.\n' "$REPO_ROOT/user" >&2`
