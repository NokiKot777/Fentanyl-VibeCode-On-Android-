# -*- coding: utf-8 -*-
"""Рендер ответа модели: перенос по словам, markdown, блоки кода в рамке."""

import re

from .term import ACCENT, BOLD, CODE, GREY, RESET, WHITE, clip, out, width
from .i18n import tr

SEP_ROW = re.compile(r"^[\s:\-|]+$")
RULE = re.compile(r"^(-{3,}|\*{3,}|_{3,})\s*$")
NUM = re.compile(r"(\d{1,3}[.)]) ")
TAGS = ("<think>", "</think>")


class Renderer:
    """Потоковый рендер. Результат не зависит от того, кусками какого размера пришёл текст."""

    def __init__(self):
        self.in_code = False
        self.lang = ""
        self.cur = []
        self.blocks = []
        self.lbuf = ""      # строка, пока не понятно, что это (код, список, заголовок…)
        self.kind = None    # None | text head bullet num quote table rule fence code
        self.fbuf = ""      # накопление служебных строк (fence / table / rule)
        self.raw = ""       # исходная строка кода
        self.w = width()
        self.col = 0
        self.indent = 2
        self.base = ""
        self.word = ""
        self.wlen = 0
        self.sp = False
        self.bold = self.tick = self.star = False
        self.in_think = False   # внутри <think>…</think>
        self.hide_think = False  # прятать рассуждение
        self.skip_nl = False
        self.tag = ""

    # ── стили ──
    def _style(self):
        return self.base + (BOLD if self.bold else "") + (CODE if self.tick else "")

    def _prefix_wrap(self):
        if self.kind in ("quote", "think"):
            return f"  {GREY}{'▎' if self.kind == 'quote' else '▏'}{RESET} "
        return " " * self.indent

    # ── блоки кода ──
    def _fence(self, info):
        fw = max(20, min(self.w - 4, 60))
        if not self.in_code:
            self.in_code = True
            self.lang = info.strip()
            self.cur = []
            label = f" {self.lang or 'code'} "
            out(f"  {GREY}╭─{RESET}{ACCENT}{label}{RESET}{GREY}" + "─" * max(2, fw - len(label) - 2) + RESET)
        else:
            self.in_code = False
            self.blocks.append((self.lang, "\n".join(self.cur)))
            out(f"  {GREY}╰" + "─" * fw + RESET)

    def _code_put(self, d):
        if self.col >= max(10, self.w - 6):  # длинная строка кода: перенос с той же рамкой
            out(f"{RESET}\n  {GREY}│{RESET} {CODE}", "")
            self.col = 0
        out(d, "")
        self.col += 1

    # ── обычный текст со словами ──
    def _add(self, ch):
        self.word += ch
        self.wlen += 1
        if self.wlen >= self.w - self.indent - 2:  # слово длиннее строки — режем
            self._flush_word()

    def _toggle(self, what):
        setattr(self, what, not getattr(self, what))
        self.word += RESET + self._style()

    def _flush_word(self):
        if not self.word:
            return
        need = self.wlen + (1 if self.sp else 0)
        if self.col > self.indent and self.col + need > self.w - 1:
            out(RESET + "\n" + self._prefix_wrap() + self._style(), "")
            self.col = self.indent
        elif self.sp and self.col > self.indent:
            out(" ", "")
            self.col += 1
        out(self.word, "")
        self.col += self.wlen
        self.word, self.wlen, self.sp = "", 0, False

    def _text_put(self, ch):
        if self.tick:
            if ch == "`":
                self._toggle("tick")
            elif ch in " \t":
                self._flush_word()
                self.sp = True
            else:
                self._add(ch)
            return
        if self.star:
            self.star = False
            if ch == "*":
                self._toggle("bold")
                return
            self._add("*")
        if ch == "*":
            self.star = True
        elif ch == "`":
            self._toggle("tick")
        elif ch in " \t":
            self._flush_word()
            self.sp = True
        else:
            self._add(ch)

    def _end_text_line(self):
        if self.star:
            self._add("*")
        self._flush_word()
        out(RESET)
        self.bold = self.tick = self.star = False
        self.sp = False

    # ── определение вида строки ──
    def _classify(self, st):
        if self.in_think and not self.in_code:
            return "think"
        if st.startswith("```"):
            return "fence"
        if self.in_code:
            return "code"
        if RULE.match(st) or st[:3] in ("---", "***", "___"):
            return "rule"
        if st.startswith("#"):
            return "head"
        if st[:2] in ("- ", "* ", "• ", "+ "):
            return "bullet"
        if NUM.match(st):
            return "num"
        if st.startswith(">"):
            return "quote"
        if st.startswith("|"):
            return "table"
        return "text"

    def _open(self, kind, raw, st):
        """Печатает начало строки, возвращает остаток текста."""
        lead = min(len(raw) - len(st), 8)
        self.col, self.indent, self.base = 2, 2, ""
        self.word, self.wlen, self.sp = "", 0, False
        if kind == "fence":
            self.fbuf = ""
            return st[3:]
        if kind in ("rule", "table"):
            self.fbuf = ""
            return st
        if kind == "code":
            out(f"  {GREY}│{RESET} {CODE}", "")
            self.col, self.raw = 0, ""
            return raw
        if kind == "head":
            self.base = BOLD + ACCENT
            body = st.lstrip("#").lstrip()
            out("  " + self.base, "")
            return body
        if kind == "bullet":
            self.indent = 4 + lead
            mark = "◦" if lead >= 2 else "•"
            out(" " * (2 + lead) + f"{ACCENT}{mark}{RESET} ", "")
            self.col = self.indent
            return st[2:]
        if kind == "num":
            m = NUM.match(st)
            self.indent = 2 + lead + len(m.group(1)) + 1
            out(" " * (2 + lead) + f"{ACCENT}{m.group(1)}{RESET} ", "")
            self.col = self.indent
            return st[m.end():]
        if kind == "think":
            self.base, self.indent = GREY, 4
            out(f"  {GREY}▏{RESET} {self.base}", "")
            self.col = 4
            return st
        if kind == "quote":
            self.base, self.indent = GREY, 4
            out(f"  {GREY}▎{RESET} {self.base}", "")
            self.col = 4
            return st[1:].lstrip()
        out("  ", "")
        return st

    def _decide(self, final):
        raw = self.lbuf.rstrip("\n")
        st = raw.lstrip()
        self.lbuf = ""
        self.w = width()
        if not st and not self.in_code:
            self.kind = None
            if final:
                out()
            return
        self.kind = self._classify(st)
        rest = self._open(self.kind, raw, st)
        for c in rest:
            self._body(c)
        if final:
            self._body("\n")

    # ── обработка символа ──
    def _body(self, ch):
        k = self.kind
        if k == "code":
            if ch == "\n":
                self.cur.append(self.raw)
                out(RESET)
                self.kind = None
                return
            self.raw += ch
            for d in ("    " if ch == "\t" else ch):
                self._code_put(d)
        elif k in ("fence", "table", "rule"):
            if ch != "\n":
                self.fbuf += ch
                return
            self.kind = None
            line = self.fbuf.strip()
            if k == "fence":
                self._fence(self.fbuf)
            elif k == "table":
                if SEP_ROW.match(line):
                    out(f"  {GREY}" + "─" * min(self.w - 4, 40) + RESET)
                else:
                    cells = [re.sub(r"\*\*|`", "", c).strip() for c in line.strip("|").split("|")]
                    out("  " + clip(f" {GREY}│{RESET} ".join(cells), self.w - 4))
            elif RULE.match(line):
                out(f"  {GREY}" + "─" * min(self.w - 4, 40) + RESET)
            else:  # не разделитель, а обычный текст вроде «---текст»
                self.kind = "text"
                self.col, self.indent, self.base = 2, 2, ""
                out("  ", "")
                for c in line:
                    self._text_put(c)
                self._end_text_line()
                self.kind = None
        else:
            if ch == "\n":
                self._end_text_line()
                self.kind = None
            else:
                self._text_put(ch)

    def feed(self, s):
        """Сначала ловим теги <think>…</think>, остальное — обычный рендер."""
        for ch in s:
            if self.tag:
                self.tag += ch
                if self.tag in TAGS:
                    self._think_switch(self.tag == "<think>")
                    self.tag = ""
                elif not any(t.startswith(self.tag) for t in TAGS):
                    pending, self.tag = self.tag, ""
                    for c in pending:
                        self._feed1(c)
                continue
            if ch == "<" and not self.in_code:
                self.tag = ch
                continue
            self._feed1(ch)

    def _think_switch(self, on):
        self.in_think = on
        if on:
            self.skip_nl = True
            if not self.hide_think and self.kind is None and not self.lbuf:
                out(tr("  {0}◌ рассуждение{1}").format(GREY, RESET))
        elif self.hide_think:
            self.skip_nl = True

    def _feed1(self, ch):
        if self.in_think and self.hide_think:
            return
        if self.skip_nl:
            if ch in "\r\n":
                return
            self.skip_nl = False
        if ch == "\r" or (ch < " " and ch not in "\n\t"):
            return  # управляющие символы из ответа не пускаем в терминал
        if self.kind is not None:
            self._body(ch)
            return
        self.lbuf += ch
        if ch == "\n":
            self._decide(True)
            return
        st = self.lbuf.lstrip()
        if (len(st) >= 3 and st[:3] in ("```", "---", "***", "___")) or len(st) >= 4:
            self._decide(False)

    def finish(self):
        pending, self.tag = self.tag, ""
        for c in pending:
            self._feed1(c)
        self.in_think = False
        if self.kind is None and self.lbuf:
            self._decide(False)
        k = self.kind
        if k == "code":
            self.cur.append(self.raw)
        elif k in ("fence", "table", "rule"):
            self._body("\n")
        elif k is not None:
            self._end_text_line_noeol()
        if self.in_code:
            self.blocks.append((self.lang, "\n".join(self.cur)))
            self.in_code = False
        self.kind = None
        out(RESET)

    def _end_text_line_noeol(self):
        if self.star:
            self._add("*")
        self._flush_word()
