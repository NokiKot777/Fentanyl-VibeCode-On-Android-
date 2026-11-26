# -*- coding: utf-8 -*-
"""Автопроверка проекта после правок ИИ + окно предпросмотра (HTML / Python / Node / sh)."""

import functools
import http.server
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time
import urllib.parse
import webbrowser

from .anim import Spinner, ok_line
from .config import save_cfg
from .term import ACCENT, ANSI, GREY, RED, RESET, YELLOW, box, out
from .tools import ask_line, in_project
from .i18n import tr

PREFER = {
    "python": ("main.py", "app.py", "run.py", "server.py", "game.py", "bot.py"),
    "node": ("index.js", "main.js", "app.js", "server.js"),
}
# ошибки окружения (нет экрана и т.п.) — не баг проекта
ENV_LIMIT = re.compile(r"no display name|TclError|no available video device|cannot connect to X server|"
                       r"could not connect to display|Unable to init server", re.I)
SECRET = re.compile(r"KEY|TOKEN|SECRET|PASSWORD|PASSWD|CREDENTIAL", re.I)
REF = re.compile(r"""(?:src|href)\s*=\s*["']([^"'#?]+)""", re.I)
MODES = ("off", "warn", "fix")


def _clean(s):
    """Вывод программы без управляющих кодов — в терминал попадает только текст."""
    s = ANSI.sub("", s)
    return "".join(c for c in s if c in "\n\t" or c.isprintable())


# ───────────────────────── что проверять ─────────────────────────
def _pick(cands, prefs):
    for pr in prefs:
        for p in cands:
            if os.path.basename(p).lower() == pr:
                return p
    for p in cands:
        try:
            with open(p, encoding="utf-8", errors="replace") as f:
                if "__main__" in f.read(200_000):
                    return p
        except OSError:
            pass
    return cands[-1]


def _is_entry(kind, path):
    if os.path.basename(path).lower() in PREFER.get(kind, ()) + ("index.html",):
        return True
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            return "__main__" in f.read(200_000)
    except OSError:
        return False


def find_target(paths=None):
    """(вид, файл) — что запускать/показывать. paths — файлы, которые только что менял ИИ."""
    files = [os.path.abspath(p) for p in (paths or [])]
    files = [p for p in files if os.path.isfile(p) and in_project(p)]
    if not files:
        for name in ("index.html", "main.py", "app.py", "run.py", "index.js", "main.js", "app.js"):
            if os.path.isfile(name):
                files = [os.path.abspath(name)]
                break
    ext = lambda *e: [p for p in files if p.lower().endswith(e)]  # noqa: E731
    if ext(".html", ".htm"):
        return "html", _pick(ext(".html", ".htm"), ("index.html",))
    if ext(".py"):
        return "python", _pick(ext(".py"), PREFER["python"])
    if ext(".js", ".mjs", ".cjs"):
        return "node", _pick(ext(".js", ".mjs", ".cjs"), PREFER["node"])
    if ext(".sh"):
        return "sh", ext(".sh")[-1]
    return None


def static_issues(paths):
    """Синтаксис и битые ссылки — без запуска кода."""
    issues, node = [], shutil.which("node")
    for p in paths:
        low, rel = p.lower(), os.path.relpath(p)
        try:
            with open(p, encoding="utf-8", errors="replace") as f:
                src = f.read()
        except OSError:
            continue
        if low.endswith(".py"):
            try:
                compile(src, p, "exec")
            except (SyntaxError, ValueError) as e:
                issues.append(tr("{0}, строка {1}: {2}").format(rel, getattr(e, 'lineno', '?'), getattr(e, 'msg', e)))
        elif low.endswith((".js", ".mjs", ".cjs")) and node:
            try:
                r = subprocess.run([node, "--check", p], capture_output=True, text=True, timeout=10)
                if r.returncode:
                    msg = [ln for ln in _clean(r.stderr).split("\n") if ln.strip()]
                    issues.append(f"{rel}: " + (next((m for m in msg if "Error" in m), msg[0]) if msg else tr("ошибка синтаксиса")))
            except (OSError, subprocess.TimeoutExpired):
                pass
        elif low.endswith((".html", ".htm")):
            base = os.path.dirname(p)
            for ref in REF.findall(src):
                if re.match(r"^(\w+:|//)", ref):  # http:, data:, mailto: …
                    continue
                if not os.path.exists(os.path.join(base, urllib.parse.unquote(ref))):
                    issues.append(tr("{0}: не найден файл «{1}»").format(rel, ref))
    return issues


# ───────────────────────── запуск ─────────────────────────
def _limits():  # только POSIX: не даём программе писать гигабайты вывода
    try:
        import resource
        resource.setrlimit(resource.RLIMIT_FSIZE, (5_000_000, 5_000_000))
    except Exception:  # noqa: BLE001
        pass


def _command(kind, entry):
    if kind == "python":
        return [sys.executable, entry]
    if kind == "node":
        exe = shutil.which("node")
        return [exe, entry] if exe else None
    if kind == "sh":
        exe = shutil.which("bash") or shutil.which("sh")
        return [exe, entry] if exe else None
    return None


