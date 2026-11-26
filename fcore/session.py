# -*- coding: utf-8 -*-
"""Контекст, @-упоминания, сохранение и загрузка чатов."""

import json
import os
import re
import sys
import time

from .agent import AGENT_PROMPT, COMMENT_CODE, COMMENT_PLAN
from .anim import Spinner
from .api import stream_reply
from .config import DEFAULT_SYSTEM
from .term import ACCENT, RED, RESET, out
from .tools import read_text_file, tree_lines
from .i18n import tr


# ───────────────────────── контекст, сессии ─────────────────────────
def load_project_md():
    for nm in ("FENTANYL.md", "CLAUDE.md", "AGENTS.md"):
        try:
            with open(nm, encoding="utf-8", errors="replace") as f:
                return nm, f.read()[:8000]
        except OSError:
            continue
    return None, ""


def build_system(st):
    parts = [st.cfg.get("system") or tr(DEFAULT_SYSTEM)]
    if st.agent:
        parts.append(AGENT_PROMPT)
        if st.cfg.get("comments", True):
            parts.append(COMMENT_PLAN)
    if st.cfg.get("comments", True):
        parts.append(COMMENT_CODE)
    if st.cfg.get("think"):
        parts.append("Before answering, think step by step. Write your reasoning inside <think>...</think> "
                     "(tags on their own lines), keep it concise, then give the final answer after </think>.")
    parts.append(f"Working directory: {os.getcwd()}\nOS: {sys.platform}")
    tree = tree_lines(".", 1, 30)
    if tree:
        parts.append("Files in the working directory:\n" + "\n".join(tree))
    nm, md = load_project_md()
    if md:
        parts.append(f"Project instructions ({nm}):\n{md}")
    return "\n\n".join(parts)


def est_tokens(history):
    return sum(len(m["content"]) for m in history) // 3


MENTION = re.compile(r"(?<!\S)@([^\s]+)")


def expand_mentions(line):
    """@файл и @папка в тексте → прикрепляются автоматически."""
    files, seen = [], set()
    for m in MENTION.finditer(line):
        p = os.path.expanduser(m.group(1).rstrip(",.;:!?)"))
        if p in seen:
            continue
        seen.add(p)
        if os.path.isfile(p):
            try:
                files.append((tr("Файл ") + p, read_text_file(p)))
                out(f"  {ACCENT}✓{RESET} @{p}")
            except Exception as e:  # noqa: BLE001
                out(f"  {RED}@{p}: {e}{RESET}")
        elif os.path.isdir(p):
            files.append((tr("Папка ") + p + "/", "\n".join(tree_lines(p, 2, 80))))
            out(f"  {ACCENT}✓{RESET} @{p}/")
    return files


SESS_DIR = os.path.join(os.path.expanduser("~"), ".fentanyl_sessions")


def _sess_name(name):
    return re.sub(r"[^\w\-.]+", "_", name).strip("_")[:60] or "chat"


def save_session(st, name):
    try:
        os.makedirs(SESS_DIR, exist_ok=True)
        path = os.path.join(SESS_DIR, _sess_name(name) + ".json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"cwd": os.getcwd(), "model": st.cfg.get("model"), "saved": time.time(),
                       "history": st.history}, f, ensure_ascii=False)
        return path
    except OSError:
        return None


def list_sessions():
    rows = []
    try:
        names = os.listdir(SESS_DIR)
    except OSError:
        return rows
    for fn in names:
        if not fn.endswith(".json"):
            continue
        p = os.path.join(SESS_DIR, fn)
        try:
            with open(p, encoding="utf-8") as f:
                d = json.load(f)
            first = next((m["content"] for m in d["history"] if m["role"] == "user"), "")
            title = first.split("\n\n")[-1].replace("\n", " ")[:50]
            rows.append((fn[:-5], d.get("saved", 0), title, len(d["history"])))
        except (OSError, ValueError, KeyError):
            continue
    rows.sort(key=lambda r: -r[1])
    return rows


def load_session(name):
    with open(os.path.join(SESS_DIR, _sess_name(name) + ".json"), encoding="utf-8") as f:
        return json.load(f)["history"]


def collect_reply(cfg, messages, system, words):
    sp = Spinner(words)
    sp.start()
    try:
        return "".join(stream_reply(cfg, messages, system=system)).strip()
    finally:
        sp.stop()
