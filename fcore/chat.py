# -*- coding: utf-8 -*-
"""Ход диалога, help, статус, приветствие."""

import os
import re
import textwrap
import time

from .agent import run_actions
from .checker import auto_check
from .anim import Spinner, grad_word, sweep_divider, typewriter, welcome
from .api import stream_reply
from .cat import cat_say
from .config import DEFAULT_SYSTEM, PROVIDERS, save_cfg
from .render import Renderer
from .server import SERVER
from .session import build_system, est_tokens, expand_mentions, load_project_md, save_session
from .sysutil import git, notify
from .greet import hello_text
from .term import ACCENT, BOLD, GREY, RED, RESET, WHITE, YELLOW, box, clip, out, short_path, width
from .i18n import tr


EXIT = object()
GGUF_P = next(p for p in PROVIDERS if p[1] == "gguf")
MAX_STEPS = 6

HELP = [
    ("Чат", [("/new", "новый чат"), ("/paste", "вставить много строк (закончи строкой END)"),
             ("/file <путь>", "прикрепить файл"), ("@путь", "в тексте: прикрепить файл или папку"),
             ("/save <путь>", "сохранить последний блок кода"), ("/compact", "сжать историю (мало контекста)"),
             ("/ctx [n]", "сколько контекста занято / задать размер")]),
    ("Агент", [("/agent on|off", "модель сама предлагает run/edit/write/read"),
               ("/auto edit|run|off", "не спрашивать подтверждение"), ("/undo", "откатить последнюю правку"),
               ("/run <cmd>  или  !cmd", "выполнить команду, вывод — в чат"), ("/ls [путь]", "дерево папки"),
               ("/grep <regex> [путь]", "поиск по проекту"), ("/read <файл> [от-до]", "показать и прикрепить"),
               ("/git [diff|log|commit]", "статус, diff, коммит с сообщением от модели")]),
    ("Вид", [("/lang [en|ru]", "язык интерфейса"),
             ("/clear", "очистить экран (чат остаётся)"),
             ("/think on|off", "рассуждение модели: показывать и просить думать вслух"),
             ("/comments on|off", "ИИ сначала поясняет план, пишет комментарии в коде"),
             ("/credits", "о программе: версия и создатели"),
             ("/name [имя|-]", "как к тебе обращаться (- убрать имя)"),
             ("/reset", "сбросить настройки fentanyl")]),
    ("Проверка", [("/check off|warn|fix", "автопроверка проекта: выкл / предупреждать / сама исправлять"),
                  ("/preview [файл|on|off]", "окно предпросмотра: запуск Python/Node/sh или HTML в браузере")]),
    ("Проект", [("/projects", "меню проектов: недавние, убрать, обзор"),
               ("/cd [путь|-]", "сменить папку проекта (без пути — обзор папок)"),
               ("/pwd", "в какой папке сейчас работает ИИ")]),
    ("Сессии", [("/save-chat [имя]", "сохранить чат"), ("/resume [имя|№|last]", "продолжить сохранённый чат")]),
    ("Модель", [("/models", "выбор: скачанные + каталог с загрузкой"), ("/download <url>", "скачать .gguf по ссылке"),
                ("/gguf [путь]", "запустить GGUF"), ("/server [stop|restart]", "сервер модели"),
                ("/battery [on|off]", "экономия батареи"), ("/model <имя>", "сменить модель"),
                ("/setup", "провайдер / ключ"), ("/sys <текст>", "системный промпт")]),
    ("Вид", [("/theme [имя]", "цветовая тема"), ("/idle <сек>", "когда засыпает котик (0 — выкл)"),
             ("/cat", "показать котика"), ("/notify on|off", "уведомление о длинных ответах"),
             ("/anim on|off", "анимации")]),
    ("", [("/help", "эта справка"), ("/exit", "выход")]),
]


def show_help(st=None, arg=""):
    for title, rows in HELP:
        out()
        if title:
            out(f"  {BOLD}{WHITE}{tr(title)}{RESET}")
        for c, d in rows:
            c, d = tr(c), tr(d)
            if 3 + 24 + len(d) <= width() - 1:
                out(f"   {ACCENT}{c:<24}{RESET}{GREY}{d}{RESET}")
            else:  # узкий экран: описание переносим под команду
                out(f"   {ACCENT}{c}{RESET}")
                for ln in textwrap.wrap(d, max(10, width() - 8)):
                    out(f"     {GREY}{ln}{RESET}")
    for ln in textwrap.wrap(tr("Строка на \\ — продолжение ввода. Ctrl+C во время ответа — стоп."), max(10, width() - 6)):
        out(f"   {GREY}{ln}{RESET}")
    out()


def read_paste():
    out(tr("  {0}Вставляй текст. Закончи строкой END.{1}").format(GREY, RESET))
    lines = []
    while True:
        try:
            ln = input()
        except EOFError:
            break
        if ln.strip() == "END":
            break
        lines.append(ln)
    return "\n".join(lines)


def show_status(st):
    c = st.cfg
    m = os.path.basename(c["gguf"]) if c.get("gguf") else c["model"]
    flags = [n for n, on in (("agent", st.agent), ("auto-edit", st.auto_edit), ("auto-run", st.auto_run),
                             ("eco", c.get("battery"))) if on]
    rows = [tr("{0}▸{1} {2}папка {3} {4}{5}{6}").format(ACCENT, RESET, GREY, RESET, WHITE, short_path(os.getcwd(), 52), RESET),
            tr("{0}▸{1} {2}модель{3} {4} · {5}").format(ACCENT, RESET, GREY, RESET, tr(c['provider']), m),
            tr("{0}▸{1} {2}режим {3} {4}  {5}· /help{6}").format(ACCENT, RESET, GREY, RESET, (' '.join(flags) if flags else tr("чат")), GREY, RESET)]
    out()
    box(rows, "fentanyl", ACCENT)


