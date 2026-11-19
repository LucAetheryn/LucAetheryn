#!/usr/bin/env python3
"""Tema neon untuk SVG Pac-Man & Breakout (hanya file yang diberikan).

Pemakaian:
  python3 .github/scripts/neon-theme.py FILE.svg [FILE2.svg ...]
"""
import re
import sys
import xml.etree.ElementTree as ET

# Peta warna GitHub (terang & gelap) -> sel gelap + hijau neon.
COLOR_MAP = {
    "#ebedf0": "#161b22",
    "#9be9a8": "#0b5d2a",
    "#40c463": "#0f8f3f",
    "#30a14e": "#19c552",
    "#216e39": "#39ff88",
    "#0e4429": "#0b5d2a",
    "#006d32": "#0f8f3f",
    "#26a641": "#19c552",
    "#39d353": "#39ff88",
}

PADDLE_COLOR = "#ff2bd6"
BALL_COLORS = "#00f0ff;#ff2bd6;#39ff14;#fff200;#ff7a00;#b266ff;#00f0ff"
BALL_DUR = "2.4s"

STYLE_ID = "neon-theme"
STYLE_CSS = (
    f'<style id="{STYLE_ID}">'
    'rect[id^="c-"]{stroke:#00e5ff;stroke-opacity:.3;stroke-width:1}'
    "</style>"
)
DEFS = (
    '<defs><filter id="neon-glow" x="-150%" y="-150%" width="400%" height="400%">'
    '<feGaussianBlur stdDeviation="2" result="b"/>'
    '<feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>'
    "</filter></defs>"
)

SVG_OPEN_RE = re.compile(r"<svg\b[^>]*>", re.S)
HEX_RE = re.compile(r"#[0-9a-fA-F]{6}\b")
RECT_RE = re.compile(r"<rect\b[^>]*?/>|<rect\b[^>]*?>.*?</rect>", re.S)
CIRCLE_RE = re.compile(r"<circle\b[^>]*?/>|<circle\b[^>]*?>.*?</circle>", re.S)
ATTR_RE = re.compile(r'([\w:.-]+)\s*=\s*(?:"([^"]*)"|\'([^\']*)\')')
PROTECTED = ("defs", "clipPath", "mask", "pattern")


def attrs(tag):
    return {m.group(1): m.group(2) if m.group(2) is not None else m.group(3)
            for m in ATTR_RE.finditer(tag)}


def num(v):
    if v is None:
        return None
    m = re.match(r"^\s*(-?\d+(?:\.\d+)?)\s*(px)?\s*$", v)
    return float(m.group(1)) if m else None


def open_tag_of(element):
    return re.match(r"<\w+\b[^>]*>", element, re.S).group(0)


def set_attr(tag, name, value):
    pat = re.compile(rf'(\s){name}\s*=\s*"[^"]*"')
    if pat.search(tag):
        return pat.sub(rf'\1{name}="{value}"', tag, count=1)
    end = "/>" if tag.endswith("/>") else ">"
    return tag[: -len(end)] + f' {name}="{value}"' + end


def add_style(tag, decl):
    m = re.search(r'(\s)style\s*=\s*"([^"]*)"', tag)
    if m:
        merged = m.group(2).rstrip("; ") + ";" + decl
        return tag[: m.start()] + f' style="{merged}"' + tag[m.end():]
    return set_attr(tag, "style", decl)


def protected_spans(text):
    spans = []
    for name in PROTECTED:
        for m in re.finditer(rf"<{name}\b.*?</{name}>", text, re.S):
            spans.append((m.start(), m.end()))
    return spans


def in_spans(pos, spans):
    return any(s <= pos < e for s, e in spans)


def luminance(hex_color):
    r, g, b = (int(hex_color[i:i + 2], 16) for i in (1, 3, 5))
    return (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255


def remap_colors(text):
    return HEX_RE.sub(lambda m: COLOR_MAP.get(m.group(0).lower(), m.group(0)), text)


def neon_paddle(text):
    spans = protected_spans(text)
    count = 0
    out, last = [], 0
    for r in RECT_RE.finditer(text):
        if in_spans(r.start(), spans):
            continue
        tag = open_tag_of(r.group(0))
        a = attrs(tag)
        if a.get("id", "").startswith("c-") or "neon-glow" in tag:
            continue
        w, h = num(a.get("width")), num(a.get("height"))
        if not w or not h or w < h * 4 or h > 20:
            continue
        new_tag = set_attr(tag, "fill", PADDLE_COLOR)
        new_tag = add_style(new_tag, f"fill:{PADDLE_COLOR}")
        new_tag = set_attr(new_tag, "filter", "url(#neon-glow)")
        out.append(text[last:r.start()])
        out.append(r.group(0).replace(tag, new_tag, 1))
        last = r.end()
        count += 1
    out.append(text[last:])
    return "".join(out), count


def neon_ball(text):
    spans = protected_spans(text)
    anim = (
        '<animate attributeName="fill" values="%s" dur="%s" '
        'repeatCount="indefinite" calcMode="discrete"/>' % (BALL_COLORS, BALL_DUR)
    )
    count = 0
    out, last = [], 0
    for c in CIRCLE_RE.finditer(text):
        if in_spans(c.start(), spans):
            continue
        tag = open_tag_of(c.group(0))
        r = num(attrs(tag).get("r"))
        if r is None or r > 8 or "data-neon" in tag:
            continue
        new_tag = set_attr(tag, "data-neon", "ball")
        if "filter=" not in new_tag:
            new_tag = set_attr(new_tag, "filter", "url(#neon-glow)")
        if tag.endswith("/>"):
            new_el = new_tag[:-2].rstrip() + ">" + anim + "</circle>"
        else:
            new_el = new_tag + anim + c.group(0)[len(tag):]
        out.append(text[last:c.start()])
        out.append(new_el)
        last = c.end()
        count += 1
    out.append(text[last:])
    return "".join(out), count


def process(path):
    with open(path, encoding="utf-8") as f:
        text = f.read()

    text = remap_colors(text)
    is_breakout = "breakout" in path.lower()
    paddles = balls = 0

    m = SVG_OPEN_RE.search(text)
    if not m:
        sys.exit(f"SVG root tidak ditemukan: {path}")
    inject = ""
    if STYLE_ID not in text:
        inject += STYLE_CSS
    if is_breakout and 'id="neon-glow"' not in text:
        inject += DEFS
    text = text[: m.end()] + inject + text[m.end():]

    if is_breakout:
        text, paddles = neon_paddle(text)
        text, balls = neon_ball(text)

    ET.fromstring(text.encode("utf-8"))  # validasi
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)

    cells = re.findall(r'<rect\b[^>]*\bid="c-[^"]*"[^>]*>', text)
    fills = sorted({attrs(c).get("fill") for c in cells if attrs(c).get("fill")})
    light = [x for x in fills if re.fullmatch(r"#[0-9a-fA-F]{6}", x) and luminance(x) > 0.75]
    print(f"{path}: sel={len(cells)} paddle={paddles} bola={balls}")
    print(f"   fill sel: {', '.join(fills) or '-'}")
    if light:
        print(f"   PERINGATAN: masih ada warna terang pada sel: {', '.join(light)}")
    if not cells:
        print("   PERINGATAN: tidak ada rect id='c-*' (selector stroke tidak kena)")
    if is_breakout and not (paddles and balls):
        print("   PERINGATAN: paddle/bola Breakout tidak terdeteksi")


def main():
    files = sys.argv[1:]
    if not files:
        sys.exit(__doc__)
    for p in files:
        process(p)


if __name__ == "__main__":
    main()
