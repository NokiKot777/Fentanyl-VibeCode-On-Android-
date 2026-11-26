# -*- coding: utf-8 -*-
"""Инструменты проекта: файлы, grep, shell, diff, State, confirm."""

import difflib
import os
import re
import subprocess

from .anim import Spinner
from .term import ACCENT, BLUE, BOLD, GREY, RED, RESET, YELLOW, fg, out, prompt_safe, width
from .i18n import tr


# ───────────────────────── инструменты проекта ─────────────────────────
IGNORE_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", "dist", "build", ".idea", ".cache"}
MAX_FILE = 100_000
DANGER = [re.compile(p) for p in (
    r"\brm\s+-[a-zA-Z]*[rf][a-zA-Z]*\s+(/|~|\$HOME|\*)", r"\bmkfs", r"\bdd\s+if=", r":\(\)\s*\{",
    r">\s*/dev/(sd|nvme|mmcblk)", r"\bchmod\s+-R\s+777\s+/", r"(curl|wget)[^|]*\|\s*(sudo\s+)?(ba|z)?sh",
    r"\bgit\s+push\s+.*--force", r"\bgit\s+reset\s+--hard", r"\bshutdown\b|\breboot\b",
)]


def trim(s, n=6000):
    if len(s) <= n:
        return s
    h = n * 2 // 3
    return s[:h] + tr("\n… [обрезано {0} симв.] …\n").format((len(s) - n)) + s[-(n - h):]


def read_text_file(path, limit=MAX_FILE, strict=False):
    with open(path, "rb") as f:
        raw = f.read(limit + 1)
    if b"\0" in raw[:4096]:
        raise ValueError(tr("бинарный файл"))
    if len(raw) > limit:
        if strict:
            raise ValueError(tr("файл слишком большой"))
        return raw[:limit].decode("utf-8", "replace") + tr("\n… [файл обрезан]")
    return raw.decode("utf-8", "replace")


def in_project(path):
    root = os.path.realpath(os.getcwd())
    p = os.path.realpath(path)
    return p == root or p.startswith(root + os.sep)


def tree_lines(root=".", depth=2, limit=80):
    lines = []

    def walk(d, level, prefix):
        try:
            names = sorted(os.listdir(d), key=lambda x: (not os.path.isdir(os.path.join(d, x)), x.lower()))
        except OSError:
            return
        for nm in names:
            if nm in IGNORE_DIRS or nm.startswith("."):
                continue
            if len(lines) >= limit:
                return
            full = os.path.join(d, nm)
            isd = os.path.isdir(full)
            lines.append(f"{prefix}{nm}{'/' if isd else ''}")
            if isd and level < depth:
                walk(full, level + 1, prefix + "  ")

    walk(root, 1, "")
    if len(lines) >= limit:
        lines.append("…")
    return lines


def grep_tree(pattern, root=".", limit=100):
    rx = re.compile(pattern, re.I)
    hits = []
    for d, dirs, files in os.walk(root):
        dirs[:] = [x for x in dirs if x not in IGNORE_DIRS and not x.startswith(".")]
        for fn in files:
            p = os.path.join(d, fn)
            try:
                if os.path.getsize(p) > 1_000_000:
                    continue
                with open(p, "rb") as f:
                    raw = f.read()
                if b"\0" in raw[:4096]:
                    continue
                for i, ln in enumerate(raw.decode("utf-8", "replace").split("\n"), 1):
                    if rx.search(ln):
                        hits.append(f"{os.path.relpath(p, root)}:{i}: {ln.strip()[:200]}")
                        if len(hits) >= limit:
                            return hits, True
            except OSError:
                continue
    return hits, False


def run_shell(cmd, timeout=120):
    sp = Spinner([tr("выполняю")])
    sp.start()
    try:
        p = subprocess.run(cmd, shell=True, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                           stderr=subprocess.STDOUT, timeout=timeout)
        return p.returncode, p.stdout.decode("utf-8", "replace")
    except subprocess.TimeoutExpired as e:
        return -1, (e.stdout or b"").decode("utf-8", "replace") + tr("\n[таймаут {0} с]").format(timeout)
    except KeyboardInterrupt:
        return -2, tr("[прервано]")
    finally:
        sp.stop()


def show_output(txt, max_lines=30):
    lines = txt.rstrip("\n").split("\n") if txt.strip() else []
    for ln in lines[:max_lines]:
        out(f"  {GREY}│{RESET} {ln[:width() - 6]}")
    if len(lines) > max_lines:
        out(tr("  {0}│ … ещё {1} строк{2}").format(GREY, (len(lines) - max_lines), RESET))


def show_diff(old, new, path):
    if old is None:
        out(tr("  {0}новый файл{1} {2}").format(GREY, RESET, path))
        for ln in new.split("\n")[:30]:
            out(f"  {fg(114)}+ {ln}{RESET}")
        if new.count("\n") > 30:
            out(tr("  {0}… ещё {1} строк{2}").format(GREY, (new.count(chr(10)) - 30), RESET))
        return
    n = 0
    for ln in difflib.unified_diff(old.split("\n"), new.split("\n"), f"a/{path}", f"b/{path}", lineterm="", n=2):
        col = fg(114) if ln.startswith("+") and not ln.startswith("+++") else \
            RED if ln.startswith("-") and not ln.startswith("---") else \
            BLUE if ln.startswith("@@") else GREY
        out(f"  {col}{ln}{RESET}")
        n += 1
        if n >= 80:
            out(tr("  {0}… diff обрезан{1}").format(GREY, RESET))
            break
    if n == 0:
        out(tr("  {0}(без изменений){1}").format(GREY, RESET))


def ask_line(prompt):
    try:
        return input(prompt_safe(f"{prompt} {ACCENT}❯{RESET} "))
    except (EOFError, KeyboardInterrupt):
        out()
        return ""


class State:
    def __init__(self, cfg):
        self.cfg = cfg
        self.history = []
        self.attached = []     # (имя, текст) — уйдёт со следующим сообщением
        self.blocks = []       # блоки кода из ответов (для /save)
        self.undo = []         # (путь, старый текст или None)
        self.agent = bool(cfg.get("agent", True))
        self.auto_edit = False
        self.auto_run = False
        self.pending = ""      # заметка модели о том, что пользователь отклонил
        self.prev_dir = None   # прошлая папка проекта (для /cd -)
        self.fix_tries = 0     # сколько раз ИИ уже чинил найденную автопроверкой ошибку
        self.last_entry = None  # что запускала автопроверка в последний раз


def confirm(st, label, flag=None, danger=False, warn=""):
    """y/n/a. flag — 'edit' или 'run' (режим «всегда» на сессию)."""
    if warn:
        out(f"  {RED}⚠ {warn}{RESET}")
    if flag and not danger and not warn and getattr(st, "auto_" + flag):
        out(tr("  {0}авто ✓ {1}{2}").format(GREY, label, RESET))
        return True
    if danger:
        out(tr("  {0}⚠ опасная команда!{1}").format(RED, RESET))
        return ask_line(tr("  Напиши {0}yes{1}, чтобы выполнить").format(BOLD, RESET)).strip().lower() == "yes"
    hint = tr("y — да · n — нет") + (tr(" · a — всегда") if flag and not warn else "")
    ans = ask_line(f"  {label}? {GREY}{hint}{RESET}").strip().lower()
    if ans in ("a", "а", "always", "всегда") and flag and not warn:
        setattr(st, "auto_" + flag, True)
        out(tr("  {0}авто-режим «{1}» включён до конца сессии (/auto off){2}").format(YELLOW, flag, RESET))
        return True
    return ans in ("y", "yes", "д", "да")
