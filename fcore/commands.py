# -*- coding: utf-8 -*-
"""Обработчики команд (/new, /git, /models …)."""

import os
import re
import shlex
import shutil
import sys
import time

from . import cat as _cat
from .anim import ok_line, show_credits, show_header
from .checker import MODES, find_target, preview_now
from .greet import ask_name, choose_language, clean_name
from .i18n import LANGS, set_lang
from .cat import cat_say, cat_sleep, cbreak, msvcrt, termios
from .chat import EXIT, boot_server, read_paste, show_help, show_status, use_gguf
from .config import save_cfg, setup
from .models import CATALOG_FILE, download_file, full_catalog, hf_url, mem_gb, models_dir
from .server import SERVER, find_ggufs
from .session import collect_reply, est_tokens, list_sessions, load_session, save_session
from .sysutil import battery_info, git
from .term import (
    ACCENT, BOLD, GREY, RED, RESET, THEMES, USE, WHITE, YELLOW, anim_flag, apply_theme, box, fg, hint, out,
    set_anim, short_path, width,
)
from .workdir import browse, check_dir, enter, projects_menu
from .tools import ask_line, grep_tree, read_text_file, run_shell, show_output, tree_lines, trim
from .i18n import tr


# ───────────────────────── обработчики команд ─────────────────────────
def cmd_new(st, arg):
    st.history, st.attached, st.pending = [], [], ""
    ok_line(tr("новый чат"))


def cmd_paste(st, arg):
    return read_paste()


def cmd_file(st, arg):
    if not arg:
        return out(tr("  {0}/file <путь> [ещё пути]{1}").format(GREY, RESET))
    for a in shlex.split(arg) if arg else []:
        try:
            st.attached.append((tr("Файл ") + a, read_text_file(os.path.expanduser(a))))
            out(tr("  {0}✓{1} прикреплён {2}").format(ACCENT, RESET, a))
        except Exception as e:  # noqa: BLE001
            out(tr("  {0}не удалось открыть {1}: {2}{3}").format(RED, a, e, RESET))


def cmd_save(st, arg):
    if not arg:
        return out(tr("  {0}/save <путь>{1}").format(GREY, RESET))
    if not st.blocks:
        return out(tr("  {0}ещё нет блоков кода{1}").format(RED, RESET))
    try:
        with open(os.path.expanduser(arg), "w", encoding="utf-8") as f:
            f.write(st.blocks[-1][1] + "\n")
        out(tr("  {0}✓{1} сохранено в {2}").format(ACCENT, RESET, arg))
    except Exception as e:  # noqa: BLE001
        out(tr("  {0}ошибка: {1}{2}").format(RED, e, RESET))


def cmd_model(st, arg):
    if not arg:
        return out(tr("  {0}/model <имя>{1}").format(GREY, RESET))
    st.cfg["model"] = arg
    save_cfg(st.cfg)
    out(tr("  {0}✓{1} модель: {2}").format(ACCENT, RESET, arg))


def cmd_sys(st, arg):
    if not arg:
        return out(tr("  {0}/sys <текст>{1}").format(GREY, RESET))
    st.cfg["system"] = arg
    save_cfg(st.cfg)
    out(tr("  {0}✓{1} системный промпт обновлён").format(ACCENT, RESET))


def cmd_setup(st, arg):
    st.cfg = setup(st.cfg)
    show_status(st)
    boot_server(st)


def cmd_gguf(st, arg):
    if arg:
        path = os.path.expanduser(arg)
        if not os.path.isfile(path):
            return out(tr("  {0}файл не найден: {1}{2}").format(RED, path, RESET))
        return use_gguf(st, path)
    found = find_ggufs()
    if not found:
        return out(tr("  {0}.gguf не найдено. Скачай: /models  или укажи путь: /gguf <файл>{1}").format(GREY, RESET))
    for f in found:
        out(f"   {WHITE}{os.path.basename(f)}{RESET}  {GREY}{f}{RESET}")


