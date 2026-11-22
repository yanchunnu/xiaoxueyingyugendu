#!/usr/bin/env python3
"""Render one A4 topic page for the listen-and-repeat book.

Layout
------
- Title and QR stay in the header (QR at the top-right).
- The word sidebar is a *narrow column on the far right*, directly under the QR,
  words stacked top-to-bottom (English then Korean meaning).
- The passage occupies the left: each English sentence with its Korean
  translation directly underneath.

Type is auto-fitted with a binary search: the largest scale that still fits
on a single A4 page is chosen. This is meant to be reused for all 100 topics.

Usage:
    python3 make_page_pdf.py
    python3 make_page_pdf.py path/to/topic.json -o out.pdf --png out.png --qr qr.png
"""

from __future__ import annotations

import argparse
import json
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path

import fitz
from fontTools.subset import Options, Subsetter
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont

ROOT = Path(__file__).resolve().parents[1]
FONT_DIR = ROOT / "fonts"
NUNITO_REG = FONT_DIR / "Nunito-Regular.ttf"
NUNITO_MED = FONT_DIR / "Nunito-Medium.ttf"
NUNITO_SB = FONT_DIR / "Nunito-SemiBold.ttf"
VARELA = FONT_DIR / "VarelaRound-Regular.ttf"
NOTO_URL = "https://github.com/google/fonts/raw/main/ofl/notosanskr/NotoSansKR%5Bwght%5D.ttf"


def korean_variable_font() -> Path:
    """Noto Sans KR variable font (TrueType). Downloaded once if it is not cached."""
    candidates = [
        FONT_DIR / "NotoSansKR-var.ttf",
        ROOT / "build" / "fonts" / "NotoSansKR-var.ttf",
        Path(tempfile.gettempdir()) / "notokr" / "NotoSansKR-VF.ttf",
    ]
    for path in candidates:
        if path.is_file() and path.stat().st_size > 1_000_000:
            return path
    dest = ROOT / "build" / "fonts" / "NotoSansKR-var.ttf"
    dest.parent.mkdir(parents=True, exist_ok=True)
    import urllib.request
    print("Downloading Noto Sans KR…")
    urllib.request.urlretrieve(NOTO_URL, dest)
    return dest


KR_VF = korean_variable_font()

# Colors (0-1 RGB), matching the existing book, with a darker Korean body color
CREAM = (1.0, 0.972549, 0.941176)
TEAL = (0.121569, 0.541176, 0.490196)
NAVY = (29 / 255, 53 / 255, 87 / 255)
KO_UI = (45 / 255, 85 / 255, 110 / 255)       # category / small UI
KO_BODY = (32 / 255, 52 / 255, 74 / 255)      # translations: darker, easier to read
BODY = (36 / 255, 48 / 255, 68 / 255)
CORAL = (231 / 255, 111 / 255, 81 / 255)
MINT = (0.956863, 0.984314, 0.980392)
CARD_STROKE = (0.901961, 0.866667, 0.823529)
MUTED = (110 / 255, 130 / 255, 150 / 255)
WHITE = (1, 1, 1)

A4 = fitz.paper_rect("a4")  # 595.28 x 841.89

# Geometry shared with the original book header
RIGHT_EDGE = 569.2756
QR_CARD = fitz.Rect(491.2756, 22, 569.2756, 112)
QR_IMAGE = fitz.Rect(495.2756, 26, 565.2756, 96)
LEFT_MARGIN = 34
FOOTER_Y = 812
CONTENT_TOP = 118  # just below the QR card
SIDEBAR_GAP = 12
SIDEBAR_MIN_W = 126
SIDEBAR_MAX_W = 168


