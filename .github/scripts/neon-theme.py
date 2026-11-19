#!/usr/bin/env python3
"""
neon-theme.py  -  transparan + neon untuk SVG Pac-Man & Breakout.

Simpan di: .github/scripts/neon-theme.py

Pakai:
  python3 .github/scripts/neon-theme.py                 # cari otomatis (*pacman*.svg, *breakout*.svg)
  python3 .github/scripts/neon-theme.py dist output     # cari hanya di folder tertentu
  python3 .github/scripts/neon-theme.py --no-recolor    # tanpa ganti warna (hanya transparan + glow)

Yang dilakukan per file:
  1. Hapus SEMUA elemen latar penuh (rect seukuran canvas / bernama bg/background)
  2. Hapus deklarasi `background` (CSS, atribut style, <style>)
  3. Set root <svg> menjadi background transparent
  4. Bungkus seluruh isi dalam <g filter="url(#neon-glow)"> (glow bekerja apa pun struktur SVG-nya)
  5. Ganti palet hijau GitHub -> neon (opsional)
  6. Verifikasi; exit code 1 bila masih ada masalah (workflow akan gagal, bukan diam-diam salah)

Snake dan SVG lain TIDAK disentuh (hanya nama file yang mengandung pacman / breakout).
"""
import os
import re
import sys
import xml.etree.ElementTree as ET

PATTERNS = ("pacman", "breakout")
SKIP_DIRS = {".git", "node_modules", ".github"}

NEON_DEFS = (
    '<defs><filter id="neon-glow" x="-25%" y="-25%" width="150%" height="150%" '
    'color-interpolation-filters="sRGB">'
    '<feGaussianBlur in="SourceGraphic" stdDeviation="2.2" result="b1"/>'
    '<feGaussianBlur in="SourceGraphic" stdDeviation="5" result="b2"/>'
    '<feMerge><feMergeNode in="b2"/><feMergeNode in="b1"/>'
    '<feMergeNode in="SourceGraphic"/></feMerge></filter></defs>'
)

# palet GitHub (terang & gelap) -> neon
RECOLOR = {
    # sel kosong
    "ebedf0": "1b2333", "161b22": "1b2333",
    # tema terang
    "9be9a8": "00a878", "40c463": "00d9a3", "30a14e": "00ffc3", "216e39": "7dffe8",
    # tema gelap
    "0e4429": "00a878", "006d32": "00d9a3", "26a641": "00ffc3", "39d353": "7dffe8",
    # teks gelap -> terang (agar terbaca di latar gelap)
    "24292f": "c9d1d9", "1f2328": "c9d1d9", "57606a": "8b949e",
}

WHITE_RE = r"(?:white|#fff(?:fff)?|rgb\(\s*255\s*,\s*255\s*,\s*255\s*\))"


COLOR_RE = (r"(#[0-9a-fA-F]{6}\b|#[0-9a-fA-F]{3}\b|rgba?\([^)]*\)|"
            r"\b(?:white|black|whitesmoke|gainsboro|lightgr[ae]y|snow|ghostwhite)\b)")
EMPTY_CELL = "#1b2333"     # sel kosong (gelap, kelihatan halus di latar GitHub dark)
NEON_PADDLE = "#00ffe0"    # paddle & bola Breakout (aslinya hitam -> tak terlihat)
NAMED = {
    "white": (255, 255, 255), "black": (0, 0, 0), "whitesmoke": (245, 245, 245),
    "gainsboro": (220, 220, 220), "lightgray": (211, 211, 211), "lightgrey": (211, 211, 211),
    "snow": (255, 250, 250), "ghostwhite": (248, 248, 255),
}
FILL_PREFIX = r"(\bfill\s*(?:=\s*\"|:\s*))"


def to_rgb(tok):
    t = tok.strip().lower()
    if t in NAMED:
        return NAMED[t]
    if t.startswith("#"):
        h = t[1:]
        if len(h) == 3:
            h = "".join(c * 2 for c in h)
        return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))
    nums = re.findall(r"\d+(?:\.\d+)?", t)
    if len(nums) >= 3:
        return tuple(int(float(n)) for n in nums[:3])
    return None


def light_neutral(rgb):
    lum = (0.2126 * rgb[0] + 0.7152 * rgb[1] + 0.0722 * rgb[2]) / 255.0
    return lum > 0.80 and (max(rgb) - min(rgb)) <= 30


def pure_black(rgb):
    return max(rgb) <= 12