def cmd_server(st, arg):
    if arg == "stop":
        SERVER.stop()
        out(tr("  {0}✓{1} сервер остановлен").format(ACCENT, RESET))
    elif arg == "restart":
        SERVER.stop()
        boot_server(st)
    elif SERVER.running():
        out(tr("  {0}●{1} работает  {2}порт {3} · {4}{5}").format(ACCENT, RESET, GREY, SERVER.port, os.path.basename(SERVER.model), RESET))
    else:
        out(tr("  {0}○ не запущен (стартует сам при первом сообщении){1}").format(GREY, RESET))


def cmd_idle(st, arg):
    try:
        _cat.IDLE_SECONDS = max(0, int(arg))
    except ValueError:
        return out(tr("  {0}/idle <секунды>{1}").format(RED, RESET))
    st.cfg["idle"] = _cat.IDLE_SECONDS
    save_cfg(st.cfg)
    out(tr("  {0}✓{1} котик засыпает через {2} с").format(ACCENT, RESET, _cat.IDLE_SECONDS) if _cat.IDLE_SECONDS else tr("  {0}✓{1} котик выключен").format(ACCENT, RESET))


def cmd_cat(st, arg):
    if not (USE and sys.stdin.isatty() and (termios is not None or msvcrt is not None)):
        return out(tr("  {0}котик показывается только в цветном терминале{1}").format(GREY, RESET))
    with cbreak():
        cat_sleep()


def cmd_theme(st, arg):
    if arg and apply_theme(arg):
        st.cfg["theme"] = arg
        save_cfg(st.cfg)
        return ok_line(tr("тема: {0}").format(arg))
    if arg:
        out(tr("  {0}нет такой темы{1}").format(RED, RESET))
    for n, t in THEMES.items():
        cur = " ←" if n == st.cfg.get("theme", "mint") else ""
        out(f"   {fg(t['ACCENT'])}████{RESET} {WHITE}{n}{RESET}{GREY}{cur}{RESET}")


def cmd_anim(st, arg):
    if arg in ("on", "off"):
        set_anim(arg == "on")
        st.cfg["anim"] = arg == "on"
        save_cfg(st.cfg)
    out(tr("  {0}✓{1} анимации: {2}  {3}(/anim on|off){4}").format(ACCENT, RESET, tr("включены") if anim_flag() else tr("выключены"), GREY, RESET))


def cmd_cd(st, arg):
    prev = os.getcwd()
    if arg == "-":
        if not st.prev_dir:
            return out(tr("  {0}прошлой папки нет{1}").format(GREY, RESET))
        target = check_dir(st.prev_dir)
    elif arg:
        p = os.path.expanduser(arg.strip().strip("\"'"))
        target = check_dir(p if os.path.isabs(p) else os.path.join(prev, p))
    else:
        target = browse(prev)
    if target:
        _open_project(st, target)


def cmd_check(st, arg):
    if arg in MODES:
        st.cfg["check"] = arg
        save_cfg(st.cfg)
    elif arg:
        return out(f"  {RED}/check off | warn | fix{RESET}")
    mode = st.cfg.get("check", "warn")
    ok_line(tr("автопроверка: ") + {"off": tr("выключена"), "warn": tr("предупреждать"), "fix": tr("сама исправлять")}[mode])
    hint(tr("warn — покажет ошибку и спросит, исправлять ли. fix — ИИ сам исправит (до 2 попыток). off — не запускать. Код запускается только с твоего согласия."))


def cmd_preview(st, arg):
    if arg in ("on", "off"):
        st.cfg["preview"] = arg == "on"
        save_cfg(st.cfg)
        return ok_line(tr("окно предпросмотра: {0}").format(tr("включено") if arg == 'on' else tr("выключено")))
    paths = None
    if arg:
        p = os.path.abspath(os.path.expanduser(arg))
        if not os.path.isfile(p):
            return out(tr("  {0}нет такого файла{1}").format(RED, RESET))
        paths = [p]
    target = find_target(paths)
    if not target:
        return out(tr("  {0}нечего показывать: в проекте нет .html / .py / .js / .sh{1}").format(GREY, RESET))
    preview_now(st, target[0], target[1], paths)


