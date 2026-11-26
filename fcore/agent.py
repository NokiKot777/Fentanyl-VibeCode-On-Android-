# -*- coding: utf-8 -*-
"""Агент: действия модели (edit / write / run / read)."""

import os
import re

from .term import ACCENT, BLUE, CODE, GREY, RED, RESET, YELLOW, out
from .tools import (
    DANGER, confirm, in_project, read_text_file, run_shell, show_diff, show_output, trim,
)
from .i18n import tr


# ───────────────────────── агент: действия модели ─────────────────────────
AGENT_PROMPT = """You can act on the user's project through special fenced blocks. The CLI runs them after the user confirms.
- Run a shell command:
```run
command
```
- Edit a file (SEARCH must match the existing text exactly; include a few lines of context; several pairs allowed):
```edit path/to/file
<<<<<<< SEARCH
old text
=======
new text
>>>>>>> REPLACE
```
- Create or overwrite a whole file:
```write path/to/file
full content
```
- Read a file:
```read path/to/file
```
Rules: at most 4 blocks per answer; after the blocks stop and wait for the results; use ordinary ```lang blocks for examples that must NOT be executed; keep answers short; reply in the user's language."""

# Стиль «как у человека»: сначала пояснение/план, потом действия, комментарии в коде
COMMENT_PLAN = ("Working style: never begin an answer with an action block. First write a short comment "
                "(1-3 sentences, in the user's language) saying what you are about to do. When asked to create "
                "a project or several files, first give a brief plan (the file list, at most 8 short bullets), "
                "then create the files. After the results, finish with a one-line summary.")
COMMENT_CODE = ("In code you write, add short helpful comments in the user's language for non-obvious parts "
                "(not on every line).")

SR = re.compile(r"<<<<<<< SEARCH\n(.*?)\n?=======\n(.*?)\n?>>>>>>> REPLACE", re.S)


def apply_blocks(text, code):
    pairs = SR.findall(code)
    if not pairs:
        raise ValueError(tr("нет блоков SEARCH/REPLACE"))
    lines = text.split("\n")
    for k, (sr, rp) in enumerate(pairs, 1):
        sl = sr.split("\n") if sr else []
        if not sl:
            raise ValueError(tr("блок {0}: пустой SEARCH допустим только для нового файла").format(k))
        rl = rp.split("\n") if rp != "" else []
        n = len(sl)
        hits = []
        for strip in (False, True):
            key = (lambda x: x.strip()) if strip else (lambda x: x)
            tgt = [key(x) for x in sl]
            hits = [i for i in range(len(lines) - n + 1) if [key(x) for x in lines[i:i + n]] == tgt]
            if hits:
                break
        if not hits:
            raise ValueError(tr("блок {0}: SEARCH не найден в файле").format(k))
        if len(hits) > 1:
            raise ValueError(tr("блок {0}: найдено {1} совпадений — добавь контекста").format(k, len(hits)))
        lines[hits[0]:hits[0] + n] = rl
    return "\n".join(lines)


def _write_file(st, path, old, new, crlf):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    data = new.replace("\n", "\r\n") if crlf else new
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(data)
    st.undo.append((path, old, crlf))


def _change_file(st, kind, path_arg, new_text_fn):
    path = os.path.abspath(os.path.expanduser(path_arg))
    old, crlf = None, False
    if os.path.isfile(path):
        try:
            old = read_text_file(path, 2_000_000, strict=True)
        except Exception as e:  # noqa: BLE001
            return tr("[{0} {1}] не удалось прочитать: {2}").format(kind, path_arg, e), "fail"
        crlf = "\r\n" in old
        old = old.replace("\r\n", "\n")
    try:
        new = new_text_fn(old)
    except ValueError as e:
        out(f"  {RED}✗ {kind} {path_arg}: {e}{RESET}")
        return tr("[{0} {1}] ошибка: {2}").format(kind, path_arg, e), "fail"
    out(f"  {YELLOW}✎ {kind}{RESET} {path_arg}")
    show_diff(old, new, path_arg)
    warn = "" if in_project(path) else tr("файл вне папки проекта")
    if old is not None and new == old:
        return tr("[{0} {1}] без изменений").format(kind, path_arg), "ok"
    if not confirm(st, tr("Применить"), "edit", warn=warn):
        return tr("[{0} {1}] пользователь отклонил").format(kind, path_arg), "declined"
    try:
        _write_file(st, path, old, new, crlf)
    except OSError as e:
        return tr("[{0} {1}] ошибка записи: {2}").format(kind, path_arg, e), "fail"
    out(tr("  {0}✓{1} сохранено {2}(/undo — откатить){3}").format(ACCENT, RESET, GREY, RESET))
    return tr("[{0} {1}] применено").format(kind, path_arg), "ok"