def fix_color(tok, breakout):
    rgb = to_rgb(tok)
    if rgb is None:
        return tok
    if light_neutral(rgb):
        return EMPTY_CELL
    if breakout and pure_black(rgb):
        return NEON_PADDLE
    return tok


def fix_styles(inner, breakout):
    """Ubah fill terang/hitam di blok <style> dan CSS variable (--warna: ...)."""
    def rule(m):
        sel, body = m.group(1), m.group(2)
        skip_sel = re.search(r"eye|ghost|pupil", sel, re.I)

        def decl(mm):
            prop = mm.group(1)
            if skip_sel or re.search(r"eye|ghost|pupil", prop, re.I):
                return mm.group(0)
            return prop + fix_color(mm.group(2), breakout)

        body = re.sub(r"((?:\bfill|--[\w-]+)\s*:\s*)" + COLOR_RE, decl, body)
        return sel + "{" + body + "}"

    def block(sm):
        return re.sub(r"([^{}]+)\{([^{}]*)\}", rule, sm.group(0))

    return re.sub(r"<style\b[^>]*>.*?</style>", block, inner, flags=re.S | re.I)


def fix_shape_tags(inner, breakout):
    """Sel (rect) terang -> gelap. Breakout: elemen hitam / tanpa fill -> neon."""
    def rect(m):
        tag = m.group(0)
        return re.sub(FILL_PREFIX + COLOR_RE,
                      lambda mm: mm.group(1) + fix_color(mm.group(2), breakout), tag)

    inner = re.sub(r"<rect\b[^>]*>", rect, inner)

    if breakout:
        def black_only(m):
            tag = m.group(0)

            def sub(mm):
                rgb = to_rgb(mm.group(2))
                return mm.group(1) + (NEON_PADDLE if rgb and pure_black(rgb) else mm.group(2))

            tag = re.sub(FILL_PREFIX + COLOR_RE, sub, tag)
            # tanpa fill/class/style sama sekali => default SVG = hitam
            if not re.search(r"\b(fill|class|style)\s*=", tag):
                tag = re.sub(r"<(\w+)", r'<\1 fill="' + NEON_PADDLE + '"', tag, count=1)
            return tag

        inner = re.sub(r"<(?:circle|ellipse|path)\b[^>]*>", black_only, inner)
        inner = re.sub(r"<rect\b(?![^>]*\b(?:fill|class|style)\s*=)[^>]*>", black_only, inner)
    return inner


def to_num(value, ref):
    if value is None:
        return None
    m = re.fullmatch(r"\s*(-?\d+(?:\.\d+)?)\s*(%|px)?\s*", value)
    if not m:
        return None
    n = float(m.group(1))
    return n / 100.0 * ref if m.group(2) == "%" else n


def parse_attrs(tag):
    return {k: v for k, v in re.findall(r'([\w:-]+)\s*=\s*"([^"]*)"', tag)}


def canvas_size(root_tag):
    attrs = parse_attrs(root_tag)
    vb = attrs.get("viewBox") or attrs.get("viewbox")
    if vb:
        parts = [float(p) for p in re.split(r"[\s,]+", vb.strip()) if p]
        if len(parts) == 4:
            return parts[2], parts[3]
    w = to_num(attrs.get("width"), 0)
    h = to_num(attrs.get("height"), 0)
    return (w or 0), (h or 0)


def is_background_rect(tag, W, H):
    attrs = parse_attrs(tag)
    name = " ".join([attrs.get("class", ""), attrs.get("id", "")]).lower()
    if re.search(r"(^|[\s_-])(bg|background)($|[\s_-])", name):
        return True
    if W <= 0 or H <= 0:
        return False
    x = to_num(attrs.get("x", "0"), W) or 0
    y = to_num(attrs.get("y", "0"), H) or 0
    w = to_num(attrs.get("width"), W)
    h = to_num(attrs.get("height"), H)
    if w is None or h is None:
        return False
    return abs(x) <= 2 and abs(y) <= 2 and w >= W * 0.95 and h >= H * 0.95