def subset_korean_font(text: str, weight: int, dest_name: str) -> Path:
    """Instantiate Noto Sans KR at `weight` and subset to the glyphs we use."""
    tmp = Path(tempfile.gettempdir()) / "notokr"
    tmp.mkdir(parents=True, exist_ok=True)
    regular = tmp / f"w{weight}.ttf"
    if not regular.exists() or regular.stat().st_size < 1000:
        inst = instantiateVariableFont(TTFont(str(KR_VF)), {"wght": weight})
        inst.save(str(regular))
    dest = tmp / dest_name
    font = TTFont(str(regular))
    opt = Options()
    opt.layout_features = ["*"]
    opt.notdef_outline = True
    opt.recommended_glyphs = True
    ss = Subsetter(options=opt)
    ss.populate(
        text=text
        + " 0123456789·.,?!'’()/—–-ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
    )
    ss.subset(font)
    font.save(str(dest))
    return dest


def split_highlights(text: str, highlights: list[str] | None) -> list[tuple[str, bool]]:
    if not highlights:
        return [(text, False)]
    terms = sorted({h for h in highlights if h}, key=len, reverse=True)
    if not terms:
        return [(text, False)]
    pattern = re.compile(
        r"(?<![A-Za-z])(" + "|".join(re.escape(t) for t in terms) + r")(?![A-Za-z])",
        re.IGNORECASE,
    )
    parts: list[tuple[str, bool]] = []
    last = 0
    for m in pattern.finditer(text):
        if m.start() > last:
            parts.append((text[last : m.start()], False))
        parts.append((m.group(0), True))
        last = m.end()
    if last < len(text):
        parts.append((text[last:], False))
    return parts or [(text, False)]


def write_text(page, pos, text, font, fontsize, color):
    tw = fitz.TextWriter(page.rect)
    tw.append(pos, text, font=font, fontsize=fontsize)
    tw.write_text(page, color=color)
    return font.text_length(text, fontsize=fontsize)


def _fits(font: fitz.Font, text: str, size: float, max_w: float) -> bool:
    return font.text_length(text, fontsize=size) <= max_w


def wrap_text(text: str, font: fitz.Font, size: float, max_w: float) -> list[str]:
    """Wrap `text` to `max_w`.

    Prefers a natural break (comma) and avoids a last line of one short word,
    which looks especially poor in a children's textbook.
    """
    if max_w <= 0:
        return [text]
    if _fits(font, text, size, max_w):
        return [text]

    words = text.split()
    if not words:
        return [text]

    def pack(seq: list[str]) -> list[str]:
        """Greedy wrap of a token list."""
        out: list[str] = []
        cur = seq[0]
        for w in seq[1:]:
            trial = f"{cur} {w}"
            if _fits(font, trial, size, max_w):
                cur = trial
            else:
                out.append(cur)
                cur = w
        out.append(cur)
        return out

    # 1) Prefer a comma break when both sides fit on one line each.
    idx = text.rfind(", ")
    while idx != -1:
        left, right = text[: idx + 1], text[idx + 2 :]
        if left.strip() and right.strip() and _fits(font, left, size, max_w) and _fits(font, right, size, max_w):
            return [left, right]
        idx = text.rfind(", ", 0, idx)

    # 2) If the text fits in two lines, choose the most balanced break
    #    (no one-word orphans, first line slightly longer is fine).
    if len(words) >= 4:
        best: list[str] | None = None
        best_score = None
        for i in range(2, len(words) - 1):  # at least 2 words on each line
            left, right = " ".join(words[:i]), " ".join(words[i:])
            if _fits(font, left, size, max_w) and _fits(font, right, size, max_w):
                lw = font.text_length(left, fontsize=size)
                rw = font.text_length(right, fontsize=size)
                score = abs(lw - rw)
                if best is None or score < best_score:
                    best, best_score = [left, right], score
        if best is not None:
            return best

    # 3) Fall back to greedy wrap (3+ lines, or very short phrases).
    return pack(words)


def collect_korean(data: dict) -> str:
    parts = [
        data.get("topic_ko", ""),
        data.get("category_ko", ""),
        data.get("category_en", ""),
        "음원 듣기",
        "단어",
        "본문",
        "Listen and Repeat   ·   듣고 따라 말하기",
        "People",
    ]
    for w in data["words"]:
        parts.append(w["en"])
        parts.append(w["ko"])
    for p in data["phrases"]:
        parts.append(p["en"])
        parts.append(p["ko"])
    return "\n".join(parts)


