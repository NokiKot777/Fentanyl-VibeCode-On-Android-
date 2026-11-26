# -*- coding: utf-8 -*-
"""Имя пользователя и приветствие по времени суток."""

import random
import time

from .anim import typewriter
from .config import save_cfg
from .term import ACCENT, ANSI, GREY, RED, RESET, WHITE, box, out, prompt_safe
from .i18n import LANGS, get_lang, set_lang, tr

# {n} превращается в «, Имя» (или в пустоту, если имени нет)
MORNING = ["Доброе утро{n}!", "С добрым утром{n}!", "Утро доброе{n}!", "Бодрого утра{n}!", "Новый день, новый код{n}!"]
DAY = ["Добрый день{n}!", "Хорошего дня{n}!", "Привет{n}!", "Рад тебя видеть{n}!", "Самое время за работу{n}!"]
EVENING = ["Добрый вечер{n}!", "Хорошего вечера{n}!", "Вечер добрый{n}!", "Вечерний кодинг{n}!", "Рад видеть{n}!"]
NIGHT = ["Доброй ночи{n}!", "Не спится{n}?", "Ночная смена{n}!", "Ещё не спишь{n}?", "Тихая ночь для кода{n}!"]
WEEKEND = ["Выходной, а ты за кодом{n}!", "Отдыхаешь только с терминалом{n}?"]
FRIDAY = ["Пятница{n}! Давай закончим всё важное."]


def clean_name(s):
    """Оставляем буквы, цифры и мягкую пунктуацию — без управляющих кодов."""
    s = ANSI.sub("", s or "")
    s = "".join(ch for ch in s if ch.isalnum() or ch in " -_.'’")
    return " ".join(s.split())[:24]


def hello_text(name=""):
    t = time.localtime()
    h = t.tm_hour
    pool = (MORNING if 5 <= h < 11 else DAY if 11 <= h < 17 else EVENING if 17 <= h < 23 else NIGHT)
    pool = list(pool)
    if 5 <= h < 23:  # особые дни подмешиваем к обычным фразам
        if t.tm_wday >= 5:
            pool += WEEKEND
        elif t.tm_wday == 4 and h >= 15:
            pool += FRIDAY
    return tr(random.choice(pool)).replace("{n}", f", {name}" if name else "")


def choose_language(cfg):
    """Экран выбора языка (двуязычный). Enter — оставить текущий (для нового пользователя — English)."""
    known = cfg.get("lang")
    cur = known or get_lang()
    default = cur if known else "en"
    mark = lambda c: f"  {GREY}●{RESET}" if known and cur == c else ""  # noqa: E731
    out()
    box([f"{ACCENT}1{RESET}  English" + mark("en"), f"{ACCENT}2{RESET}  Русский" + mark("ru")],
        "Choose your language · Выберите язык")
    table = {"": default, "1": "en", "en": "en", "e": "en", "english": "en",
             "2": "ru", "ru": "ru", "р": "ru", "рус": "ru", "русский": "ru"}
    while True:
        try:
            a = input(prompt_safe(f"  {GREY}1 / 2 · Enter — {LANGS[default]}{RESET} {ACCENT}❯{RESET} ")).strip().lower()
        except (EOFError, KeyboardInterrupt):
            out()
            a = ""
        code = table.get(a)
        if code:
            break
        out(f"  {RED}1 / 2{RESET}")
    set_lang(code)
    cfg["lang"] = code
    save_cfg(cfg)
    return code


def ask_name(cfg):
    """Спрашивает имя или псевдоним. Enter — оставить как есть / пропустить."""
    cur = cfg.get("name", "")
    out()
    typewriter(tr("  {0}Как к тебе обращаться?{1} {2}имя или псевдоним · Enter — ").format(WHITE, RESET, GREY)
               + (tr("оставить «{0}»").format(cur) if cur else tr("пропустить")) + RESET)
    try:
        raw = input(prompt_safe(f"  {ACCENT}❯{RESET} "))
    except (EOFError, KeyboardInterrupt):
        out()
        raw = ""
    name = clean_name(raw) or cur
    cfg["name"] = name
    save_cfg(cfg)
    if name and name != cur:
        typewriter(tr("  {0}Приятно познакомиться, {1}!{2}").format(ACCENT, name, RESET))
    return name