def boot_server(st):
    if st.cfg.get("kind") != "gguf":
        return
    try:
        SERVER.ensure(st.cfg)
        out(tr("  {0}✓{1} модель запущена {2}(порт {3}){4}").format(ACCENT, RESET, GREY, SERVER.port, RESET))
    except Exception as e:  # noqa: BLE001
        out(f"  {RED}⚠ {e}{RESET}")


def greeting(st):
    hello = hello_text(st.cfg.get("name", ""))
    extra = []
    nm, md = load_project_md()
    if md:
        extra.append(tr("{0} загружен").format(nm))
    rc, br = git("rev-parse", "--abbrev-ref", "HEAD", timeout=2)
    if rc == 0 and br:
        extra.append(f"git: {br}")
    proj = os.path.basename(os.getcwd()) or "/"
    sub = tr("проект {0}").format(proj) + (" · " + " · ".join(extra) if extra else "")
    if not welcome(hello, st.cfg.get("name", ""), sub):
        typewriter(clip(f"  {WHITE}{hello}{RESET} {GREY}{sub}{RESET}", width() - 2))


def use_gguf(st, path):
    st.cfg.update(provider=GGUF_P[0], kind="gguf", base=GGUF_P[2], model="local", key="",
                  gguf=os.path.abspath(path), system=st.cfg.get("system") or DEFAULT_SYSTEM)
    save_cfg(st.cfg)
    show_status(st)
    boot_server(st)


# ───────────────────────── ход диалога ─────────────────────────
def stream_turn(st):
    sp = Spinner()
    sp.start()
    r = Renderer()
    r.hide_think = not st.cfg.get("think")
    full, err, first, n, t1 = "", None, True, 0, 0.0
    try:
        for chunk in stream_reply(st.cfg, st.history, system=build_system(st)):
            if first:
                sp.stop()
                out(f"  {BOLD}{grad_word('fentanyl')}{RESET}")
                first, t1 = False, time.time()
            n += 1
            full += chunk
            r.feed(chunk)
    except KeyboardInterrupt:
        err = "stop"
    except Exception as e:  # noqa: BLE001
        err = str(e)
    finally:
        sp.stop()
    if not first:
        r.finish()
        st.blocks.extend(r.blocks)
        dt = time.time() - t1
        if not err and n > 5 and dt > 0.3:
            out(tr("  {0}≈{1} ток  ·  {2:.1f} ток/с  ·  {3:.1f} с{4}").format(GREY, n, (n / dt), dt, RESET))
        sweep_divider()
    return full, err, (r.blocks if not first else [])


def converse(st, text):
    st.history.append({"role": "user", "content": text})
    t0, undo0 = time.time(), len(st.undo)
    err, stop = None, False
    for step in range(MAX_STEPS):
        out()
        full, err, blocks = stream_turn(st)
        if err == "stop":
            out(tr("\n  {0}■ остановлено{1}").format(YELLOW, RESET))
        elif err:
            out(tr("\n  {0}⚠ ошибка:{1} {2}").format(RED, RESET, err))
            out(tr("  {0}Проверь ключ, адрес и модель: /setup{1}").format(GREY, RESET))
            cat_say("sad", tr("что-то пошло не так"))
        if not full:
            if st.history and st.history[-1]["role"] == "user":
                st.history.pop()
            return
        # рассуждение в историю не кладём — экономим контекст
        st.history.append({"role": "assistant",
                           "content": re.sub(r"<think>.*?(</think>|$)", "", full, flags=re.S).strip() or full})
        if err or not st.agent:
            break
        results, stop = run_actions(st, blocks)
        if not results:
            break
        note = tr("Результаты действий:\n\n") + "\n\n".join(results)
        if stop:
            st.pending = note + tr("\n\n(Пользователь отклонил последнее действие. Не повторяй его без запроса.)")
            break
        if step == MAX_STEPS - 1:
            st.pending = note
            out(tr("  {0}лимит шагов — напиши «продолжай»{1}").format(GREY, RESET))
            break
        out(tr("  {0}↻ отправляю результаты модели{1}").format(GREY, RESET))
        st.history.append({"role": "user", "content": note})
    if st.agent and not err and not stop and not st.pending and len(st.undo) > undo0:
        # проект собран — запускаем, смотрим консоль, показываем предпросмотр
        follow = auto_check(st, [u[0] for u in st.undo[undo0:]])
        if follow:
            st.fix_tries += 1
            return converse(st, follow)
    if len(st.undo) > undo0:
        cat_say("happy", tr("готово!"))
    est = est_tokens(st.history)
    limit = SERVER.sig[1] if st.cfg.get("kind") == "gguf" and getattr(SERVER, "sig", None) else None
    if (limit and est > limit * 0.7) or (not limit and est > 24000):
        out(tr("  {0}контекст почти заполнен (≈{1} ток) — сделай /compact или /new{2}").format(YELLOW, est, RESET))
    if st.cfg.get("notify", True) and time.time() - t0 > 15:
        notify(tr("Ответ готов"))
    save_session(st, "last")


def send(st, line):
    st.fix_tries = 0
    files = st.attached + expand_mentions(line)
    st.attached = []
    text = line
    if files:
        text = "\n\n".join(f"{n}:\n```\n{c}\n```" for n, c in files) + "\n\n" + line
    if st.pending:
        text, st.pending = st.pending + "\n\n" + text, ""
    converse(st, text)