@dataclass
class Scale:
    en: float
    ko: float
    word_en: float
    word_ko: float
    section: float
    bullet: float
    # Vertical rhythm, in points
    en_line: float      # line-to-line for wrapped English
    ko_gap: float       # en baseline → first ko baseline
    ko_line: float      # line-to-line for wrapped Korean
    after: float        # gap after a sentence block
    word_pad_x: float
    word_pad_y: float
    word_gap: float     # gap between EN and KO inside a word cell
    word_row_gap: float # gap between word cells


def make_scale(en: float) -> Scale:
    """Derive every type size and spacing from the English body size."""
    ko = en * 0.90  # Korean almost as large as English
    return Scale(
        en=en,
        ko=ko,
        word_en=max(10.0, en * 0.70),
        word_ko=max(9.5, en * 0.66),
        section=max(11.0, en * 0.70),
        bullet=max(2.3, en * 0.155),
        en_line=en * 1.28,
        ko_gap=en * 0.28 + ko * 0.92,  # room for underline + Korean ascent
        ko_line=ko * 1.28,
        after=en * 0.42,
        word_pad_x=5.5,
        word_pad_y=3.5,
        word_gap=1.6,
        word_row_gap=3.0,
    )


@dataclass
class Layout:
    scale: Scale
    sidebar: fitz.Rect
    pass_x0: float
    pass_x1: float
    text_x: float
    text_w: float
    header_h: float
    block_top: float
    # per-phrase: (en_lines, ko_lines, height)
    phrase_plan: list[tuple[list[str], list[str], float]]
    word_plan: list[tuple[float, float, float, float]]  # y0, y1, en_base, ko_base
    sidebar_inner_top: float
    passage_bottom: float
    fits: bool
    reason: str


