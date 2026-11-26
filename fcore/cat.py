# -*- coding: utf-8 -*-
"""Котик (если пользователь АФК) и чтение клавиш."""

import contextlib
import os
import shutil
import sys
import time

from .term import GREY, RESET, USE, fg, hide_cursor, out, show_cursor, width
from .i18n import tr


# ───────────────────────── котик (если пользователь АФК) ─────────────────────────
IDLE_SECONDS = int(os.environ.get("FENTANYL_IDLE", "300"))  # 0 — выключено; /idle <сек>
IDLE_DEFAULT = IDLE_SECONDS

try:
    import select
    import termios
    import tty
except ImportError:  # Windows
    termios = None
try:
    import msvcrt
except ImportError:
    msvcrt = None


@contextlib.contextmanager
def cbreak():
    """Читаем клавиши сразу, без Enter и без эха (только Unix)."""
    if termios is None:
        yield
        return
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setcbreak(fd)
        yield
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)


def read_keys(timeout):
    """Ждёт нажатия до timeout сек. Вернёт набранные символы или None."""
    if termios is not None:
        fd = sys.stdin.fileno()
        r, _, _ = select.select([fd], [], [], timeout)
        if not r:
            return None
        return os.read(fd, 4096).decode("utf-8", "ignore")
    if msvcrt is not None:
        t0 = time.time()
        while time.time() - t0 < timeout:
            if msvcrt.kbhit():
                s = ""
                while msvcrt.kbhit():
                    s += msvcrt.getwch()
                return s
            time.sleep(0.05)
        return None
    return None


def idle_ok():
    return (IDLE_SECONDS > 0 and USE and sys.stdin.isatty()
            and (termios is not None or msvcrt is not None))


CAT_FACES = {"sad": ";_;", "happy": "^.^", "think": "o.o", "wow": "O.O"}


def cat_say(mood, msg=""):
    """Маленький котик с настроением (в обычном режиме без цветов не показывается)."""
    if not USE:
        return
    out(f"  {GREY} /\\_/\\{RESET}")
    out(f"  {GREY}( {fg(252)}{CAT_FACES.get(mood, '-.-')}{GREY} ){RESET}  {GREY}{msg}{RESET}")


def _cat_draw(art, caption, i=0, zs=0):
    w = width()
    h = shutil.get_terminal_size((60, 24)).lines
    top = max(3, h // 2 - 3)
    left = max(1, (w - 9) // 2 + 1)
    for r in range(top - 3, top + 8):
        out(f"\033[{r};1H\033[2K", "")
    for r, ln in enumerate(art):
        out(f"\033[{top + r};{left}H{fg(252)}{ln}{RESET}", "")
    for k in range(zs):  # плывущие «z»
        ch = "z" if k < 2 else "Z"
        out(f"\033[{top + 1 - k};{left + 10 + k * 2}H{fg(111 if k < 2 else 255)}{ch}{RESET}", "")
    out(f"\033[{top + 6};{max(1, (w - len(caption)) // 2 + 1)}H{GREY}{caption}{RESET}", "")


def cat_wake():
    """Котик просыпается и потягивается."""
    frames = [
        ([r"  /\_/\  ", r" ( o.o ) ", r"  > ^ <  ", r' (")_(") '], tr("мяу?")),
        ([r"  /\_/\  ", r"\( >.< )/", r"  > O <  ", r"  _/ \_  "], tr("потягиваюсь…")),
        ([r"  /\_/\  ", r" ( ^.^ ) ", r"  > ω <  ", r' (")_(") '], tr("доброе утро!")),
    ]
    for art, cap in frames:
        _cat_draw(art, cap)
        time.sleep(0.35)


def cat_sleep():
    """Спящий котик на отдельном экране. Любая клавиша — проснуться."""
    out("\033[?1049h", "")
    hide_cursor()
    try:
        i = 0
        while True:
            mouth = "^" if (i // 3) % 2 == 0 else "ω"  # дыхание
            art = [r"  /\_/\  ", r" ( -.- ) ", f"  > {mouth} <  ", r' (")_(") ']
            _cat_draw(art, tr("котик задремал  ·  нажми любую клавишу"), i, (i // 2) % 4)
            if read_keys(0.45) is not None:
                break
            i += 1
        cat_wake()
    finally:
        out("\033[?1049l", "")
        show_cursor()
