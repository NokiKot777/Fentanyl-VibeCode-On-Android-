# -*- coding: utf-8 -*-
"""Ввод пользователя и главный цикл main()."""

import os
import re
import sys
import time

from . import cat as _cat
from .anim import boot, bye, show_header
from .cat import cat_sleep, cbreak, idle_ok, read_keys
from .chat import EXIT, boot_server, greeting, send, show_status
from .greet import ask_name, choose_language
from .i18n import set_lang
from .commands import COMMANDS, cmd_run
from .config import load_cfg, setup
from .session import SESS_DIR, save_session
from .term import ACCENT, BOLD, GREY, RED, RESET, YELLOW, USE, apply_theme, clear, hint, out, prompt_safe, set_anim
from .tools import State
from .workdir import enter, startup_dir
from .i18n import tr


def read_input(attached):
    badge = tr("{0}[+{1} файл]{2} ").format(YELLOW, len(attached), RESET) if attached else ""
    proj = os.path.basename(os.getcwd()) or "/"
    proj = proj if len(proj) <= 16 else proj[:15] + "…"
    body = f"{badge}{GREY}{proj}{RESET} {ACCENT}{BOLD}❯{RESET} "
    if not idle_ok():
        out()
        line = input(prompt_safe(body))
    else:
        out("\n" + body, "")
        text = ""
        with cbreak():
            keys = read_keys(_cat.IDLE_SECONDS)
            if keys is None:  # пять минут тишины
                cat_sleep()
            elif keys.startswith("\x04"):
                raise EOFError
            elif "\n" in keys or "\r" in keys:  # Enter на пустой строке / быстрый ввод
                text = re.split(r"[\r\n]", keys)[0]
                out("\r\033[2K" + body + text)
                line = text
                keys = None
                text = None
            elif not keys.startswith("\x1b"):
                text = "".join(c for c in keys if c.isprintable())
        if text is None:
            pass
        else:
            out("\r\033[2K", "")
            hook = False
            if text:
                try:
                    import readline
                    readline.set_startup_hook(lambda: readline.insert_text(text))
                    hook = True
                except Exception:
                    pass
            try:
                line = input(prompt_safe(body))
            finally:
                if hook:
                    readline.set_startup_hook()
    while line.endswith("\\"):
        line = line[:-1] + "\n" + input(prompt_safe(f"{GREY}   … {RESET}"))
    return line


def main():
    cfg = load_cfg()
    if "FENTANYL_IDLE" not in os.environ and isinstance(cfg.get("idle"), int):
        _cat.IDLE_SECONDS = cfg["idle"]
    set_lang(cfg.get("lang", "ru"))
    if cfg.get("anim") is False:
        set_anim(False)
    apply_theme(cfg.get("theme", "mint"))
    boot()
    tty = USE and sys.stdout.isatty()
    if tty:  # экран загрузки исчез
        clear()
    if "lang" not in cfg and sys.stdin.isatty():  # самый первый экран — выбор языка
        choose_language(cfg)
        if tty:
            clear()
    if tty:  # рисуем интерфейс с логотипом в углу
        show_header()
    if not cfg.get("base") or not cfg.get("model"):
        cfg = setup(cfg)
    if "name" not in cfg and sys.stdin.isatty():
        ask_name(cfg)
    folder = startup_dir(cfg)
    if folder:
        enter(cfg, folder)
    st = State(cfg)
    show_status(st)
    greeting(st)
    boot_server(st)
    if os.path.exists(os.path.join(SESS_DIR, "last.json")):
        hint(tr("есть прошлый чат: /resume last"))

    last_int = 0.0
    while True:
        try:
            line = read_input(st.attached).rstrip()
        except EOFError:
            out()
            bye()
            break
        except KeyboardInterrupt:
            now = time.time()
            if now - last_int < 2:
                out()
                bye()
                break
            last_int = now
            out(tr("\n  {0}Ctrl+C ещё раз — выход (или /exit){1}").format(GREY, RESET))
            continue
        if not line.strip():
            continue
        if line.startswith("!") and len(line) > 1:
            cmd_run(st, line[1:].strip())
            continue
        if line.startswith("/"):
            cmd, _, arg = line.partition(" ")
            handler = COMMANDS.get(cmd.lower())
            if handler is None:
                out(tr("  {0}неизвестная команда{1}  {2}/help{3}").format(RED, RESET, GREY, RESET))
                continue
            try:
                res = handler(st, arg.strip())
            except KeyboardInterrupt:
                out(tr("\n  {0}■ прервано{1}").format(YELLOW, RESET))
                continue
            if res is EXIT:
                bye()
                break
            if isinstance(res, str) and res.strip():
                line = res  # /paste → отправить как сообщение
            else:
                continue
        send(st, line)
    if st.history:
        save_session(st, "last")