def plan_layout(data: dict, scale: Scale, fonts: dict) -> Layout:
    nunito = fonts["nunito"]
    nunito_sb = fonts["nunito_sb"]
    kr = fonts["kr"]
    kr_med = fonts["kr_med"]

    words = data["words"]
    phrases = data["phrases"]
    sc = scale

    # Sidebar width: narrow, just enough for the longest stacked word at this size
    longest_w = max(
        nunito.text_length(w["en"], fontsize=sc.word_en) for w in words
    )
    longest_k = max(
        kr_med.text_length(w["ko"], fontsize=sc.word_ko) for w in words
    )
    # Must match the drawn insets: 5 pt row inset + word_pad_x on both sides, plus 1 pt slack.
    needed = max(longest_w, longest_k) + 5 * 2 + sc.word_pad_x * 2 + 1
    sidebar_w = min(SIDEBAR_MAX_W, max(SIDEBAR_MIN_W, needed))
    side = fitz.Rect(RIGHT_EDGE - sidebar_w, CONTENT_TOP, RIGHT_EDGE, FOOTER_Y - 8)

    pass_x0 = LEFT_MARGIN
    pass_x1 = side.x0 - SIDEBAR_GAP
    text_x = pass_x0 + 14
    text_w = pass_x1 - text_x

    # Section header ("Let's Read")
    header_h = sc.section * 1.55 + 4
    block_top = CONTENT_TOP + header_h

    # Compact word cells (EN + KO stacked). Do *not* stretch to the page height.
    section_w = nunito_sb.text_length("Words", fontsize=sc.section)
    # "Words" + gap + "단어" should fit; if not, shrink later via fits flag
    words_header_h = sc.section * 1.5 + 4
    y = side.y0 + words_header_h
    word_plan: list[tuple[float, float, float, float]] = []
    word_fits = True
    for w in words:
        cell_h = sc.word_pad_y + sc.word_en * 1.05 + sc.word_gap + sc.word_ko * 1.05 + sc.word_pad_y
        y0 = y
        y1 = y + cell_h
        en_base = y0 + sc.word_pad_y + sc.word_en * 0.85
        ko_base = en_base + sc.word_en * 0.20 + sc.word_gap + sc.word_ko * 0.85
        word_plan.append((y0, y1, en_base, ko_base))
        y = y1 + sc.word_row_gap
        if nunito.text_length(w["en"], fontsize=sc.word_en) > (sidebar_w - 12 - sc.word_pad_x * 2):
            word_fits = False
        if kr_med.text_length(w["ko"], fontsize=sc.word_ko) > (sidebar_w - 12 - sc.word_pad_x * 2):
            word_fits = False
    sidebar_bottom = y + 4
    if sidebar_bottom > side.y1:
        word_fits = False
    # Shrink the card to its compact height
    side.y1 = min(side.y1, max(sidebar_bottom, side.y0 + 80))

    # Passage: wrap if needed, measure each block
    phrase_plan: list[tuple[list[str], list[str], float]] = []
    y = block_top
    pass_fits = True
    if text_w < 80:
        pass_fits = False
    for p in phrases:
        en_lines = wrap_text(p["en"], nunito, sc.en, text_w)
        ko_lines = wrap_text(p["ko"], kr_med, sc.ko, text_w)
        # A single unbreakable token wider than the column is a fail
        if any(nunito.text_length(ln, fontsize=sc.en) > text_w + 0.4 for ln in en_lines):
            pass_fits = False
        if any(kr_med.text_length(ln, fontsize=sc.ko) > text_w + 0.4 for ln in ko_lines):
            pass_fits = False
        # height from top of block to bottom of last Korean descender + trailing gap
        h = sc.en_line * (len(en_lines) - 1) + sc.ko_gap + sc.ko_line * (len(ko_lines) - 1) + sc.ko * 0.28 + sc.after
        # plus the first English ascent area
        h += sc.en * 0.95
        phrase_plan.append((en_lines, ko_lines, h))
        y += h
    passage_bottom = y
    if passage_bottom > FOOTER_Y - 10:
        pass_fits = False

    fits = word_fits and pass_fits
    reason = ""
    if not word_fits:
        reason = "sidebar overflow"
    elif not pass_fits:
        reason = "passage overflow"
    return Layout(
        scale=sc,
        sidebar=side,
        pass_x0=pass_x0,
        pass_x1=pass_x1,
        text_x=text_x,
        text_w=text_w,
        header_h=header_h,
        block_top=block_top,
        phrase_plan=phrase_plan,
        word_plan=word_plan,
        sidebar_inner_top=side.y0 + words_header_h,
        passage_bottom=passage_bottom,
        fits=fits,
        reason=reason,
    )


def autofit(data: dict, fonts: dict, lo: float = 11.0, hi: float = 22.0) -> Layout:
    """Binary-search the largest English body size that still fits on one A4 page."""
    best: Layout | None = None
    # 18 iterations → ~0.004 pt precision over an 11-pt range
    for _ in range(18):
        mid = (lo + hi) / 2
        lay = plan_layout(data, make_scale(mid), fonts)
        if lay.fits:
            best = lay
            lo = mid
        else:
            hi = mid
    if best is None:
        # Fall back to the small end (should still be readable)
        best = plan_layout(data, make_scale(lo), fonts)
    return best


def draw_highlighted_line(page, x, baseline_y, text, highlights, font, fontsize, color, hl_color):
    cx = x
    ul = max(1.1, fontsize * 0.085)
    for part, is_hl in split_highlights(text, highlights):
        fill = hl_color if is_hl else color
        write_text(page, (cx, baseline_y), part, font, fontsize, fill)
        w = font.text_length(part, fontsize=fontsize)
        if is_hl and part.strip():
            y_ul = baseline_y + fontsize * 0.16
            page.draw_line((cx, y_ul), (cx + w, y_ul), color=hl_color, width=ul)
        cx += w
    return cx


