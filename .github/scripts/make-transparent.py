#!/usr/bin/env python3
"""Hapus background solid dari SVG Pac-Man & Breakout (normal + dark).

Pemakaian:
  python3 .github/scripts/make-transparent.py FILE.svg [FILE2.svg ...]
  python3 .github/scripts/make-transparent.py --check FILE.svg [...]
"""
import re
import sys
import xml.etree.ElementTree as ET

PROTECTED = ("defs", "clipPath", "mask", "pattern")
ATTR_RE = re.compile(r'([\w:.-]+)\s*=\s*(?:"([^"]*)"|\'([^\']*)\')')
SVG_OPEN_RE = re.compile(r"<svg\b[^>]*>", re.S)
RECT_RE = re.compile(r"<rect\b[^>]*?/>|<rect\b[^>]*?>.*?</rect>", re.S)
STYLE_BLOCK_RE = re.compile(r"(<style\b[^>]*>)(.*?)(</style>)", re.S)
BG_DECL_RE = re.compile(r"background(?:-color|-image)?\s*:[^;}\"']*;?", re.I)
ROOT_RULE_RE = re.compile(
    r"((?:^|})\s*(?:svg|html|body|:root)\s*\{)([^}]*)(\})", re.I
)


def attrs(tag):
    return {m.group(1): m.group(2) if m.group(2) is not None else m.group(3)
            for m in ATTR_RE.finditer(tag)}


def num(v):
    if v is None:
        return None
    m = re.match(r"^\s*(-?\d+(?:\.\d+)?)\s*(px)?\s*$", v)
    return float(m.group(1)) if m else None


def canvas_size(svg_tag):
    a = attrs(svg_tag)
    if "viewBox" in a:
        p = re.split(r"[\s,]+", a["viewBox"].strip())
        if len(p) == 4:
            return float(p[2]), float(p[3])
    return num(a.get("width")), num(a.get("height"))


def covers(value, canvas):
    if value is None:
        return False
    if value.strip() == "100%":
        return True
    n = num(value)
    return n is not None and canvas is not None and n >= canvas * 0.98


def is_full_rect(tag, w, h):
    a = attrs(tag)
    if num(a.get("x", "0")) not in (0.0, None) or num(a.get("y", "0")) not in (0.0, None):
        return False
    return covers(a.get("width"), w) and covers(a.get("height"), h)


def protected_spans(text):
    spans = []
    for name in PROTECTED:
        for m in re.finditer(rf"<{name}\b.*?</{name}>", text, re.S):
            spans.append((m.start(), m.end()))
    return spans


def in_spans(pos, spans):
    return any(s <= pos < e for s, e in spans)


def find_full_rects(text):
    m = SVG_OPEN_RE.search(text)
    if not m:
        return []
    w, h = canvas_size(m.group(0))
    spans = protected_spans(text)
    out = []
    for r in RECT_RE.finditer(text):
        if in_spans(r.start(), spans):
            continue
        open_tag = re.match(r"<rect\b[^>]*>", r.group(0), re.S).group(0)
        if is_full_rect(open_tag, w, h):
            out.append(r)
    return out


def strip_root_style(svg_tag):
    def fix(m):
        val = BG_DECL_RE.sub("", m.group(2)).strip()
        return f' style="{val}"' if val else ""
    return re.sub(r'(\s)style\s*=\s*"([^"]*)"', lambda m: fix(m), svg_tag)


def strip_css(text):
    def block(m):
        css = ROOT_RULE_RE.sub(
            lambda r: r.group(1) + BG_DECL_RE.sub("", r.group(2)) + r.group(3),
            m.group(2),
        )
        return m.group(1) + css + m.group(3)
    return STYLE_BLOCK_RE.sub(block, text)


def process(path):
    with open(path, encoding="utf-8") as f:
        original = f.read()
    text = original

    for r in reversed(find_full_rects(text)):
        text = text[:r.start()] + text[r.end():]

    m = SVG_OPEN_RE.search(text)
    if m:
        text = text[:m.start()] + strip_root_style(m.group(0)) + text[m.end():]
    text = strip_css(text)

    ET.fromstring(text.encode("utf-8"))  # pastikan SVG tetap valid
    if text != original:
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
    return text != original


def check(path):
    with open(path, encoding="utf-8") as f:
        text = f.read()
    problems = []
    try:
        ET.fromstring(text.encode("utf-8"))
    except ET.ParseError as e:
        problems.append(f"SVG tidak valid: {e}")
    for r in find_full_rects(text):
        problems.append(f"rect penutup canvas: {r.group(0)[:100]}")
    m = SVG_OPEN_RE.search(text)
    if m and re.search(r"background", m.group(0), re.I):
        problems.append("root <svg> masih punya background")
    for b in STYLE_BLOCK_RE.finditer(text):
        if ROOT_RULE_RE.search(b.group(2)) and any(
            BG_DECL_RE.search(r.group(2)) for r in ROOT_RULE_RE.finditer(b.group(2))
        ):
            problems.append("CSS svg/html/body/:root masih punya background")
    return problems


def main():
    args = sys.argv[1:]
    do_check = "--check" in args
    files = [a for a in args if a != "--check"]
    if not files:
        sys.exit(__doc__)
    failed = False
    for p in files:
        if do_check:
            probs = check(p)
            print(f"{'FAIL' if probs else 'OK  '} {p}")
            for x in probs:
                print("   -", x)
            failed = failed or bool(probs)
        else:
            print(f"{'diubah' if process(p) else 'tidak berubah'}: {p}")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
