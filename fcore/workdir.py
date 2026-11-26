# -*- coding: utf-8 -*-
"""Выбор папки проекта: ИИ работает только там, где скажет пользователь."""

import os
import sys

from .config import save_cfg
from .term import ACCENT, GREY, RED, RESET, YELLOW, box, hint, out, prompt_safe, short_path
from .tools import IGNORE_DIRS
from .i18n import tr

PAGE = 12
MAX_PROJECTS = 9  # сколько недавних проектов помним


def _safe(s):
    """Имя папки без управляющих символов (в имени может быть что угодно)."""
    return "".join(c for c in s if c.isprintable())


def remember(cfg, path):
    """Ставит проект в начало списка недавних."""
    lst = [p for p in cfg.get("projects", []) if isinstance(p, str) and p != path]
    cfg["projects"] = ([path] + lst)[:MAX_PROJECTS]


def recent(cfg, skip=()):
    return [p for p in cfg.get("projects", []) if isinstance(p, str) and p not in skip]


def projects_menu(cfg, current):
    """Меню проектов: открыть недавний, убрать из списка, добавить, обзор. Возвращает путь или None."""
    cur = os.path.realpath(current)
    while True:
        items = recent(cfg)
        rows = []
        for i, p in enumerate(items, 1):
            mark = f"{ACCENT}●{RESET}" if os.path.realpath(p) == cur else " "
            name = _safe(os.path.basename(p.rstrip(os.sep)) or p)[:14]
            tail = _safe(short_path(p, 34)) if os.path.isdir(p) else tr("{0}нет папки{1}").format(RED, RESET)
            rows.append(f"{ACCENT}{i}{RESET}  {mark} {name:<14} {GREY}{tail}{RESET}")
        if not items:
            rows.append(tr("{0}пока пусто — открой папку через /cd или b{1}").format(GREY, RESET))
        rows += ["", tr("{0}a{1}  добавить текущую   {2}b{3}  обзор папок").format(ACCENT, RESET, ACCENT, RESET)]
        out()
        box(rows, tr("Проекты"))
        hint(tr("номер — открыть · d номер — убрать из списка · Enter — отмена"))
        a = _ask(f"  {ACCENT}❯{RESET} ")
        if a is None or not a.strip():
            return None
        a = a.strip().lower()
        num = a[1:].strip() if a.startswith("d") else a
        if a.isdigit() and 1 <= int(a) <= len(items):
            p = check_dir(items[int(a) - 1])
            if p:
                return p
        elif a.startswith("d") and num.isdigit() and 1 <= int(num) <= len(items):
            gone = items[int(num) - 1]
            cfg["projects"] = [p for p in cfg.get("projects", []) if p != gone]
            save_cfg(cfg)
        elif a == "a":
            remember(cfg, cur)
            save_cfg(cfg)
        elif a in ("b", "и"):
            p = browse(cur)
            if p:
                return p
        else:
            out(tr("  {0}не понял: номер, d номер, a или b{1}").format(RED, RESET))


def _ask(prompt):
    """input() с отменой: None при Ctrl+C / Ctrl+D."""
    try:
        return input(prompt_safe(prompt))
    except (EOFError, KeyboardInterrupt):
        out()
        return None


def _yes(prompt):
    a = _ask(prompt)
    return a is not None and a.strip().lower() in ("y", "yes", "д", "да")


def subdirs(path):
    try:
        names = [n for n in os.listdir(path)
                 if not n.startswith(".") and n not in IGNORE_DIRS and os.path.isdir(os.path.join(path, n))]
    except OSError:
        return []
    return sorted(names, key=str.lower)


def check_dir(path):
    """Проверяет папку; возвращает абсолютный путь или None."""
    p = os.path.realpath(os.path.expanduser(path))
    if not os.path.isdir(p):
        out(tr("  {0}нет такой папки:{1} {2}").format(RED, RESET, short_path(p, 50)))
        return None
    if not os.access(p, os.R_OK | os.X_OK):
        out(tr("  {0}нет доступа к папке{1}").format(RED, RESET))
        return None
    if os.path.dirname(p) == p:
        out(tr("  {0}⚠ это корень диска{1} {2}— ИИ сможет менять любые файлы. Лучше выбрать папку проекта.{3}").format(RED, RESET, GREY, RESET))
        a = _ask(tr("  Напиши {0}yes{1}, если всё равно здесь {2}❯{3} ").format(YELLOW, RESET, ACCENT, RESET))
        if (a or "").strip().lower() != "yes":
            return None
    elif p == os.path.realpath(os.path.expanduser("~")):
        out(tr("  {0}это домашняя папка — ИИ увидит все твои файлы{1}").format(YELLOW, RESET))
        if not _yes(tr("  Всё равно здесь? {0}y/n{1} {2}❯{3} ").format(GREY, RESET, ACCENT, RESET)):
            return None
    if not os.access(p, os.W_OK):
        out(tr("  {0}нет прав на запись — ИИ сможет только читать{1}").format(YELLOW, RESET))
    return p


