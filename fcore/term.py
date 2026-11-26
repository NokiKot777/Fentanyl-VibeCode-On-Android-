# -*- coding: utf-8 -*-
"""Цвета, темы и базовый вывод в терминал."""

import atexit
import os
import re
import shutil
import sys
import threading
import time

# Консоль в «не-UTF-8» (Windows и т.п.) не должна падать на рамках и значках
for _s in (sys.stdout, sys.stderr, sys.stdin):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass

try:  # стрелки, история и правка строки в input()
    import readline  # noqa: F401
    RL = sys.stdin.isatty()
except Exception:  # noqa: BLE001
    RL = False

_LOCK = threading.RLock()
ANIM = "--no-anim" not in sys.argv and os.environ.get("FENTANYL_ANIM", "1") != "0"
ANSI = re.compile(r"\033\[[0-9;?]*[A-Za-z]")


# ───────────────────────── цвета / терминал ─────────────────────────
PLAIN = "--plain" in sys.argv
FORCE = "--color" in sys.argv
USE = (not PLAIN) and (FORCE or (sys.stdout.isatty() and os.environ.get("NO_COLOR") is None))

if USE and os.name == "nt":
    os.system("")  # включает ANSI в Windows-консоли


def fg(n):
    return f"\033[38;5;{n}m" if USE else ""


RESET = "\033[0m" if USE else ""
BOLD = "\033[1m" if USE else ""
DIM = "\033[2m" if USE else ""
ACCENT_N = 121
ACCENT = fg(121)
WHITE = fg(255)
GREY = fg(244)
RED = fg(203)
YELLOW = fg(222)
BLUE = fg(111)
CODE = fg(187)

THEMES = {
    "mint":   dict(ACCENT=121, WHITE=255, GREY=244, RED=203, YELLOW=222, BLUE=111, CODE=187),
    "sunset": dict(ACCENT=209, WHITE=255, GREY=245, RED=196, YELLOW=221, BLUE=175, CODE=223),
    "ocean":  dict(ACCENT=45,  WHITE=255, GREY=244, RED=203, YELLOW=229, BLUE=75,  CODE=153),
    "grape":  dict(ACCENT=141, WHITE=255, GREY=245, RED=204, YELLOW=222, BLUE=111, CODE=183),
    "mono":   dict(ACCENT=252, WHITE=255, GREY=242, RED=252, YELLOW=250, BLUE=248, CODE=250),
}


def apply_theme(name):
    t = THEMES.get(name)
    if not t:
        return False
    vals = {"ACCENT_N": t["ACCENT"]}
    vals.update({k: fg(v) for k, v in t.items()})
    # цвета импортируются в другие модули копиями — обновляем их везде
    for mname, mod in list(sys.modules.items()):
        if mod is not None and (mname == __name__ or mname.startswith(__package__ + ".")):
            for k, v in vals.items():
                if k in vars(mod):
                    setattr(mod, k, v)
    return True


def out(s="", end="\n"):
    with _LOCK:
        try:
            sys.stdout.write(s + end)
            sys.stdout.flush()
        except (BrokenPipeError, ValueError):
            pass


def width():
    return max(30, shutil.get_terminal_size((60, 24)).columns)


def height():
    return max(8, shutil.get_terminal_size((60, 24)).lines)


def hide_cursor():
    if USE:
        out("\033[?25l", "")


def show_cursor():
    if USE:
        out("\033[?25h", "")


atexit.register(lambda: out(RESET + "\033[?25h", "") if USE else None)


def clear():
    if USE:
        out("\033[2J\033[H", "")


def set_anim(on):
    global ANIM
    ANIM = bool(on)


def anim_flag():
    return ANIM


def anim_on():
    """Анимации включены и терминал их поддерживает."""
    return USE and ANIM and sys.stdout.isatty()


def sleep(t):
    if anim_on():
        time.sleep(t)


def vlen(s):
    """Видимая длина строки (без ANSI-кодов)."""
    return len(ANSI.sub("", s))


def clip(s, n):
    """Обрезать по видимой длине, не ломая цветовые коды."""
    if vlen(s) <= n:
        return s
    res, vis, i = [], 0, 0
    while i < len(s) and vis < n - 1:
        m = ANSI.match(s, i)
        if m:
            res.append(m.group())
            i = m.end()
            continue
        res.append(s[i])
        vis += 1
        i += 1
    return "".join(res) + "…" + RESET


def hint(text, indent=2, color=None):
    """Серая подсказка с переносом по словам под ширину экрана."""
    import textwrap
    c = GREY if color is None else color
    for ln in textwrap.wrap(text, max(10, width() - indent - 1)) or [""]:
        out(" " * indent + c + ln + RESET)


def prompt_safe(p):
    """Цветной промпт для input(): иначе readline неверно считает длину строки."""
    return ANSI.sub(lambda m: "\001" + m.group() + "\002", p) if (USE and RL) else p


def short_path(p, n):
    home = os.path.expanduser("~")
    if p == home or p.startswith(home + os.sep):
        p = "~" + p[len(home):]
    return p if len(p) <= n else "…" + p[-(n - 1):]


def box(rows, title="", color=None, indent=2):
    """Рамка вокруг строк (строки могут содержать цвета)."""
    c = GREY if color is None else color
    w = max(24, min(width() - indent - 2, 72))
    inner = w - 4
    head = f" {title} " if title else ""
    if len(head) > w - 5:
        head = " " + head.strip()[:max(1, w - 9)] + "… "
    out(" " * indent + f"{c}╭─{RESET}{BOLD}{WHITE}{head}{RESET}{c}" + "─" * max(1, w - 3 - len(head)) + f"╮{RESET}")
    for r in rows:
        r = clip(r, inner)
        out(" " * indent + f"{c}│{RESET} {r}" + " " * (inner - vlen(r)) + f" {c}│{RESET}")
    out(" " * indent + f"{c}╰" + "─" * (w - 2) + f"╯{RESET}")
