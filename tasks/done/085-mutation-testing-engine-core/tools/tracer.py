import sys as _s, os as _o
if not hasattr(_s, "_cov085"):
    _s._cov085 = 1
    try:
        _cur = open("/tmp/mut085/cov/current").read().strip()
    except OSError:
        _cur = ""
    if _cur:
        _dir = "/tmp/mut085/cov/" + _cur
        _o.makedirs(_dir, exist_ok=True)
        _T = frozenset(("gate.py", "overseer_verdict.py", "overseer_stop.py", "board.py", "engine.py", "lesson_queue.py"))
        def _line(code, line, _T=_T, _dir=_dir, _o=_o, _D=_s.monitoring.DISABLE):
            name = code.co_filename.rsplit("/", 1)[-1]
            if name in _T:
                fd = _o.open(_dir + "/" + name, _o.O_WRONLY | _o.O_APPEND | _o.O_CREAT, 0o644)
                _o.write(fd, b"%d\n" % line)
                _o.close(fd)
            return _D
        try:
            _s.monitoring.use_tool_id(1, "cov085")
            _s.monitoring.register_callback(1, _s.monitoring.events.LINE, _line)
            _s.monitoring.set_events(1, _s.monitoring.events.LINE)
        except Exception:
            pass