def cmd_lang(st, arg):
    arg = arg.strip().lower()
    code = {"en": "en", "english": "en", "ru": "ru", "рус": "ru", "русский": "ru"}.get(arg)
    if arg and not code:
        return out(f"  {RED}/lang en | ru{RESET}")
    if code:
        set_lang(code)
        st.cfg["lang"] = code
        save_cfg(st.cfg)
    else:
        code = choose_language(st.cfg)
    ok_line(tr("язык: {0}").format(LANGS[code]))
    show_status(st)


def cmd_projects(st, arg):
    target = projects_menu(st.cfg, os.getcwd())
    if target:
        _open_project(st, target)


def cmd_comments(st, arg):
    if arg in ("on", "off"):
        st.cfg["comments"] = arg == "on"
        save_cfg(st.cfg)
    on = st.cfg.get("comments", True)
    ok_line(tr("комментарии: {0}").format(tr("включены") if on else tr("выключены")))
    hint(tr("on — ИИ сначала коротко поясняет, что будет делать (для проекта — план), и пишет комментарии в коде."))


def _open_project(st, target):
    """Переключает рабочую папку (общая часть /cd и /projects)."""
    prev = os.getcwd()
    if os.path.realpath(target) == os.path.realpath(prev):
        return out(tr("  {0}ты уже в этой папке{1}").format(GREY, RESET))
    if not enter(st.cfg, target):
        return
    st.prev_dir = prev
    st.undo, st.attached, st.blocks, st.last_entry = [], [], [], None
    if st.history:
        ans = ask_line(tr("  Начать новый чат для этой папки? {0}Y/n{1}").format(GREY, RESET))
        if ans.strip().lower() not in ("n", "н", "no", "нет"):
            st.history, st.pending = [], ""
    ok_line(tr("папка: {0}").format(short_path(target, 50)))
    show_status(st)


def cmd_clear(st, arg):
    if sys.stdout.isatty():
        out("\033[2J\033[3J\033[H", "")
        if USE:
            show_header()
    show_status(st)


def cmd_think(st, arg):
    if arg in ("on", "off"):
        st.cfg["think"] = arg == "on"
        save_cfg(st.cfg)
    on = bool(st.cfg.get("think"))
    ok_line(tr("рассуждение: {0}").format(tr("включено") if on else tr("выключено")))
    hint(tr("on — модель думает вслух, это показывается серым. off — рассуждение скрыто."))


UI_KEYS = ("lang", "name", "projects", "comments", "check", "preview", "check_trust", "check_tries", "check_timeout", "theme", "idle", "anim", "think", "workdir", "notify", "battery", "ctx", "agent", "system")


def cmd_reset(st, arg):
    level = {"1": 1, "ui": 1, "2": 2, "all": 2}.get(arg.strip().lower())
    if not level:
        box([tr("{0}1{1}  вид и режимы   {2}тема, анимации, рассуждение, котик, папка{3}").format(ACCENT, RESET, GREY, RESET),
             tr("{0}2{1}  всё            {2}+ ключ, модель и провайдер{3}").format(ACCENT, RESET, GREY, RESET)], tr("Сброс настроек"))
        hint(tr("Чаты и файлы проекта не удаляются. Enter — отмена."))
        level = {"1": 1, "2": 2}.get(ask_line(tr("  Что сбросить?")).strip())
    if not level:
        return out(tr("  {0}отменено{1}").format(GREY, RESET))
    if level == 2 and ask_line(tr("  Ключ и модель будут удалены. Напиши {0}yes{1}").format(BOLD, RESET)).strip().lower() != "yes":
        return out(tr("  {0}отменено{1}").format(GREY, RESET))
    if level == 1:
        for k in UI_KEYS:
            st.cfg.pop(k, None)
    else:
        SERVER.stop()
        st.cfg.clear()
    save_cfg(st.cfg)
    if sys.stdin.isatty():
        choose_language(st.cfg)
    apply_theme("mint")
    set_anim(True)
    _cat.IDLE_SECONDS = _cat.IDLE_DEFAULT
    st.agent, st.auto_edit, st.auto_run = True, False, False
    ok_line(tr("настройки сброшены"))
    if level == 2:
        st.history, st.attached = [], []
        st.cfg = setup(st.cfg)
    if sys.stdin.isatty():
        ask_name(st.cfg)
    show_status(st)


