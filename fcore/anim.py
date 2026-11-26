# -*- coding: utf-8 -*-
"""Логотип, анимации, спиннер."""

import itertools
import math
import random
import re
import sys
import threading
import time

from .term import (
    ACCENT, ACCENT_N, ANSI, BOLD, GREY, RESET, USE, WHITE, anim_on, clear, clip, fg, height,
    hide_cursor, out, show_cursor, vlen, width,
)
from .i18n import tr


# ───────────────────────── логотип ─────────────────────────
LOGO = """                ▄▄▄███▀▀███▄▄▄
            ▄█▀▀▀            ▀▀█▄▄
         ▄█▀▀                    ▀▀▄▄
       ██████▀▀▀▀▀▀▀██████▀▀▀▀▀▀▀██████
      ▄█▀█████▄▄    ██████    ▄▄█████ █▄
     █▀█▄▄   ▀▀████▄██████▄████▀▀   ▄▄█▀█
    █▀ ████████████████████████████████ ▀█
   ▄█  █            ██████            █  █▄
   █   █            ██████            █   █
   █   █            ██████            █   █
   █   █           ▄██████▄           █   █
   █   █          ██████████          █   █
   █▄  █         ▄██████████▄         █  ▄█
   ▀█  █       ▄███ ██████▀███▄       █  █
    ▀█ █      ▄██▀  ██ ███  ███▄      █ █▀
     ▀██     ▄██▀   ██ ███   ▀██      ██▀
       █▄  ▄▄█▀     ██ ██▀     ██▄▄  ▄█
       █▀█▄▀▀▀       ████       ▀▀▀▄█▀█
       █▄▄███▄▄▄▄▄▄▄███████▄▄▄▄▄▄███▄▄█
             ▀▀█▄▄▄▄      ▄▄▄▄█▀▀
                  ▀▀▀▀▀▀▀▀▀▀""".split("\n")

NAME = "FENTANYL"
VERSION = "BETA"
AUTHOR = "SlimeCat"
CREDITS = [("Создатель", AUTHOR), ("Сделано с помощью", "Claude (Anthropic)")]

# ───────────────────────── анимации ─────────────────────────
GRAD = [240, 244, 248, 252, 255, 121, 85, 49, 43, 37]  # градиент для «волны»


def shimmer(text, shift=0):
    """Текст с бегущим бликом (в plain-режиме — как есть)."""
    if not USE:
        return text
    pal = [244, 247, 251, 255, ACCENT_N, 255, 251, 247, 244, 244, 244]
    return "".join(fg(pal[(k - shift) % len(pal)]) + ch for k, ch in enumerate(text)) + RESET


def grad_word(text):
    if not USE:
        return text
    return "".join(fg(GRAD[(k * 2 + 5) % len(GRAD)]) + ch for k, ch in enumerate(text)) + RESET


def logo_frame(shift):
    """Логотип с бегущей световой полосой."""
    lines = []
    for i, row in enumerate(LOGO):
        d = abs(((i - shift) % (len(LOGO) + 6)))
        if d < 3:
            col = fg(255)
        elif d < 5:
            col = fg(ACCENT_N)
        else:
            col = fg(244)
        lines.append(col + row + RESET)
    return lines


MINI = [  # маленький логотип для правого верхнего угла
    "  ▄▄████▄▄  ",
    " ██▀▀██▀▀██ ",
    " █   ██   █ ",
    " █   ██   █ ",
    " ▀█▄ ██ ▄█▀ ",
    "   ▀▀██▀▀   ",
]