def run_entry(kind, entry, timeout):
    """Запускает файл с таймаутом и без секретов в окружении. Возвращает (код, stdout, stderr, сек, таймаут?)."""
    cmd = _command(kind, entry)
    if not cmd:
        return None
    env = {k: v for k, v in os.environ.items() if not SECRET.search(k)}
    env.update(PYTHONUNBUFFERED="1", PYTHONDONTWRITEBYTECODE="1", PYTHONIOENCODING="utf-8")
    posix = os.name != "nt"
    t0, timed_out = time.time(), False
    with tempfile.TemporaryFile() as fo, tempfile.TemporaryFile() as fe:
        p = subprocess.Popen(cmd, cwd=os.getcwd(), stdin=subprocess.DEVNULL, stdout=fo, stderr=fe, env=env,
                             start_new_session=posix, preexec_fn=_limits if posix else None)
        try:
            p.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            timed_out = True
        except KeyboardInterrupt:
            timed_out = True
        finally:
            if p.poll() is None:  # убиваем всю группу процессов, чтобы не оставались сироты
                try:
                    os.killpg(p.pid, signal.SIGKILL) if posix else p.kill()
                except OSError:
                    pass
                p.wait()
        res = []
        for f in (fo, fe):
            f.seek(0)
            res.append(_clean(f.read(60_000).decode("utf-8", "replace")))
    return p.returncode, res[0], res[1], time.time() - t0, timed_out


def evaluate(st, kind, entry, paths=None):
    """Проверка: статические ошибки + запуск. Возвращает словарь результата."""
    timeout = int(st.cfg.get("check_timeout", 8))
    rel = os.path.relpath(entry)
    cmd = " ".join([{"python": "python", "node": "node", "sh": "sh"}.get(kind, ""), rel]).strip()
    r = {"kind": kind, "entry": entry, "rel": rel, "cmd": cmd, "issues": static_issues(paths or [entry]),
         "out": "", "err": "", "code": None, "secs": 0.0, "timeout": False, "note": "", "bug": False}
    if r["issues"] or kind == "html":
        r["bug"] = bool(r["issues"])
        return r
    sp = Spinner([tr("запускаю проект"), tr("смотрю в консоль")])
    sp.start()
    try:
        ran = run_entry(kind, entry, timeout)
    finally:
        sp.stop()
    if ran is None:
        r["note"] = tr("нужный интерпретатор не найден — запуск пропущен")
        return r
    r["code"], r["out"], r["err"], r["secs"], r["timeout"] = ran
    text = r["err"] + r["out"]
    if r["timeout"]:
        r["note"] = tr("работает дольше {0} с — остановил (для серверов и игр это нормально)").format(timeout)
    elif r["code"] != 0:
        if ENV_LIMIT.search(text):
            r["note"] = tr("нужен графический экран — запуск здесь невозможен")
        elif "EOFError" in text and "input" in text:
            r["note"] = tr("программа ждёт ввод с клавиатуры — дальше не проверял")
        else:
            r["bug"] = True
    return r


def _tail(text, n):
    lines = [ln.rstrip() for ln in text.rstrip("\n").split("\n")] if text.strip() else []
    return ([tr("… ещё {0} строк выше").format((len(lines) - n))] if len(lines) > n else []) + lines[-n:]


def bug_text(r):
    parts = list(r["issues"])
    if r["code"] not in (None, 0):
        parts.append("\n".join(_tail(r["err"] or r["out"], 25)))
    return "\n".join(p for p in parts if p)[:3000]


def report(r, window=True):
    """Окно предпросмотра: что вывела программа и чем всё закончилось."""
    bug = r["bug"]
    if not window and not bug:
        return ok_line(tr("проверка: {0} — ошибок нет").format(r['cmd'] or r['rel']))
    rows = [f"{RED}✗ {i}{RESET}" for i in r["issues"]]
    rows += [f"{GREY}{ln}{RESET}" for ln in _tail(r["out"], 10)]
    rows += [f"{RED}{ln}{RESET}" for ln in _tail(r["err"], 8)] if (r["err"] and (bug or r["code"])) else \
            [f"{YELLOW}{ln}{RESET}" for ln in _tail(r["err"], 4)]
    if not r["issues"] and not rows:
        rows.append(tr("{0}(программа ничего не вывела){1}").format(GREY, RESET))
    rows.append("")
    if bug:
        rows.append(tr("{0}✗ найдена ошибка").format(RED) + (tr(" · код {0}").format(r['code']) if r["code"] else "") + RESET)
    elif r["note"]:
        rows.append(f"{YELLOW}● {r['note']}{RESET}")
    else:
        rows.append(tr("{0}✓ завершилось без ошибок · {1:.1f} с{2}").format(ACCENT, r['secs'], RESET))
    out()
    box(rows, tr("Предпросмотр") + (f" · {r['cmd']}" if r["cmd"] else f" · {r['rel']}"), RED if bug else ACCENT)