def build(
    data: dict,
    pdf_path: Path,
    png_path: Path | None,
    qr_path: Path | None = None,
) -> Layout:
    FONT_DIR.mkdir(parents=True, exist_ok=True)
    corpus = collect_korean(data)
    kr_reg_path = subset_korean_font(corpus, 400, "NotoSansKR-Regular-subset.ttf")
    kr_med_path = subset_korean_font(corpus, 500, "NotoSansKR-Medium-subset.ttf")

    fonts = {
        "nunito": fitz.Font(fontfile=str(NUNITO_MED)),
        "nunito_reg": fitz.Font(fontfile=str(NUNITO_REG)),
        "nunito_sb": fitz.Font(fontfile=str(NUNITO_SB)),
        "varela": fitz.Font(fontfile=str(VARELA)),
        "kr": fitz.Font(fontfile=str(kr_reg_path)),
        "kr_med": fitz.Font(fontfile=str(kr_med_path)),
    }
    nunito = fonts["nunito"]
    nunito_reg = fonts["nunito_reg"]
    nunito_sb = fonts["nunito_sb"]
    varela = fonts["varela"]
    kr = fonts["kr"]
    kr_med = fonts["kr_med"]

    lay = autofit(data, fonts)
    sc = lay.scale
    print(
        f"Auto-fit: en={sc.en:.2f} ko={sc.ko:.2f} "
        f"word_en={sc.word_en:.2f} word_ko={sc.word_ko:.2f} "
        f"passage_bottom={lay.passage_bottom:.1f} footer={FOOTER_Y} "
        f"sidebar={lay.sidebar.width:.1f}x{lay.sidebar.height:.1f} "
        f"fits={lay.fits} {lay.reason}"
    )

    doc = fitz.open()
    page = doc.new_page(width=A4.width, height=A4.height)
    W, H = A4.width, A4.height

    page.draw_rect(A4, fill=CREAM, color=CREAM, width=0)
    page.draw_rect(fitz.Rect(0, 0, W, 12), fill=TEAL, color=TEAL, width=0)

    # Number badge + title (same positions as the original book)
    badge = fitz.Rect(34, 32, 66, 64)
    page.draw_rect(badge, fill=TEAL, color=TEAL, width=0, radius=0.5)
    num = str(data.get("topic_number", 1))
    nw = nunito_sb.text_length(num, fontsize=12)
    write_text(page, ((badge.x0 + badge.x1) / 2 - nw / 2, 54.2), num, nunito_sb, 12, WHITE)

    cat_ko = data.get("category_ko", "")
    cat_en = data.get("category_en", "")
    cat = f"{cat_ko}   ·   {cat_en}" if cat_ko or cat_en else ""
    if cat:
        write_text(page, (78, 34.2), cat, kr, 8, TEAL)
    write_text(page, (78, 55.5), data["topic"], varela, 20, NAVY)
    write_text(page, (78, 73.2), data.get("topic_ko", ""), kr, 11, KO_BODY)

    # QR card (top-right) with 음원 듣기 label
    page.draw_rect(QR_CARD, fill=WHITE, color=WHITE, width=0, radius=0.12)
    if qr_path and Path(qr_path).exists():
        page.insert_image(QR_IMAGE, filename=str(qr_path), keep_proportion=True)
    label = "음원 듣기"
    lw = kr.text_length(label, fontsize=8)
    write_text(page, ((QR_CARD.x0 + QR_CARD.x1) / 2 - lw / 2, 107.2), label, kr, 8, NAVY)

    # ----- Right-edge word sidebar, under the QR, compact rows -----
    side = lay.sidebar
    page.draw_rect(side, fill=WHITE, color=CARD_STROKE, width=0.6, radius=0.04)
    write_text(page, (side.x0 + 8, side.y0 + sc.section * 1.15), "Words", nunito_sb, sc.section, TEAL)
    ww = nunito_sb.text_length("Words", fontsize=sc.section)
    write_text(
        page,
        (side.x0 + 8 + ww + 5, side.y0 + sc.section * 1.12),
        "단어",
        kr_med,
        sc.section * 0.88,
        KO_BODY,
    )

    for i, ((y0, y1, en_base, ko_base), w) in enumerate(zip(lay.word_plan, data["words"])):
        row = fitz.Rect(side.x0 + 5, y0, side.x1 - 5, y1)
        # alternate mint / white, tight to the text, little empty padding
        if i % 2 == 0:
            page.draw_rect(row, fill=MINT, color=MINT, width=0, radius=0.12)
        write_text(page, (row.x0 + sc.word_pad_x, en_base), w["en"], nunito_sb, sc.word_en, NAVY)
        write_text(page, (row.x0 + sc.word_pad_x, ko_base), w["ko"], kr_med, sc.word_ko, KO_BODY)

    # ----- Left passage -----
    write_text(page, (lay.pass_x0, CONTENT_TOP + sc.section * 1.05), "Let's Read", nunito_sb, sc.section, TEAL)
    lr_w = nunito_sb.text_length("Let's Read", fontsize=sc.section)
    write_text(
        page,
        (lay.pass_x0 + lr_w + 7, CONTENT_TOP + sc.section * 1.02),
        "본문",
        kr_med,
        sc.section * 0.88,
        KO_BODY,
    )

    y = lay.block_top
    for p, (en_lines, ko_lines, h) in zip(data["phrases"], lay.phrase_plan):
        # first English baseline
        en0 = y + sc.en * 0.85
        page.draw_circle(
            (lay.pass_x0 + sc.bullet + 0.4, en0 - sc.en * 0.28),
            sc.bullet,
            fill=TEAL,
            color=TEAL,
            width=0,
        )
        for i, line in enumerate(en_lines):
            draw_highlighted_line(
                page,
                lay.text_x,
                en0 + i * sc.en_line,
                line,
                p.get("highlights") or [],
                nunito,
                sc.en,
                BODY,
                CORAL,
            )
        ko0 = en0 + (len(en_lines) - 1) * sc.en_line + sc.ko_gap
        for i, line in enumerate(ko_lines):
            write_text(page, (lay.text_x, ko0 + i * sc.ko_line), line, kr_med, sc.ko, KO_BODY)
        y += h

    footer = "Listen and Repeat   ·   듣고 따라 말하기"
    write_text(page, (LEFT_MARGIN, 818.5), footer, kr, 8, MUTED)
    total = data.get("topic_total", 100)
    pn = f"{data.get('topic_number', 1)} / {total}"
    pw = nunito_reg.text_length(pn, fontsize=8)
    write_text(page, (RIGHT_EDGE - pw, 818.2), pn, nunito_reg, 8, MUTED)

    try:
        doc.subset_fonts()
    except Exception as exc:
        print("subset_fonts failed:", exc)
        try:
            doc.subset_fonts(fallback=True)
        except Exception as exc2:
            print("subset_fonts fallback failed:", exc2)
    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(pdf_path), deflate=True, garbage=4)
    doc.close()

    if png_path is not None:
        doc = fitz.open(str(pdf_path))
        pix = doc[0].get_pixmap(matrix=fitz.Matrix(150 / 72, 150 / 72), alpha=False)
        png_path.parent.mkdir(parents=True, exist_ok=True)
        pix.save(str(png_path))
        doc.close()
    print(f"Wrote {pdf_path} ({pdf_path.stat().st_size} bytes)")
    return lay


def main() -> int:
    parser = argparse.ArgumentParser(description="Render one A4 listen-and-repeat topic page.")
    parser.add_argument("content", nargs="?", type=Path, default=ROOT / "about_me_long.json")
    parser.add_argument("-o", "--pdf", type=Path, default=None)
    parser.add_argument("--png", type=Path, default=None)
    parser.add_argument("--qr", type=Path, default=ROOT / "qr_001_about_me.png")
    args = parser.parse_args()
    content = args.content.expanduser().resolve()
    data = json.loads(content.read_text(encoding="utf-8"))
    outdir = content.parent
    slug = data.get("slug") or content.stem
    pdf_path = (args.pdf or outdir / f"{slug}.pdf").expanduser().resolve()
    png_path = (args.png or outdir / f"{slug}_page.png").expanduser().resolve()
    build(data, pdf_path, png_path, args.qr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