def process(text, recolor, breakout=False):
    m = re.search(r"<svg\b[^>]*>", text)
    end = text.rfind("</svg>")
    if not m or end == -1:
        raise ValueError("bukan SVG valid (tag <svg> / </svg> tidak ketemu)")

    root_tag = m.group(0)
    W, H = canvas_size(root_tag)

    # 1) hapus rect latar penuh
    def drop_rect(mm):
        return "" if is_background_rect(mm.group(0), W, H) else mm.group(0)

    inner = text[m.end():end]
    inner = re.sub(r"<rect\b[^>]*?(?:/>|>\s*</rect>)", drop_rect, inner)

    # 2) hapus deklarasi background di mana pun (CSS, style="", <style>)
    inner = re.sub(r"background(?:-color)?\s*:\s*[^;\"'}]+;?", "", inner)
    root_tag = re.sub(r"background(?:-color)?\s*:\s*[^;\"'}]+;?", "", root_tag)

    # 3) root transparan
    if re.search(r'\bstyle\s*=\s*"', root_tag):
        root_tag = re.sub(r'\bstyle\s*=\s*"', 'style="background:transparent;', root_tag, count=1)
    else:
        root_tag = root_tag[:-1] + ' style="background:transparent">'

    # 4b) sel putih/terang -> gelap (berdasar kecerahan, bukan hex tertentu)
    inner = fix_styles(inner, breakout)
    inner = fix_shape_tags(inner, breakout)

    # 5) recolor palet
    if recolor:
        def repl(mm):
            key = mm.group(1).lower()
            if len(key) == 3:
                key = "".join(c * 2 for c in key)
            return "#" + RECOLOR.get(key, mm.group(1))
        inner = re.sub(r"(?<!url\()#([0-9a-fA-F]{6}|[0-9a-fA-F]{3})\b", repl, inner)

    # 4) glow (idempotent)
    if 'id="neon-layer"' not in inner:
        inner = NEON_DEFS + '<g id="neon-layer" filter="url(#neon-glow)">' + inner + "</g>"

    return text[:m.start()] + root_tag + inner + text[end:]


def verify(path):
    problems = []
    with open(path, encoding="utf-8") as f:
        text = f.read()
    m = re.search(r"<svg\b[^>]*>", text)
    if not m:
        return ["tag <svg> hilang"]
    W, H = canvas_size(m.group(0))
    for r in re.findall(r"<rect\b[^>]*?(?:/>|>\s*</rect>)", text):
        if is_background_rect(r, W, H):
            problems.append("masih ada rect latar penuh: " + r[:120])
    for r in re.findall(r"<rect\b[^>]*>", text):
        for mm in re.finditer(FILL_PREFIX + COLOR_RE, r):
            rgb = to_rgb(mm.group(2))
            if rgb and light_neutral(rgb):
                problems.append("masih ada sel terang: " + r[:120])
    if re.search(r"background(?:-color)?\s*:\s*(?!transparent)[^;\"'}]+", text):
        problems.append("masih ada deklarasi background non-transparent")
    if re.search(r"background(?:-color)?\s*:\s*" + WHITE_RE, text, re.I):
        problems.append("masih ada background putih")
    if 'id="neon-glow"' not in text or 'id="neon-layer"' not in text:
        problems.append("filter neon tidak terpasang")
    try:
        ET.fromstring(text.encode("utf-8"))
    except ET.ParseError as e:
        problems.append("XML tidak valid: %s" % e)
    return problems


def find_files(roots):
    found = []
    for root in roots:
        if os.path.isfile(root):
            found.append(root)
            continue
        for dp, dn, fn in os.walk(root):
            dn[:] = [d for d in dn if d not in SKIP_DIRS]
            for name in fn:
                low = name.lower()
                if low.endswith(".svg") and any(p in low for p in PATTERNS):
                    found.append(os.path.join(dp, name))
    return sorted(set(found))


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    recolor = "--no-recolor" not in sys.argv
    files = find_files(args or ["."])
    if not files:
        print("ERROR: tidak ada SVG pacman/breakout ditemukan. Jalankan step ini SETELAH step generate.")
        sys.exit(1)

    failed = False
    for path in files:
        with open(path, encoding="utf-8") as f:
            original = f.read()
        try:
            result = process(original, recolor, "breakout" in os.path.basename(path).lower())
        except ValueError as e:
            print("GAGAL  %s -> %s" % (path, e))
            failed = True
            continue
        with open(path, "w", encoding="utf-8") as f:
            f.write(result)
        problems = verify(path)
        if problems:
            failed = True
            print("GAGAL  %s" % path)
            for p in problems:
                print("   - " + p)
            print("   head:", result[:600].replace("\n", " "))
        else:
            print("OK     %s (%d -> %d bytes)" % (path, len(original), len(result)))
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