# ───────────────────────── предпросмотр HTML ─────────────────────────
class _Handler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def do_GET(self):
        # скрытые файлы (.env, .git …) не отдаём
        if any(seg.startswith(".") for seg in urllib.parse.unquote(self.path).split("?")[0].split("/") if seg):
            return self.send_error(404)
        return super().do_GET()


def serve_html(entry):
    """Локальный сервер только на 127.0.0.1 + браузер; ждёт Enter и закрывается."""
    handler = functools.partial(_Handler, directory=os.getcwd())
    try:
        httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    except OSError as e:
        return out(tr("  {0}не удалось запустить предпросмотр: {1}{2}").format(RED, (e.strerror or e), RESET))
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    rel = os.path.relpath(entry).replace(os.sep, "/")
    url = f"http://127.0.0.1:{httpd.server_address[1]}/{urllib.parse.quote(rel)}"
    try:
        opened = webbrowser.open(url)
    except Exception:  # noqa: BLE001
        opened = False
    out()
    box([f"{ACCENT}{url}{RESET}",
         tr("{0}открыто в браузере{1}").format(GREY, RESET) if opened else tr("{0}открой этот адрес в браузере{1}").format(YELLOW, RESET),
         "", tr("{0}Enter — закрыть предпросмотр{1}").format(GREY, RESET)], tr("Предпросмотр · {0}").format(rel), ACCENT)
    try:
        input()
    except (EOFError, KeyboardInterrupt):
        pass
    finally:
        httpd.shutdown()
        httpd.server_close()
    ok_line(tr("предпросмотр закрыт"))


# ───────────────────────── автопроверка ─────────────────────────
def ensure_trust(st):
    """Автозапуск кода от ИИ — только с согласия пользователя."""
    if st.cfg.get("check_trust"):
        return True
    ans = ask_line(tr("  Запустить проект для проверки? {0}y — да · a — всегда · n — нет{1}").format(GREY, RESET)).strip().lower()
    if ans in ("a", "а", "always", "всегда"):
        st.cfg["check_trust"] = True
        save_cfg(st.cfg)
        out(tr("  {0}автозапуск включён (отключить: /check off){1}").format(YELLOW, RESET))
        return True
    return ans in ("y", "yes", "д", "да")


def fix_message(r):
    return (tr("Автопроверка запустила `{0}` и нашла ошибку:\n```\n{1}\n```\nНайди причину и исправь минимальными правками, не ломая остальное.").format(r['cmd'] or r['rel'], bug_text(r)))


def auto_check(st, paths):
    """Вызывается после правок ИИ. Возвращает текст для ИИ (исправить ошибку) или None."""
    mode = st.cfg.get("check", "warn")
    show = st.cfg.get("preview", True)
    target = find_target(paths)
    if not target or (mode == "off" and not show):
        return None
    kind, entry = target
    last = getattr(st, "last_entry", None)  # правили вспомогательный файл — проверяем основной
    if last and kind == last[0] and entry != last[1] and os.path.isfile(last[1]) and not _is_entry(kind, entry):
        entry = last[1]
    st.last_entry = (kind, entry)
    if kind == "html" and mode == "off":
        return preview_now(st, kind, entry)
    if kind != "html" and not ensure_trust(st):  # статическая проверка html безопасна — без вопросов
        return None
    r = evaluate(st, kind, entry, paths)
    if r["bug"]:
        report(r)
        tries = int(st.cfg.get("check_tries", 2))
        if st.fix_tries >= tries:
            out(tr("  {0}лимит авто-исправлений ({1}) — напиши, что поправить{2}").format(YELLOW, tries, RESET))
            return None
        if mode == "fix":
            out(tr("  {0}↻ отправляю ошибку ИИ на исправление{1} {2}(попытка {3}/{4}){5}").format(ACCENT, RESET, GREY, (st.fix_tries + 1), tries, RESET))
            return fix_message(r)
        ans = ask_line(tr("  Попросить ИИ исправить? {0}Y/n · /check fix — всегда сам{1}").format(GREY, RESET)).strip().lower()
        return None if ans in ("n", "н", "no", "нет") else fix_message(r)
    st.fix_tries = 0
    if kind == "html":
        if show:
            return preview_now(st, kind, entry)
        return ok_line(tr("проверка: {0} — битых ссылок нет").format(r['rel']))
    report(r, window=show)
    return None


def preview_now(st, kind, entry, paths=None):
    """Показать результат сейчас (команда /preview и ответ «да» на предложение)."""
    if kind == "html":
        issues = static_issues(paths or [entry])
        for i in issues:
            out(f"  {YELLOW}⚠ {i}{RESET}")
        ans = ask_line(tr("  Открыть предпросмотр в браузере? {0}Y/n{1}").format(GREY, RESET)).strip().lower()
        if ans not in ("n", "н", "no", "нет"):
            serve_html(entry)
        return None
    if not ensure_trust(st):
        return None
    report(evaluate(st, kind, entry, paths))
    return None