def cmd_name(st, arg):
    arg = arg.strip()
    if arg == "-":
        st.cfg["name"] = ""
        save_cfg(st.cfg)
        return ok_line(tr("имя убрано"))
    if arg:
        n = clean_name(arg)
        if not n:
            return out(tr("  {0}имя: буквы, цифры, пробел и - _ . ' (до 24 символов){1}").format(RED, RESET))
        st.cfg["name"] = n
        save_cfg(st.cfg)
        return ok_line(tr("буду обращаться: {0}").format(n))
    ask_name(st.cfg)


def cmd_credits(st, arg):
    show_credits()


def cmd_pwd(st, arg):
    out(tr("  {0}▸{1} {2}  {3}(сменить: /cd){4}").format(ACCENT, RESET, os.getcwd(), GREY, RESET))


def cmd_notify(st, arg):
    if arg in ("on", "off"):
        st.cfg["notify"] = arg == "on"
        save_cfg(st.cfg)
    out(tr("  {0}уведомления: {1}{2}{3}").format(GREY, tr("вкл") if st.cfg.get('notify', True) else tr("выкл"), ('' if shutil.which('termux-notification') else tr(" (нужен пакет termux-api)")), RESET))


def cmd_battery(st, arg):
    if arg in ("on", "off"):
        st.cfg["battery"] = arg == "on"
        save_cfg(st.cfg)
        show_status(st)
        boot_server(st)  # параметры изменились — сервер перезапустится
        return
    info = battery_info()
    eco = tr("вкл (2 потока, контекст ≤2048)") if st.cfg.get("battery") else tr("выкл")
    out(tr("  {0}режим экономии: {1}{2}").format(GREY, eco, RESET))
    if info:
        out(tr("  {0}батарея: {1}%  ·  {2}{3}").format(GREY, info.get('percentage'), info.get('status'), RESET))
    else:
        out(tr("  {0}состояние батареи — нужен termux-api (pkg install termux-api + приложение Termux:API){1}").format(GREY, RESET))
    out(f"  {GREY}/battery on  ·  /battery off{RESET}")


def cmd_ctx(st, arg):
    if arg.isdigit():
        st.cfg["ctx"] = int(arg)
        save_cfg(st.cfg)
        out(tr("  {0}✓{1} контекст: {2}").format(ACCENT, RESET, arg))
        return boot_server(st)
    est = est_tokens(st.history)
    limit = SERVER.sig[1] if st.cfg.get("kind") == "gguf" and getattr(SERVER, "sig", None) else None
    hint(tr("в истории ≈{0} ток").format(est) + (tr(" из {0}").format(limit) if limit else "") + tr("  ·  /compact сжать  ·  /ctx <n> задать размер"))


