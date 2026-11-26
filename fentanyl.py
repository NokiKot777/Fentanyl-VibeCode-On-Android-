#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fentanyl — AI-ассистент для кода прямо в консоли (в духе Codex / Claude Code).
Только стандартная библиотека Python: ничего ставить не нужно.

Режимы:
  - API: Anthropic / OpenAI / OpenRouter (ключ вводишь при первом запуске)
  - Локальная ИИ: Ollama / LM Studio (любой OpenAI-совместимый сервер)
  - GGUF: встроенный автозапуск llama-server (модель .gguf прямо на телефоне)

Запуск:  python fentanyl.py            (--plain  без цветов и анимаций)
"""

from fcore.app import main
from fcore.server import SERVER
from fcore.term import show_cursor

if __name__ == "__main__":
    try:
        main()
    finally:
        SERVER.stop()
        show_cursor()