def browse(start):
    """Обзор папок. Возвращает выбранный путь или None."""
    path, page = os.path.realpath(start), 0
    while True:
        names = subdirs(path)
        pages = max(1, (len(names) + PAGE - 1) // PAGE)
        page = min(page, pages - 1)
        chunk = names[page * PAGE:(page + 1) * PAGE]
        rows = [f"{ACCENT}{short_path(path, 60)}{RESET}", f"{GREY}0   ..{RESET}"]
        rows += [f"{GREY}{i:<3}{RESET} {n}/" for i, n in enumerate(chunk, 1)]
        if not names:
            rows.append(tr("{0}(вложенных папок нет){1}").format(GREY, RESET))
        if pages > 1:
            rows.append(tr("{0}стр. {1}/{2} · m — дальше{3}").format(GREY, (page + 1), pages, RESET))
        out()
        box(rows, tr("Выбор папки"))
        hint(tr("номер — войти · Enter — выбрать эту · путь · n имя — создать · q — отмена"))
        a = _ask(f"  {ACCENT}❯{RESET} ")
        if a is None or a.strip().lower() in ("q", "й"):
            return None
        a = a.strip()
        if not a:
            p = check_dir(path)
            if p:
                return p
        elif a in ("0", ".."):
            path, page = os.path.dirname(path) or path, 0
        elif a.lower() == "m":
            page = (page + 1) % pages
        elif a.isdigit() and 1 <= int(a) <= len(chunk):
            path, page = os.path.join(path, chunk[int(a) - 1]), 0
        elif a.lower().startswith("n "):
            name = a[2:].strip()
            if not name or name in (".", "..") or os.sep in name or "/" in name:
                out(tr("  {0}имя папки без / и пробелов по краям{1}").format(RED, RESET))
                continue
            try:
                os.makedirs(os.path.join(path, name), exist_ok=True)
                path, page = os.path.join(path, name), 0
            except OSError as e:
                out(tr("  {0}не создать: {1}{2}").format(RED, (e.strerror or e), RESET))
        else:
            cand = os.path.expanduser(a)
            if not os.path.isabs(cand):
                cand = os.path.join(path, cand)
            if os.path.isdir(cand):
                path, page = os.path.realpath(cand), 0
            else:
                out(tr("  {0}нет такой папки{1}").format(RED, RESET))


def cli_dir():
    for a in sys.argv[1:]:
        if not a.startswith("-"):
            return a
    return None


def startup_dir(cfg):
    """Какую папку взять при запуске (спрашивает, если терминал интерактивный)."""
    cwd = os.path.realpath(os.getcwd())
    arg = cli_dir()
    if arg:
        p = check_dir(arg)
        if p:
            return p
    last = cfg.get("workdir")
    last = last if last and os.path.isdir(last) else None
    if not sys.stdin.isatty() or os.environ.get("FENTANYL_ASK") == "0":
        return os.path.realpath(last) if last else cwd
    opts = []
    if last and os.path.realpath(last) != cwd:
        opts.append((tr("последняя"), os.path.realpath(last)))
    opts.append((tr("здесь"), cwd))
    seen = {p for _, p in opts}
    for p in recent(cfg):  # недавние проекты тоже в стартовом меню
        rp = os.path.realpath(p)
        if rp not in seen and os.path.isdir(rp) and len(opts) < 6:
            opts.append((_safe(os.path.basename(rp))[:10] or tr("проект"), rp))
            seen.add(rp)
    rows = [f"{ACCENT}{i}{RESET}   {lab:<10}{GREY}{short_path(p, 42)}{RESET}" for i, (lab, p) in enumerate(opts, 1)]
    rows.append(tr("{0}b{1}   {2:<10}{3}выбрать другую папку{4}").format(ACCENT, RESET, tr("обзор"), GREY, RESET))
    out()
    box(rows, tr("Папка проекта — здесь работает ИИ"))
    while True:
        a = _ask(tr("  {0}Enter — 1 · номер · b · путь{1} {2}❯{3} ").format(GREY, RESET, ACCENT, RESET))
        a = "" if a is None else a.strip()
        if not a:
            a = "1"
        if a.isdigit() and 1 <= int(a) <= len(opts):
            p = check_dir(opts[int(a) - 1][1])
        elif a.lower() in ("b", "и", "обзор"):
            p = browse(opts[0][1])
        else:
            p = check_dir(a if os.path.isabs(os.path.expanduser(a)) else os.path.join(cwd, os.path.expanduser(a)))
        if p:
            return p


def enter(cfg, path):
    """Переходит в папку и запоминает её."""
    try:
        os.chdir(path)
    except OSError as e:
        out(tr("  {0}не удалось открыть папку: {1}{2}").format(RED, (e.strerror or e), RESET))
        return False
    cfg["workdir"] = path
    remember(cfg, path)
    save_cfg(cfg)
    return True