def cmd_compact(st, arg):
    if len(st.history) < 4:
        return out(tr("  {0}история ещё короткая{1}").format(GREY, RESET))
    before = est_tokens(st.history)
    ask = {"role": "user", "content": "Summarize our conversation so far for your own future reference: goals, "
           "decisions, file changes, open questions, key facts. Under 300 words, same language as the conversation."}
    try:
        summary = collect_reply(st.cfg, st.history + [ask], "You summarize conversations.", [tr("сжимаю историю")])
    except Exception as e:  # noqa: BLE001
        return out(tr("  {0}не удалось сжать: {1}{2}").format(RED, e, RESET))
    if not summary:
        return out(tr("  {0}модель вернула пустой ответ{1}").format(RED, RESET))
    st.history = [{"role": "user", "content": tr("Краткое содержание предыдущего диалога:\n") + summary},
                  {"role": "assistant", "content": tr("Понял, продолжаем.")}]
    out(tr("  {0}✓{1} история сжата: ≈{2} → ≈{3} ток").format(ACCENT, RESET, before, est_tokens(st.history)))


def cmd_agent(st, arg):
    if arg in ("on", "off"):
        st.agent = arg == "on"
        st.cfg["agent"] = st.agent
        save_cfg(st.cfg)
    out(tr("  {0}агент: {1}{2}{3}").format(GREY, tr("вкл") if st.agent else tr("выкл"), ('' if st.agent else tr("  (/agent on — модель сможет предлагать команды и правки)")), RESET))


def cmd_auto(st, arg):
    a = arg.lower()
    if a == "edit":
        st.auto_edit = True
    elif a == "run":
        st.auto_run = True
    elif a == "off":
        st.auto_edit = st.auto_run = False
    out(tr("  {0}без подтверждения: правки {1} · команды {2}  (опасные команды всегда спрашивают){3}").format(GREY, tr("да") if st.auto_edit else tr("нет"), tr("да") if st.auto_run else tr("нет"), RESET))


def cmd_undo(st, arg):
    if not st.undo:
        return out(tr("  {0}нечего откатывать{1}").format(GREY, RESET))
    path, old, crlf = st.undo.pop()
    try:
        if old is None:
            os.remove(path)
            out(tr("  {0}✓{1} удалён созданный файл {2}").format(ACCENT, RESET, path))
        else:
            with open(path, "w", encoding="utf-8", newline="") as f:
                f.write(old.replace("\n", "\r\n") if crlf else old)
            out(tr("  {0}✓{1} восстановлено {2}").format(ACCENT, RESET, path))
    except OSError as e:
        out(tr("  {0}не удалось откатить: {1}{2}").format(RED, e, RESET))


def cmd_run(st, arg):
    if not arg:
        return out(tr("  {0}/run <команда>   или   !команда{1}").format(GREY, RESET))
    rc, txt = run_shell(arg)
    show_output(txt, 40)
    out(f"  {ACCENT}✓{RESET}" if rc == 0 else tr("  {0}✗ код {1}{2}").format(RED, rc, RESET))
    st.attached.append((tr("$ {0} (код {1})").format(arg, rc), trim(txt)))
    out(tr("  {0}вывод добавлен к следующему сообщению{1}").format(GREY, RESET))


def cmd_ls(st, arg):
    path = os.path.expanduser(arg) if arg else "."
    if not os.path.isdir(path):
        return out(tr("  {0}нет такой папки: {1}{2}").format(RED, path, RESET))
    lines = tree_lines(path, 2, 80)
    for ln in lines:
        out(f"  {GREY}│{RESET} {ln}")
    st.attached.append((tr("Дерево папки {0}").format(path), "\n".join(lines)))
    out(tr("  {0}добавлено к следующему сообщению{1}").format(GREY, RESET))


def cmd_grep(st, arg):
    try:
        parts = shlex.split(arg)
    except ValueError as e:
        return out(f"  {RED}{e}{RESET}")
    if not parts:
        return out(tr("  {0}/grep <regex> [путь]{1}").format(GREY, RESET))
    try:
        hits, cut = grep_tree(parts[0], os.path.expanduser(parts[1]) if len(parts) > 1 else ".")
    except re.error as e:
        return out(tr("  {0}ошибка в regex: {1}{2}").format(RED, e, RESET))
    if not hits:
        return out(tr("  {0}ничего не найдено{1}").format(GREY, RESET))
    for h in hits[:40]:
        out(f"  {GREY}│{RESET} {h[:width() - 6]}")
    if len(hits) > 40 or cut:
        out(tr("  {0}│ … всего {1}{2}{3}").format(GREY, len(hits), ('+' if cut else ''), RESET))
    st.attached.append((tr("Результат grep {0}").format(parts[0]), "\n".join(hits)))
    out(tr("  {0}добавлено к следующему сообщению{1}").format(GREY, RESET))