def show_header():
    """Шапка: слева название и подсказки, справа в углу логотип."""
    w = width()
    left = [
        f"{BOLD}{grad_word(NAME)}{RESET} {ACCENT}{VERSION}{RESET}",
        f"{GREY}code anywhere{RESET}",
        "",
        tr("{0}/help — команды · /cd — папка{1}").format(GREY, RESET),
        tr("{0}/think — рассуждение · /clear{1}").format(GREY, RESET),
        "",
    ]
    mw = len(MINI[0])
    logo_ok = w >= 52
    out()
    for i, row in enumerate(MINI):
        text = clip(left[i], w - 4)
        if logo_ok:
            gap = max(1, w - 3 - 2 - vlen(text) - mw)
            logo = fg(GRAD[min(i + 4, len(GRAD) - 1)]) + row + RESET
            out("  " + text + " " * gap + logo)
        elif text:
            out("  " + text)
    out()


def _ease(p):
    return 1 - (1 - p) ** 3


def welcome(hello, name="", sub=""):
    """Анимированное приветствие: рамка растёт из центра, буквы «расшифровываются»
    из шума, по тексту бежит блик, вокруг мерцают звёзды. False — не поместилось/анимации выключены."""
    w, n = width(), 7
    if not anim_on() or height() < n + 6 or not hello:
        return False
    sub = sub[:max(0, w - 14)]
    iw = max(len(hello), len(sub)) + 4
    bw = iw + 2
    if bw + 4 > w:
        return False
    pad = " " * ((w - bw) // 2)
    stars_w = min(w - 2, bw + 10)
    spad = " " * ((w - stars_w) // 2)
    L = len(hello)
    ni = hello.find(name) if name else -1
    t_res = [int(i / max(1, L) * 14) + random.randint(0, 4) for i in range(L)]
    pool = "ABCDEFGHJKLMNPRSTUVXYZ#%&@$"
    edge = ACCENT + "│" + RESET

    def stars():
        cells = []
        for _ in range(stars_w):
            if random.random() < 0.10:
                cells.append(fg(random.choice((240, 245, 250, 255, ACCENT_N))) + random.choice("·+*•˙") + RESET)
            else:
                cells.append(" ")
        return spad + "".join(cells)

    def border(cur, left, right):
        return pad + " " * ((iw - cur) // 2) + ACCENT + left + "─" * cur + right + RESET

    def inner(content, vis):
        a = (iw - vis) // 2
        return pad + edge + " " * a + content + " " * (iw - vis - a) + edge

    def text_row(f, shim=None):
        cells = []
        for i, ch in enumerate(hello):
            isname = ni >= 0 and ni <= i < ni + len(name)
            if ch.isalnum() and f < t_res[i]:  # ещё «шум»
                cells.append(fg(random.choice((238, 241, 244))) + random.choice(pool) + RESET)
            elif ch.isalnum() and f == t_res[i]:  # вспышка при появлении
                cells.append(BOLD + WHITE + ch + RESET)
            else:
                near = shim is not None and abs(i - shim) <= 2
                if isname:
                    cells.append(BOLD + (WHITE if near else ACCENT) + ch + RESET)
                else:
                    cells.append((fg(ACCENT_N) if near else WHITE) + ch + RESET)
        return inner("".join(cells), L)

    def sub_row(k):
        return inner(GREY + sub[:k] + RESET, k)

    def draw(rows):
        out(f"\033[{n}A", "")
        for r in rows:
            out("\033[2K" + r)

    empty = pad + edge + " " * iw + edge
    for _ in range(n):
        out()
    hide_cursor()
    try:
        for k in range(1, 11):  # 1) рамка растёт из центра
            cur = max(2, int(iw * _ease(k / 10)))
            draw([stars(), border(cur, "╭", "╮"), "", "", "", border(cur, "╰", "╯"), stars()])
            time.sleep(0.025)
        for f in range(max(t_res) + 2):  # 2) буквы собираются из шума
            draw([stars(), border(iw, "╭", "╮"), empty, text_row(f), empty, border(iw, "╰", "╯"), stars()])
            time.sleep(0.035)
        for s in range(max(L + 6, len(sub) // 2 + 1)):  # 3) блик по тексту + подпись «печатается»
            draw([stars(), border(iw, "╭", "╮"), empty, text_row(10 ** 6, s - 3),
                  sub_row(min(len(sub), (s + 1) * 2)), border(iw, "╰", "╯"), stars()])
            time.sleep(0.03)
    except KeyboardInterrupt:
        pass
    finally:
        draw(["", border(iw, "╭", "╮"), empty, text_row(10 ** 6), sub_row(len(sub)), border(iw, "╰", "╯"), ""])
        show_cursor()
    return True


def show_credits():
    """Экран «о программе»: версия, создатель, помощник."""
    from .term import box
    rows = [f"{BOLD}{grad_word(NAME)}{RESET}  {ACCENT}{VERSION}{RESET}", ""]
    rows += [f"{GREY}{tr(k):<18}{RESET}{WHITE}{v}{RESET}" for k, v in CREDITS]
    out()
    box(rows, tr("О программе"), ACCENT)
    out()


def wipe():
    """Экран загрузки «сматывается» сверху вниз."""
    if not anim_on():
        return
    for r in range(1, height() + 1):
        out(f"\033[{r};1H\033[2K", "")
        time.sleep(0.006)
    out("\033[H", "")


def _logo_intro(w):
    """Логотип «собирается» из шума, потом по нему бежит блик."""
    pad = " " * max(0, (w - 46) // 2)
    n = len(LOGO)
    cols = max(len(r) for r in LOGO)
    glyphs = "░▒▓█#%&@*+"
    for _ in LOGO:
        out()
    frames = 14
    for f in range(frames + 1):
        out(f"\033[{n}A", "")
        edge = f / frames * (cols + 8)
        for i, row in enumerate(LOGO):
            r = max(0, int(edge - 8))
            e = min(len(row), int(edge))
            noise = "".join(" " if ch == " " else random.choice(glyphs) for ch in row[r:e])
            out("\033[2K" + pad + fg(GRAD[min(i // 2, len(GRAD) - 1)]) + row[:r] + fg(255) + noise + RESET)
        time.sleep(0.035)
    for f in range(n + 6):  # бегущая световая волна
        out(f"\033[{n}A", "")
        for ln in logo_frame(f):
            out("\033[2K" + pad + ln)
        time.sleep(0.03)
    for _ in range(3):  # короткий глитч
        out(f"\033[{n}A", "")
        for row in LOGO:
            shift = random.choice([0, 1, 2, -1]) if random.random() < 0.2 else 0
            s = (" " * shift + row) if shift >= 0 else row[1:]
            out("\033[2K" + pad + fg(random.choice([255, 121, 203, 111])) + s + RESET)
        time.sleep(0.05)
    out(f"\033[{n}A", "")
    for row in LOGO:
        out("\033[2K" + pad + ACCENT + row + RESET)


def boot():
    w = width()
    if not USE:
        out(f"{NAME} {VERSION}")
        return
    if not anim_on():
        return  # шапку нарисует main()
    clear()
    hide_cursor()
    try:
        if w >= 48 and height() >= len(LOGO) + 8:
            _logo_intro(w)
        else:  # маленький экран — без логотипа, чтобы не ломать вывод
            out()
        title = " ".join(NAME)
        out(" " * max(0, (w - len(title)) // 2), "")
        for ch in title:
            out(BOLD + WHITE + ch + RESET, "")
            time.sleep(0.04)
        out()
        sub = f"code anywhere  ·  {VERSION}  ·  by {AUTHOR}"
        out(" " * max(0, (w - len(sub)) // 2) + GREY + sub + RESET)
        out()
        bw = min(30, w - 14)
        padb = " " * max(0, (w - bw - 6) // 2)
        for i in range(bw + 1):
            bar = ACCENT + "█" * i + GREY + "░" * (bw - i) + RESET
            out(f"\r{padb}{bar} {int(i / bw * 100):3d}%", "")
            time.sleep(0.012)
        out()
        time.sleep(0.25)
        wipe()
    finally:
        show_cursor()


STYLES = {
    "dots": lambda i: "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"[i % 10],
    "orbit": lambda i: "◜◠◝◞◡◟"[i % 6],
    "wave": lambda i: "".join("▁▂▃▄▅▆▇█"[int((math.sin(i * 0.5 + j * 0.9) + 1) / 2 * 7.99)] for j in range(5)),
    "bounce": lambda i: "".join("●" if k == (i % 8 if i % 8 < 5 else 8 - i % 8) else "·" for k in range(5)),
    "pulse": lambda i: ("·  ", "·· ", "···", " ··", "  ·", "   ")[i % 6],
}


class Spinner:
    WORDS = ["думаю", "читаю код", "пишу", "проверяю", "собираю"]

    def __init__(self, words=None, style=None):
        self.stop_ev = threading.Event()
        self.th = None
        self.words = words or self.WORDS
        self.style = style if style in STYLES else random.choice(list(STYLES))

    def _run(self):
        t0 = time.time()
        frame = STYLES[self.style]
        for i in itertools.count():
            if self.stop_ev.is_set():
                break
            el = time.time() - t0
            word = tr(self.words[int(el // 2.5) % len(self.words)])
            text = shimmer(word + "." * (i // 4 % 4), i // 2)
            tm = tr(" {0}{1} с{2}").format(GREY, int(el), RESET) if el >= 2 else ""
            col = fg(GRAD[(i // 2) % len(GRAD)])
            out(clip(f"\r\033[2K  {col}{frame(i)}{RESET} {text}{tm}", width() - 1), "")
            time.sleep(0.08)
        out("\r\033[2K", "")

    def start(self):
        if not anim_on():
            out(GREY + "  …" + RESET)
            return
        hide_cursor()
        self.th = threading.Thread(target=self._run, daemon=True)
        self.th.start()

    def stop(self):
        if self.th:
            self.stop_ev.set()
            self.th.join()
            self.th = None
            show_cursor()


def sweep_divider():
    """Тонкая линия-разделитель; по ней пробегает блик."""
    n = max(10, min(width() - 4, 60))
    if not anim_on():
        out(f"  {GREY}" + "─" * n + RESET)
        return
    hide_cursor()
    try:
        for p in range(-4, n + 4, 3):
            line = "".join((fg(255) if abs(k - p) <= 1 else fg(ACCENT_N) if abs(k - p) <= 3 else fg(238)) + "─"
                           for k in range(n))
            out("\r  " + line + RESET, "")
            time.sleep(0.012)
        out("\r  " + GREY + "─" * n + RESET)
    finally:
        show_cursor()


def ok_line(msg):
    """✓ с короткой «вспышкой»."""
    msg = clip(msg, width() - 6)
    if anim_on():
        for sym in ("·", "•", "●"):
            out(f"\r\033[2K  {ACCENT}{sym}{RESET} {GREY}{msg}{RESET}", "")
            time.sleep(0.05)
        out("\r\033[2K", "")
    out(f"  {ACCENT}✓{RESET} {msg}")


def typewriter(text, delay=0.012):
    """Печать «машинкой»; цветовые коды выводятся мгновенно."""
    if not anim_on():
        out(text)
        return
    for tok in re.split(r"(\033\[[0-9;?]*[A-Za-z])", text):
        if ANSI.fullmatch(tok):
            out(tok, "")
        else:
            for ch in tok:
                out(ch, "")
                time.sleep(delay if ch != " " else delay / 2)
    out(RESET)


def bye(msg=None):
    msg = tr("пока!") if msg is None else tr(msg)
    if not anim_on():
        out(f"{GREY}{msg}{RESET}")
        return
    for c in (236, 239, 242, 245, 248, 251, 255):
        out(f"\r\033[2K  {fg(c)}{msg}{RESET}", "")
        time.sleep(0.05)
    out(f"\r\033[2K  {ACCENT}{msg}{RESET}")
