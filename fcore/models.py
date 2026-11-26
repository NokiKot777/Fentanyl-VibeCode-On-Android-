# -*- coding: utf-8 -*-
"""Каталог GGUF-моделей и скачивание."""

import json
import os
import shutil
import time
import urllib.error
import urllib.request

from .term import ACCENT, GREY, RED, RESET, YELLOW, hide_cursor, out, show_cursor, width
from .i18n import tr


# ───────────────────────── каталог моделей GGUF ─────────────────────────
CATALOG = [
    dict(name="Qwen2.5-Coder 0.5B", repo="Qwen/Qwen2.5-Coder-0.5B-Instruct-GGUF",
         file="qwen2.5-coder-0.5b-instruct-q4_k_m.gguf", gb=0.4, note="самая лёгкая, для слабых телефонов"),
    dict(name="Qwen2.5-Coder 1.5B", repo="Qwen/Qwen2.5-Coder-1.5B-Instruct-GGUF",
         file="qwen2.5-coder-1.5b-instruct-q4_k_m.gguf", gb=1.12, note="баланс скорости и качества"),
    dict(name="Qwen2.5-Coder 3B", repo="Qwen/Qwen2.5-Coder-3B-Instruct-GGUF",
         file="qwen2.5-coder-3b-instruct-q4_k_m.gguf", gb=2.1, note="лучший код на 6+ ГБ RAM"),
    dict(name="Qwen2.5-Coder 7B", repo="bartowski/Qwen2.5-Coder-7B-Instruct-GGUF",
         file="Qwen2.5-Coder-7B-Instruct-Q4_K_M.gguf", gb=4.7, note="сильная, нужно 8+ ГБ RAM"),
    dict(name="Llama 3.2 1B", repo="bartowski/Llama-3.2-1B-Instruct-GGUF",
         file="Llama-3.2-1B-Instruct-Q4_K_M.gguf", gb=0.8, note="общий чат, быстрая"),
    dict(name="Llama 3.2 3B", repo="bartowski/Llama-3.2-3B-Instruct-GGUF",
         file="Llama-3.2-3B-Instruct-Q4_K_M.gguf", gb=2.0, note="общий чат"),
]
CATALOG_FILE = os.path.join(os.path.expanduser("~"), ".fentanyl_catalog.json")


def models_dir():
    d = os.path.expanduser("~/models")
    os.makedirs(d, exist_ok=True)
    return d


def full_catalog():
    cat = list(CATALOG)
    try:  # свои модели: список объектов с теми же полями
        with open(CATALOG_FILE, encoding="utf-8") as f:
            for e in json.load(f):
                if all(k in e for k in ("name", "repo", "file")):
                    e.setdefault("gb", 0)
                    e.setdefault("note", "")
                    cat.append(e)
    except (OSError, ValueError):
        pass
    return cat


def mem_gb():
    try:
        with open("/proc/meminfo") as f:
            for ln in f:
                if ln.startswith("MemTotal"):
                    return int(ln.split()[1]) / 1048576
    except OSError:
        pass
    return None


def hf_url(entry):
    return f"https://huggingface.co/{entry['repo']}/resolve/main/{entry['file']}"


def download_file(url, dest):
    """Скачивание с докачкой и прогрессом. True — готово."""
    part = dest + ".part"
    have = os.path.getsize(part) if os.path.exists(part) else 0
    headers = {"User-Agent": "fentanyl/beta"}
    if have:
        headers["Range"] = f"bytes={have}-"
    try:
        resp = urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=60)
    except urllib.error.HTTPError as e:
        if e.code == 416 and have:  # уже докачано
            os.replace(part, dest)
            return True
        out(f"  {RED}HTTP {e.code}: " + (tr("файла нет по этой ссылке — каталог мог устареть, дай прямую ссылку: /download <url>") if e.code == 404 else tr("не удалось скачать")) + RESET)
        return False
    except urllib.error.URLError as e:
        out(tr("  {0}нет соединения: {1}{2}").format(RED, e.reason, RESET))
        return False
    with resp:
        resumed = resp.status == 206
        if not resumed:
            have = 0
        try:
            total = int(resp.headers.get("Content-Length", 0)) + have
        except ValueError:
            total = 0
        free = shutil.disk_usage(os.path.dirname(dest) or ".").free
        if total and free < (total - have) * 1.02:
            out(tr("  {0}мало места: нужно {1:.1f} ГБ, свободно {2:.1f} ГБ{3}").format(RED, ((total - have) / 1e9), (free / 1e9), RESET))
            return False
        done, t0, last, base = have, time.time(), 0, have
        hide_cursor()
        try:
            with open(part, "ab" if resumed else "wb") as f:
                while True:
                    chunk = resp.read(256 * 1024)
                    if not chunk:
                        break
                    f.write(chunk)
                    done += len(chunk)
                    now = time.time()
                    if now - last > 0.2:
                        last = now
                        speed = (done - base) / max(now - t0, 0.1)
                        bw = max(10, min(24, width() - 40))
                        frac = done / total if total else 0
                        bar = ACCENT + "█" * int(bw * frac) + GREY + "░" * (bw - int(bw * frac)) + RESET
                        eta = tr("{0} с").format(int((total - done) / speed)) if total and speed else "…"
                        out(tr("\r\u001b[2K  {0} {1:3d}%  {2:.0f}/{3:.0f} МБ  {4:.1f} МБ/с  ост. {5}").format(bar, int(frac * 100), (done / 1e6), (total / 1e6), (speed / 1e6), eta), "")
        except KeyboardInterrupt:
            out(tr("\n  {0}■ остановлено — повтори команду, скачивание продолжится{1}").format(YELLOW, RESET))
            return False
        except OSError as e:
            out(tr("\n  {0}ошибка записи: {1}{2}").format(RED, e, RESET))
            return False
        finally:
            show_cursor()
    out()
    if total and done < total:
        out(tr("  {0}скачано не полностью — повтори команду для докачки{1}").format(RED, RESET))
        return False
    os.replace(part, dest)
    return True