def cmd_read(st, arg):
    try:
        parts = shlex.split(arg)
    except ValueError as e:
        return out(f"  {RED}{e}{RESET}")
    if not parts:
        return out(tr("  {0}/read <файл> [от-до]{1}").format(GREY, RESET))
    path = os.path.expanduser(parts[0])
    try:
        lines = read_text_file(path).split("\n")
    except Exception as e:  # noqa: BLE001
        return out(tr("  {0}не удалось открыть: {1}{2}").format(RED, e, RESET))
    a, b = 1, len(lines)
    if len(parts) > 1:
        m = re.fullmatch(r"(\d+)-(\d+)", parts[1])
        if m:
            a, b = max(1, int(m.group(1))), min(len(lines), int(m.group(2)))
    sel = [f"{i:>4}  {lines[i - 1]}" for i in range(a, b + 1)]
    for ln in sel[:60]:
        out(f"  {GREY}│{RESET} {ln[:width() - 6]}")
    if len(sel) > 60:
        out(tr("  {0}│ … ещё {1} строк{2}").format(GREY, (len(sel) - 60), RESET))
    st.attached.append((tr("Файл {0} (строки {1}-{2})").format(parts[0], a, b), "\n".join(sel)))
    out(tr("  {0}добавлено к следующему сообщению{1}").format(GREY, RESET))


def cmd_git(st, arg):
    sub, _, rest = arg.partition(" ")
    sub, rest = sub.lower(), rest.strip()
    if sub in ("", "status"):
        rc, s = git("status", "-sb")
        if rc != 0:
            return out(f"  {RED}{s}{RESET}")
        for ln in s.split("\n"):
            out(f"  {GREY}│{RESET} {ln}")
        rc, d = git("diff", "--stat")
        for ln in d.split("\n") if d else []:
            out(f"  {GREY}│{RESET} {ln}")
    elif sub == "log":
        rc, s = git("log", "--oneline", "-10")
        for ln in s.split("\n"):
            out(f"  {GREY}│{RESET} {ln}")
    elif sub == "diff":
        rc, d1 = git("diff")
        rc2, d2 = git("diff", "--cached")
        d = (d1 + "\n" + d2).strip()
        if rc != 0:
            return out(f"  {RED}{d1}{RESET}")
        if not d:
            return out(tr("  {0}изменений нет{1}").format(GREY, RESET))
        st.attached.append(("git diff", trim(d, 20000)))
        out(tr("  {0}✓{1} diff ({2} строк) добавлен к следующему сообщению").format(ACCENT, RESET, (d.count(chr(10)) + 1)))
    elif sub == "commit":
        rc, status = git("status", "--porcelain")
        if rc != 0:
            return out(f"  {RED}{status}{RESET}")
        if not status:
            return out(tr("  {0}нечего коммитить{1}").format(GREY, RESET))
        msg = rest
        if not msg:
            rc, d = git("diff", "HEAD")
            if rc != 0:
                d = git("diff")[1] + "\n" + git("diff", "--cached")[1]
            prompt = ("Write a concise git commit message (one line, imperative mood, max 72 chars) for these "
                      "changes. Output ONLY the message.\n\nStatus:\n" + status[:2000] + "\n\nDiff:\n" + trim(d, 10000))
            try:
                msg = collect_reply(st.cfg, [{"role": "user", "content": prompt}],
                                    "You write git commit messages.", [tr("пишу сообщение коммита")])
            except Exception as e:  # noqa: BLE001
                return out(tr("  {0}не удалось получить сообщение: {1}{2}").format(RED, e, RESET))
            msg = (msg.strip().strip("`\"'").split("\n") or [""])[0][:100]
        files = status.split("\n")
        for ln in files[:15]:
            out(f"  {GREY}│{RESET} {ln}")
        if len(files) > 15:
            out(tr("  {0}│ … ещё {1}{2}").format(GREY, (len(files) - 15), RESET))
        out(tr("  {0}коммит:{1} {2}").format(YELLOW, RESET, msg))
        ans = ask_line(tr("  Закоммитить всё? {0}y — да · n — нет · или введи своё сообщение{1}").format(GREY, RESET)).strip()
        if ans.lower() in ("", "n", "no", "н", "нет"):
            return out(tr("  {0}отменено{1}").format(GREY, RESET))
        if ans.lower() not in ("y", "yes", "д", "да"):
            msg = ans
        git("add", "-A")
        rc, res = git("commit", "-m", msg)
        out(tr("  {0}✓{1} {2}").format(ACCENT, RESET, res.splitlines()[0] if res else tr("готово")) if rc == 0 else f"  {RED}{res}{RESET}")
        if rc == 0:
            cat_say("happy", tr("закоммитили!"))
    else:
        out(tr("  {0}/git  ·  /git diff  ·  /git log  ·  /git commit [сообщение]{1}").format(GREY, RESET))