def act_edit(st, path_arg, code):
    if not path_arg:
        return tr("[edit] не указан путь"), "fail"

    def make(old):
        if old is None:  # новый файл: единственный блок с пустым SEARCH
            pairs = SR.findall(code)
            if len(pairs) == 1 and pairs[0][0] == "":
                return pairs[0][1] + "\n" if pairs[0][1] else ""
            raise ValueError(tr("файла нет; для создания используй write"))
        return apply_blocks(old, code)

    return _change_file(st, "edit", path_arg, make)


def act_write(st, path_arg, code):
    if not path_arg:
        return tr("[write] не указан путь"), "fail"
    return _change_file(st, "write", path_arg, lambda old: code.rstrip("\n") + "\n")


def act_run(st, cmd):
    cmd = cmd.strip()
    if not cmd:
        return tr("[run] пустая команда"), "fail"
    danger = any(rx.search(cmd) for rx in DANGER)
    out(f"  {YELLOW}▶ run{RESET}")
    for ln in cmd.split("\n"):
        out(f"  {GREY}│{RESET} {CODE}{ln}{RESET}")
    if not confirm(st, tr("Выполнить"), "run", danger=danger):
        return tr("[run] $ {0}\nпользователь отклонил").format(cmd), "declined"
    rc, txt = run_shell(cmd)
    show_output(txt)
    mark = f"{ACCENT}✓{RESET}" if rc == 0 else tr("{0}✗ код {1}{2}").format(RED, rc, RESET)
    out(f"  {mark}")
    return tr("[run] $ {0}\nкод выхода: {1}\n{2}").format(cmd, rc, trim(txt)), "ok"


def act_read(st, path_arg):
    if not path_arg:
        return tr("[read] не указан путь"), "fail"
    path = os.path.abspath(os.path.expanduser(path_arg))
    if not in_project(path):
        out(tr("  {0}✗ read {1}: вне папки проекта{2}").format(RED, path_arg, RESET))
        return tr("[read {0}] отказано: файл вне папки проекта").format(path_arg), "fail"
    try:
        txt = read_text_file(path)
    except Exception as e:  # noqa: BLE001
        out(f"  {RED}✗ read {path_arg}: {e}{RESET}")
        return tr("[read {0}] ошибка: {1}").format(path_arg, e), "fail"
    out(tr("  {0}◦ read{1} {2} {3}({4} строк){5}").format(BLUE, RESET, path_arg, GREY, (txt.count(chr(10)) + 1), RESET))
    return f"[read {path_arg}]\n{txt}", "ok"


ICONS = {"write": "+ создать", "edit": "✎ изменить", "run": "▶ выполнить", "read": "◌ прочитать"}


def show_plan(blocks):
    """Короткий список действий перед выполнением (если их несколько)."""
    items = []
    for lang, code in blocks:
        kind, _, arg = lang.strip().partition(" ")
        kind = kind.lower()
        if kind in ICONS:
            what = arg.strip() or code.strip().split("\n")[0]
            items.append(f"{tr(ICONS[kind])} {''.join(c for c in what if c.isprintable())[:60]}")
    if len(items) > 1:
        out(tr("  {0}▸ дальше:{1}").format(ACCENT, RESET))
        for it in items[:4]:
            out(f"    {GREY}{it}{RESET}")


def run_actions(st, blocks):
    """Выполняет действия из ответа. Возвращает (результаты, остановиться?)."""
    results, stop, n = [], False, 0
    show_plan(blocks)
    for lang, code in blocks:
        kind, _, arg = lang.strip().partition(" ")
        kind, arg = kind.lower(), arg.strip()
        if kind not in ("run", "edit", "write", "read"):
            continue
        n += 1
        if n > 4:
            results.append(tr("(лишние блоки пропущены, максимум 4 за ответ)"))
            break
        if kind == "run":
            res, status = act_run(st, code)
        elif kind == "edit":
            res, status = act_edit(st, arg, code)
        elif kind == "write":
            res, status = act_write(st, arg, code)
        else:
            res, status = act_read(st, arg or code.strip())
        results.append(res)
        if status == "declined":
            stop = True
            break
    return results, stop
