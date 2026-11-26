# -*- coding: utf-8 -*-
"""Запросы к ИИ (стриминг ответа)."""

import json
import urllib.error
import urllib.request

from .config import DEFAULT_SYSTEM
from .server import SERVER
from .i18n import tr


# ───────────────────────── запросы к ИИ ─────────────────────────
def stream_reply(cfg, history, system=None):
    kind = cfg["kind"]
    if kind == "gguf":
        base = SERVER.ensure(cfg)
        kind = "openai"
    else:
        base = cfg["base"].rstrip("/")
    system = system or cfg.get("system") or DEFAULT_SYSTEM
    key = cfg.get("key", "").strip()
    if kind == "anthropic":
        url = base + "/v1/messages"
        headers = {"x-api-key": key, "anthropic-version": "2023-06-01",
                   "content-type": "application/json"}
        body = {"model": cfg["model"], "max_tokens": 4096, "stream": True,
                "system": system, "messages": history}
    else:
        url = base + "/chat/completions"
        headers = {"content-type": "application/json"}
        if key:
            headers["Authorization"] = "Bearer " + key
        body = {"model": cfg["model"], "stream": True,
                "messages": [{"role": "system", "content": system}] + history}
    req = urllib.request.Request(url, data=json.dumps(body).encode("utf-8"),
                                 headers=headers, method="POST")
    try:
        resp = urllib.request.urlopen(req, timeout=120)
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", "ignore")[:400]
        raise RuntimeError(f"HTTP {e.code}: {raw}")
    except urllib.error.URLError as e:
        raise RuntimeError(tr("нет соединения: {0}").format(e.reason))
    with resp:
        for raw in resp:
            line = raw.decode("utf-8", "ignore").strip()
            if not line.startswith("data:"):
                continue
            data = line[5:].strip()
            if not data or data == "[DONE]":
                continue
            try:
                obj = json.loads(data)
            except ValueError:
                continue
            if kind == "anthropic":
                t = obj.get("type")
                if t == "content_block_delta":
                    txt = (obj.get("delta") or {}).get("text")
                    if txt:
                        yield txt
                elif t == "error":
                    raise RuntimeError((obj.get("error") or {}).get("message", "error"))
            else:
                ch = obj.get("choices") or []
                if ch:
                    txt = (ch[0].get("delta") or {}).get("content")
                    if txt:
                        yield txt