def cmd_save_chat(st, arg):
    if not st.history:
        return out(tr("  {0}чат пуст{1}").format(GREY, RESET))
    name = arg or "chat-" + time.strftime("%Y%m%d-%H%M")
    p = save_session(st, name)
    out(tr("  {0}✓{1} сохранено: {2}{3}{4}").format(ACCENT, RESET, GREY, p, RESET) if p else tr("  {0}не удалось сохранить{1}").format(RED, RESET))


def cmd_resume(st, arg):
    rows = list_sessions()
    if not rows:
        return out(tr("  {0}сохранённых чатов нет (/save-chat){1}").format(GREY, RESET))
    if not arg:
        for i, (n, ts, title, cnt) in enumerate(rows, 1):
            out(tr("   {0}{1}{2}  {3}{4}{5}  {6}{7} · {8} сообщ. · {9}{10}").format(ACCENT, i, RESET, WHITE, n, RESET, GREY, time.strftime('%d.%m %H:%M', time.localtime(ts)), cnt, title, RESET))
        arg = ask_line(tr("Номер или имя (Enter — отмена)")).strip()
        if not arg:
            return
    name = rows[int(arg) - 1][0] if arg.isdigit() and 0 < int(arg) <= len(rows) else arg
    try:
        st.history = load_session(name)
    except (OSError, ValueError, KeyError):
        return out(tr("  {0}чат не найден: {1}{2}").format(RED, name, RESET))
    st.attached, st.pending = [], ""
    out(tr("  {0}✓{1} загружено {2} сообщений ({3})").format(ACCENT, RESET, len(st.history), name))


