# -*- coding: utf-8 -*-
"""Системное: уведомления, батарея, git."""

import json
import shutil
import subprocess

from .term import out
from .i18n import tr


def notify(msg):
    if shutil.which("termux-notification"):
        try:
            subprocess.Popen(["termux-notification", "--title", "fentanyl", "--content", msg],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except OSError:
            pass
    out("\a", "")


def battery_info():
    if not shutil.which("termux-battery-status"):
        return None
    try:
        p = subprocess.run(["termux-battery-status"], capture_output=True, text=True, timeout=4)
        return json.loads(p.stdout)
    except Exception:  # noqa: BLE001
        return None


def git(*args, timeout=20):
    try:
        p = subprocess.run(["git", *args], capture_output=True, text=True, timeout=timeout, errors="replace")
        return p.returncode, (p.stdout + p.stderr).strip()
    except FileNotFoundError:
        return 127, tr("git не установлен (Termux: pkg install git)")
    except subprocess.TimeoutExpired:
        return -1, tr("git: таймаут")
