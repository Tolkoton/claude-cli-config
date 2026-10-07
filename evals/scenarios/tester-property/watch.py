

# --- appended by evals/run_tester_evals.py to the scene's RIGHT module: every call of a watched
# function is also given to the scene's wrong implementation, and a call on which the two differ
# (another value, another exception) is a call that reached the trap.
def _watch() -> None:
    import functools
    import importlib.util
    import os
    import sys

    spec = importlib.util.spec_from_file_location("_scene_wrong", os.environ["SCENE_WRONG"])
    assert spec is not None and spec.loader is not None
    wrong = importlib.util.module_from_spec(spec)
    sys.modules["_scene_wrong"] = wrong
    spec.loader.exec_module(wrong)

    def outcome(function, args, kwargs):  # type: ignore[no-untyped-def]
        try:
            return repr(function(*args, **kwargs))
        except Exception as exc:  # noqa: BLE001 - the kind of refusal is what is compared
            return type(exc).__name__

    def watched(name, right):  # type: ignore[no-untyped-def]
        @functools.wraps(right)
        def call(*args, **kwargs):  # type: ignore[no-untyped-def]
            differs = outcome(right, args, kwargs) != outcome(getattr(wrong, name), args, kwargs)
            with open(os.environ["SCENE_LOG"], "a", encoding="utf-8") as log:
                log.write("trap\n" if differs else "call\n")
            return right(*args, **kwargs)

        return call

    for name in os.environ["SCENE_WATCH"].split(","):
        globals()[name] = watched(name, globals()[name])


_watch()