def cmd_models(st, arg):
    have = find_ggufs()
    have_names = {os.path.basename(p) for p in have}
    ram = mem_gb()
    rows = []
    out()
    if ram:
        out(tr("  {0}RAM телефона: {1:.1f} ГБ{2}").format(GREY, ram, RESET))
    if have:
        out(tr("  {0}{1}Скачано{2}").format(BOLD, WHITE, RESET))
        for p in have:
            rows.append(("local", p))
            cur = tr("  ← сейчас") if os.path.abspath(p) == st.cfg.get("gguf") else ""
            out(tr("   {0}{1}{2}  {3}{4}{5}  {6}{7:.1f} ГБ{8}{9}").format(ACCENT, len(rows), RESET, WHITE, os.path.basename(p), RESET, GREY, (os.path.getsize(p) / 1e9), cur, RESET))
    avail = [e for e in full_catalog() if e["file"] not in have_names]
    if avail:
        out(tr("  {0}{1}Каталог{2} {3}(Hugging Face → {4}){5}").format(BOLD, WHITE, RESET, GREY, models_dir(), RESET))
        for e in avail:
            rows.append(("cat", e))
            fit = ""
            if ram and e["gb"]:
                fit = tr("{0}✓ влезет{1}").format(fg(114), RESET) if e["gb"] * 1.3 + 1 <= ram else tr("{0}⚠ мало RAM{1}").format(YELLOW, RESET)
            out(tr("   {0}{1}{2}  {3}{4}{5}  {6}~{7} ГБ · {8}{9} {10}").format(ACCENT, len(rows), RESET, WHITE, e['name'], RESET, GREY, e['gb'], tr(e['note']), RESET, fit))
    out(tr("  {0}свои модели: /download <ссылка>  ·  или список в {1}{2}").format(GREY, CATALOG_FILE, RESET))
    choice = (arg or ask_line(tr("Номер (Enter — отмена)"))).strip()
    if not choice.isdigit() or not 0 < int(choice) <= len(rows):
        return
    kind, item = rows[int(choice) - 1]
    if kind == "local":
        return use_gguf(st, item)
    dest = os.path.join(models_dir(), item["file"])
    out(f"  {YELLOW}↓{RESET} {item['name']}  {GREY}{hf_url(item)}{RESET}")
    if download_file(hf_url(item), dest):
        out(tr("  {0}✓{1} скачано: {2}").format(ACCENT, RESET, dest))
        if ask_line(tr("Запустить сейчас? [Y/n]")).strip().lower() in ("", "y", "д", "да"):
            use_gguf(st, dest)


def cmd_download(st, arg):
    url = arg.strip()
    if not url.startswith(("http://", "https://")):
        return out(tr("  {0}/download <ссылка на .gguf>   или   /models{1}").format(GREY, RESET))
    url = url.replace("/blob/", "/resolve/", 1)
    name = os.path.basename(url.split("?")[0])
    if not name.lower().endswith(".gguf"):
        return out(tr("  {0}ссылка должна вести на .gguf файл{1}").format(RED, RESET))
    dest = os.path.join(models_dir(), name)
    if download_file(url, dest):
        out(tr("  {0}✓{1} скачано: {2}").format(ACCENT, RESET, dest))
        if ask_line(tr("Запустить сейчас? [Y/n]")).strip().lower() in ("", "y", "д", "да"):
            use_gguf(st, dest)


COMMANDS = {
    "/help": show_help, "/new": cmd_new, "/paste": cmd_paste, "/file": cmd_file, "/save": cmd_save,
    "/model": cmd_model, "/sys": cmd_sys, "/setup": cmd_setup, "/gguf": cmd_gguf, "/server": cmd_server,
    "/idle": cmd_idle, "/cat": cmd_cat, "/theme": cmd_theme, "/notify": cmd_notify, "/battery": cmd_battery,
    "/ctx": cmd_ctx, "/compact": cmd_compact, "/agent": cmd_agent, "/auto": cmd_auto, "/undo": cmd_undo,
    "/run": cmd_run, "/ls": cmd_ls, "/grep": cmd_grep, "/read": cmd_read, "/git": cmd_git,
    "/save-chat": cmd_save_chat, "/resume": cmd_resume, "/models": cmd_models, "/download": cmd_download,
    "/check": cmd_check, "/preview": cmd_preview, "/projects": cmd_projects, "/p": cmd_projects, "/comments": cmd_comments, "/cd": cmd_cd, "/project": cmd_cd, "/pwd": cmd_pwd, "/lang": cmd_lang, "/clear": cmd_clear, "/reset": cmd_reset, "/name": cmd_name, "/credits": cmd_credits, "/about": cmd_credits, "/think": cmd_think, "/anim": cmd_anim,
    "/exit": lambda st, a: EXIT, "/quit": lambda st, a: EXIT, "/q": lambda st, a: EXIT,
}
