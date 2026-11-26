# -*- coding: utf-8 -*-
"""Языки интерфейса (ru / en). tr(текст) возвращает перевод, если выбран English."""

LANGS = {"ru": "Русский", "en": "English"}
LANG = "ru"
_EN = None


def set_lang(code):
    global LANG
    LANG = code if code in LANGS else "ru"


def get_lang():
    return LANG


def tr(s):
    """Перевод строки-шаблона. В русском режиме и для неизвестных строк — как есть."""
    global _EN
    if LANG != "en":
        return s
    if _EN is None:
        from .lang_en import EN
        _EN = EN
    return _EN.get(s, s)
