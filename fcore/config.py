# -*- coding: utf-8 -*-
"""Настройки, провайдеры, первый запуск."""

import json
import os

from .server import SERVER, find_ggufs
from .term import ACCENT, BOLD, GREY, RED, RESET, WHITE, out
from .i18n import tr


# ───────────────────────── конфиг ─────────────────────────
PROVIDERS = [
    ("Anthropic", "anthropic", "https://api.anthropic.com", "claude-sonnet-5-5", True),
    ("OpenAI", "openai", "https://api.openai.com/v1", "gpt-4o", True),
    ("OpenRouter", "openai", "https://openrouter.ai/api/v1", "anthropic/claude-sonnet-4.5", True),
    ("Ollama (локально)", "openai", "http://127.0.0.1:11434/v1", "qwen2.5-coder", False),
    ("LM Studio (локально)", "openai", "http://127.0.0.1:1234/v1", "local-model", False),
    ("GGUF (встроенный, автозапуск)", "gguf", "http://127.0.0.1:8080/v1", "local", False),
]

DEFAULT_SYSTEM = (
    "Ты — fentanyl, ассистент-программист в терминале. Отвечай коротко и по делу, "
    "код всегда оформляй в блоках с указанием языка. Предлагай готовые правки."
)


def cfg_path():
    home = os.path.expanduser("~")
    for base in (home, os.path.dirname(os.path.dirname(os.path.abspath(__file__))), os.getcwd()):
        try:
            p = os.path.join(base, ".fentanyl.json")
            with open(p, "a"):
                pass
            return p
        except Exception:
            continue
    return ".fentanyl.json"


CFG_FILE = cfg_path()


def load_cfg():
    try:
        with open(CFG_FILE, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_cfg(cfg):
    try:
        with open(CFG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
        try:
            os.chmod(CFG_FILE, 0o600)
        except Exception:
            pass
    except Exception as e:
        out(RED + tr("Не удалось сохранить настройки: {0}").format(e) + RESET)


def ask(prompt, default=""):
    d = f" {GREY}[{default}]{RESET}" if default else ""
    try:
        v = input(f"  {ACCENT}›{RESET} {prompt}{d}: ").strip()
    except EOFError:
        v = ""
    return v or default


def ask_secret(prompt):
    try:
        import getpass
        return getpass.getpass(tr("  {0}›{1} {2} (ввод скрыт): ").format(ACCENT, RESET, prompt)).strip()
    except Exception:
        return ask(prompt)


def setup(cfg):
    out()
    out(tr("  {0}{1}Подключение{2}  {3}API или локальная ИИ{4}").format(BOLD, WHITE, RESET, GREY, RESET))
    out()
    for i, p in enumerate(PROVIDERS, 1):
        kind = "API" if p[4] else tr("локально")
        out(f"   {ACCENT}{i}{RESET}  {WHITE}{tr(p[0]):<22}{RESET}{GREY}{kind}{RESET}")
    out()
    try:
        n = int(ask(tr("Номер"), "1")) - 1
        name, kind, base, model, needs_key = PROVIDERS[n]
    except Exception:
        name, kind, base, model, needs_key = PROVIDERS[0]
    key = ""
    SERVER.stop()
    cfg.pop("gguf", None)
    if kind == "gguf":
        found = find_ggufs()
        for i, f in enumerate(found, 1):
            out(f"   {ACCENT}{i}{RESET}  {WHITE}{os.path.basename(f)}{RESET}  {GREY}{os.path.dirname(f)}{RESET}")
        v = ask(tr("Номер или путь к .gguf"), "1" if found else "")
        if v.isdigit() and 0 < int(v) <= len(found):
            v = found[int(v) - 1]
        cfg["gguf"] = os.path.expanduser(v)
        model = "local"
    elif needs_key:
        key = ask_secret(tr("API-ключ"))
        base = ask(tr("Адрес сервера"), base)
        model = ask(tr("Модель"), model)
    else:
        out(tr("  {0}Если ИИ на компьютере — укажи его IP в Wi-Fi (на телефоне 127.0.0.1 — это сам телефон).{1}").format(GREY, RESET))
        base = ask(tr("Адрес сервера"), base)
        model = ask(tr("Модель"), model)
    cfg.update(provider=name, kind=kind, base=base, model=model, key=key,
               system=cfg.get("system") or DEFAULT_SYSTEM)
    save_cfg(cfg)
    out(tr("\n  {0}✓{1} сохранено в {2}{3}{4}\n").format(ACCENT, RESET, GREY, CFG_FILE, RESET))
    return cfg
