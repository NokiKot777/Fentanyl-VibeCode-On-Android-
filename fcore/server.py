# -*- coding: utf-8 -*-
"""Встроенный GGUF-сервер (llama-server)."""

import atexit
import os
import shutil
import socket
import subprocess
import sys
import time
import urllib.request

from .anim import Spinner
from .i18n import tr


# ───────────────────────── встроенный GGUF-сервер ─────────────────────────
START_DIR = os.path.abspath(".")  # папка запуска; рабочая папка проекта может быть другой
MODEL_DIRS = ["~/models", "~/storage/downloads", "~/Download", "~/Downloads", START_DIR]
SERVER_LOG = os.path.join(os.path.expanduser("~"), ".fentanyl_server.log")


def find_server_bin():
    for name in ("llama-server", "llama-cpp-server"):
        p = shutil.which(name)
        if p:
            return p
    prefix = os.environ.get("PREFIX", "")
    for p in (os.path.join(prefix, "bin", "llama-server"),
              os.path.expanduser("~/llama.cpp/build/bin/llama-server"),
              os.path.expanduser("~/llama.cpp/llama-server")):
        if p and os.path.isfile(p) and os.access(p, os.X_OK):
            return p
    return None


def find_ggufs():
    found = []
    for d in MODEL_DIRS:
        d = os.path.expanduser(d)
        try:
            for fn in sorted(os.listdir(d)):
                if fn.lower().endswith(".gguf"):
                    full = os.path.abspath(os.path.join(d, fn))
                    if full not in found:
                        found.append(full)
        except OSError:
            continue
    return found


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _die_with_parent():
    """Linux/Android: сервер сам завершится, если CLI убили."""
    try:
        import ctypes
        ctypes.CDLL("libc.so.6", use_errno=True).prctl(1, 15)  # PR_SET_PDEATHSIG, SIGTERM
    except Exception:
        pass


class LocalServer:
    """llama-server как подпроцесс: сам стартует, сам перезапускается, сам гасится."""

    def __init__(self):
        self.proc = None
        self.port = None
        self.model = None
        self.base = None
        self._log = None
        atexit.register(self.stop)

    def running(self):
        return self.proc is not None and self.proc.poll() is None

    def _tail(self, n=6):
        try:
            with open(SERVER_LOG, encoding="utf-8", errors="replace") as f:
                return "".join(f.readlines()[-n:]).strip()
        except OSError:
            return ""

    def _healthy(self):
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{self.port}/health", timeout=2) as r:
                return r.status == 200
        except Exception:
            return False  # 503 = модель ещё грузится

    @staticmethod
    def params(cfg):
        path = os.path.expanduser(cfg.get("gguf", ""))
        ctx = int(cfg.get("ctx") or 4096)
        threads = int(cfg.get("threads") or max(2, min(6, (os.cpu_count() or 4) // 2)))
        if cfg.get("battery"):  # режим экономии батареи
            ctx, threads = min(ctx, 2048), 2
        return path, ctx, threads

    def start(self, cfg):
        path, ctx, threads = self.params(cfg)
        self.sig = (path, ctx, threads)
        if not path or not os.path.isfile(path):
            raise RuntimeError(tr("файл модели не найден: {0}  ·  /gguf <путь>").format((path or tr("(не задан)"))))
        binary = find_server_bin()
        if not binary:
            raise RuntimeError(tr("не найден llama-server. Termux: pkg install llama-cpp  (или собери llama.cpp и добавь в PATH)"))
        self.stop()
        self.port = free_port()
        self.model = path
        self.base = f"http://127.0.0.1:{self.port}/v1"
        cmd = [binary, "-m", path, "--host", "127.0.0.1", "--port", str(self.port),
               "-c", str(ctx), "-t", str(threads)]
        kw = {}
        if os.name != "nt":
            kw["start_new_session"] = True
            if sys.platform.startswith("linux"):
                kw["preexec_fn"] = _die_with_parent
        self._log = open(SERVER_LOG, "w", encoding="utf-8")
        self.proc = subprocess.Popen(cmd, stdin=subprocess.DEVNULL, stdout=self._log,
                                     stderr=subprocess.STDOUT, **kw)
        name = os.path.basename(path)
        sp = Spinner([tr("загружаю {0}").format(name), tr("читаю веса"), tr("почти готово")])
        sp.start()
        try:
            t0 = time.time()
            while time.time() - t0 < 600:
                if self.proc.poll() is not None:
                    raise RuntimeError(tr("llama-server завершился:\n") + self._tail())
                if self._healthy():
                    return
                time.sleep(0.5)
            raise RuntimeError(tr("модель не загрузилась за 10 минут (мало RAM?)\n") + self._tail())
        except BaseException:
            sp.stop()
            self.stop()
            raise
        finally:
            sp.stop()

    def ensure(self, cfg):
        """Вызывается перед каждым запросом: поднимет или перезапустит сервер."""
        if not self.running() or getattr(self, "sig", None) != self.params(cfg):
            self.start(cfg)
        return self.base

    def stop(self):
        p, self.proc = self.proc, None
        if p is not None and p.poll() is None:
            try:
                p.terminate()
                p.wait(timeout=5)
            except Exception:
                try:
                    p.kill()
                except Exception:
                    pass
        if self._log:
            try:
                self._log.close()
            except Exception:
                pass
            self._log = None


SERVER = LocalServer()
