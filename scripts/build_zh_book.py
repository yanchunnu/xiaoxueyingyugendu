#!/usr/bin/env python3
"""Build the Chinese edition of the listen-and-repeat book.

One A4 page per topic: Chinese sentences on the left (pinyin above, Korean
under), words stacked in a far-right column (Chinese, pinyin, Korean).
Type is auto-fitted to the largest size that still fits on that single page.

QR codes open the player in Chinese:
    https://yanchunnu.github.io/xiaoxueyingyugendu/player.html?t=NNN&lang=zh
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

import fitz
import qrcode
from fontTools.subset import Options, Subsetter
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont

sys.path.insert(0, str(Path(__file__).resolve().parent))

from contentlib import CONTENT, ROOT  # noqa: E402
from make_page_pdf import (  # noqa: E402
    CREAM,
    CORAL,
    FONT_DIR,
    KO_BODY,
    KO_UI,
    LEFT_MARGIN,
    MINT,
    MUTED,
    NAVY,
    TEAL,
    WHITE,
    BODY,
    CARD_STROKE,
    subset_korean_font,
    wrap_text,
)

PAGES = "https://yanchunnu.github.io/xiaoxueyingyugendu/player.html?t="
SC_URL = "https://github.com/google/fonts/raw/main/ofl/notosanssc/NotoSansSC%5Bwght%5D.ttf"
PINYIN_URL = "https://github.com/notofonts/notofonts.github.io/raw/main/fonts/NotoSans/full/ttf/NotoSans-Medium.ttf"
PDF_DIR = ROOT / "pdf" / "zh"
TOPIC_DIR = PDF_DIR / "topics"
QR_DIR = ROOT / "qr" / "zh"
A4 = fitz.paper_rect("a4")
RIGHT_EDGE = 569.2756
QR_CARD = fitz.Rect(491.2756, 22, 569.2756, 112)
QR_IMAGE = fitz.Rect(495.2756, 26, 565.2756, 96)
CONTENT_TOP = 118
FOOTER_Y = 812
SIDEBAR_GAP = 12

PY_COLOR = (138 / 255, 90 / 255, 68 / 255)

SECTION_ZH = {
    "인물 묘사": "人物",
    "장소·풍경 묘사": "地方和风景",
    "개인 물건": "我的东西",
    "취미·관심사": "爱好和兴趣",
    "학교생활": "学校生活",
    "일상생활": "日常生活",
    "건강과 음식": "健康和食物",
    "사계절": "四季",
}
SECTION_COLOR = {
    "인물 묘사": (0.122, 0.541, 0.490),
    "장소·풍경 묘사": (0.180, 0.608, 0.416),
    "개인 물건": (0.831, 0.416, 0.298),
    "취미·관심사": (0.722, 0.455, 0.165),
    "학교생활": (0.239, 0.435, 0.604),
    "일상생활": (0.427, 0.357, 0.816),
    "건강과 음식": (0.878, 0.541, 0.173),
    "사계절": (0.165, 0.561, 0.722),
}

_NO_START = set("，。！？、；：）」』》〉】〕,.!?;:)]}")


def pinyin_font() -> Path:
    """Noto Sans has the pinyin tone marks Nunito is missing (ǐ ǒ ü with tones)."""
    dest = ROOT / "build" / "fonts" / "NotoSans-Medium.ttf"
    if dest.is_file() and dest.stat().st_size > 100_000:
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    import urllib.request
    print("Downloading Noto Sans for pinyin…")
    urllib.request.urlretrieve(PINYIN_URL, dest)
    return dest


def sc_variable_font() -> Path:
    dest = ROOT / "build" / "fonts" / "NotoSansSC-VF.ttf"
    if dest.is_file() and dest.stat().st_size > 1_000_000:
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    import urllib.request
    print("Downloading Noto Sans SC…")
    urllib.request.urlretrieve(SC_URL, dest)
    return dest


def sc_static(weight: int) -> Path:
    tmp = Path(tempfile.gettempdir()) / "notosc"
    tmp.mkdir(parents=True, exist_ok=True)
    dest = tmp / f"sc-w{weight}.ttf"
    if dest.is_file() and dest.stat().st_size > 1_000_000:
        return dest
    inst = instantiateVariableFont(TTFont(str(sc_variable_font())), {"wght": weight})
    inst.save(str(dest))
    return dest


def subset_sc(text: str, weight: int, dest_name: str) -> Path:
    tmp = Path(tempfile.gettempdir()) / "notosc"
    tmp.mkdir(parents=True, exist_ok=True)
    dest = tmp / dest_name
    font = TTFont(str(sc_static(weight)))
    opt = Options()
    opt.layout_features = ["*"]
    opt.notdef_outline = True
    opt.recommended_glyphs = True
    subsetter = Subsetter(options=opt)
    subsetter.populate(text=text + " 0123456789·")
    subsetter.subset(font)
    font.save(str(dest))
    return dest


def cmap_chars(path: Path) -> set[int]:
    return set(TTFont(str(path)).getBestCmap())


def missing_glyphs(path: Path, text: str) -> str:
    cmap = cmap_chars(path)
    skip = set(" \n\t")
    return "".join(sorted({ch for ch in text if ch not in skip and ord(ch) not in cmap}))


def py_display(text: str) -> str:
    """Latin pinyin. Fullwidth punctuation is drawn as ASCII so Nunito can show it."""
    table = str.maketrans({
        "，": ",",
        "。": ".",
        "！": "!",
        "？": "?",
        "、": ",",
        "：": ":",
        "；": ";",
        "（": "(",
        "）": ")",
        "《": "",
        "》": "",
    })
    return " ".join(text.translate(table).split())


def wrap_units(text: str, font: fitz.Font, size: float, max_w: float) -> list[str]:
    if max_w <= 0:
        return [text]
    if font.text_length(text, fontsize=size) <= max_w:
        return [text]
    lines: list[str] = []
    cur = ""
    for ch in text:
        trial = cur + ch
        if not cur or font.text_length(trial, fontsize=size) <= max_w:
            cur = trial
            continue
        lines.append(cur)
        cur = ch
    if cur:
        lines.append(cur)
    fixed: list[str] = []
    for line in lines:
        if fixed and line and line[0] in _NO_START:
            fixed[-1] += line[0]
            line = line[1:]
        if line:
            fixed.append(line)
    return fixed or [text]


def wrap_ko(text: str, font: fitz.Font, size: float, max_w: float) -> list[str]:
    lines = wrap_text(text, font, size, max_w)
    out: list[str] = []
    for line in lines:
        if font.text_length(line, fontsize=size) <= max_w + 0.4:
            out.append(line)
        else:
            out.extend(wrap_units(line, font, size, max_w))
    return out or [text]


def write_text(page, pos, text, font, fontsize, color) -> float:
    if not text:
        return 0.0
    tw = fitz.TextWriter(page.rect)
    tw.append(pos, text, font=font, fontsize=fontsize)
    tw.write_text(page, color=color)
    return font.text_length(text, fontsize=fontsize)


@dataclass
class Scale:
    zh: float
    py: float
    ko: float
    word_zh: float
    word_py: float
    word_ko: float
    section: float
    bullet: float
    zh_step: float
    py_step: float
    ko_step: float
    gap_py_zh: float
    gap_zh_ko: float
    after: float
    pad_x: float
    pad_y: float
    row_gap: float


def make_scale(zh: float) -> Scale:
    py = zh * 0.62
    ko = zh * 0.78
    return Scale(
        zh=zh,
        py=py,
        ko=ko,
        word_zh=max(8.0, zh * 0.62),
        word_py=max(6.4, zh * 0.46),
        word_ko=max(7.2, zh * 0.52),
        section=max(9.0, zh * 0.62),
        bullet=max(1.8, zh * 0.13),
        zh_step=zh * 1.26,
        py_step=py * 1.18,
        ko_step=ko * 1.24,
        gap_py_zh=zh * 0.34,
        gap_zh_ko=zh * 0.30,
        after=max(3.2, zh * 0.26),
        pad_x=4.5,
        pad_y=2.6,
        row_gap=2.4,
    )


@dataclass
class Layout:
    scale: Scale
    sidebar: fitz.Rect
    text_x: float
    text_w: float
    pass_x0: float
    phrase_plan: list
    word_plan: list
    passage_bottom: float
    fits: bool
    reason: str


def _stack_h(n_lines: int, size: float, step: float) -> float:
    if n_lines <= 0:
        return 0.0
    return size * 0.82 + step * (n_lines - 1)


def plan_layout(data: dict, scale: Scale, fonts: dict) -> Layout:
    sc_font = fonts["sc"]
    nunito = fonts["nunito"]
    kr = fonts["kr"]
    sc = scale
    sidebar_w = 156
    side = fitz.Rect(RIGHT_EDGE - sidebar_w, CONTENT_TOP, RIGHT_EDGE, FOOTER_Y - 8)
    text_x = LEFT_MARGIN + 14
    text_w = side.x0 - SIDEBAR_GAP - text_x
    inner_w = sidebar_w - 10 - sc.pad_x * 2

    header_h = sc.section * 1.55 + 2
    block_top = CONTENT_TOP + header_h
    words_header_h = sc.section * 1.45 + 2
    y = side.y0 + words_header_h
    word_plan = []
    word_fits = text_w >= 90
    for word in data["words"]:
        zh_lines = wrap_units(word["zh"], sc_font, sc.word_zh, inner_w)
        py_lines = wrap_text(py_display(word.get("py") or ""), nunito, sc.word_py, inner_w)
        ko_lines = wrap_ko(word["ko"], kr, sc.word_ko, inner_w)
        zh_h = len(zh_lines) * sc.word_zh * 1.28
        py_h = len(py_lines) * sc.word_py * 1.48
        ko_h = len(ko_lines) * sc.word_ko * 1.30
        cell_h = sc.pad_y + zh_h + 3.2 + py_h + 3.2 + ko_h + sc.pad_y
        y0, y1 = y, y + cell_h
        word_plan.append({
            "y0": y0,
            "y1": y1,
            "zh": zh_lines,
            "py": py_lines,
            "ko": ko_lines,
        })
        y = y1 + sc.row_gap
        for line in zh_lines + py_lines + ko_lines:
            pass
        if any(sc_font.text_length(line, fontsize=sc.word_zh) > inner_w + 0.6 for line in zh_lines):
            word_fits = False
        if any(nunito.text_length(line, fontsize=sc.word_py) > inner_w + 0.6 for line in py_lines):
            word_fits = False
        if any(kr.text_length(line, fontsize=sc.word_ko) > inner_w + 0.6 for line in ko_lines):
            word_fits = False
    if y + 4 > side.y1:
        word_fits = False
    side.y1 = min(side.y1, max(y + 4, side.y0 + 70))

    phrase_plan = []
    y = block_top
    pass_fits = word_fits
    for phrase in data["phrases"]:
        py_lines = wrap_text(py_display(phrase.get("py") or ""), nunito, sc.py, text_w)
        zh_lines = wrap_units(phrase["zh"], sc_font, sc.zh, text_w)
        ko_lines = wrap_ko(phrase["ko"], kr, sc.ko, text_w)
        if any(nunito.text_length(line, fontsize=sc.py) > text_w + 0.5 for line in py_lines):
            pass_fits = False
        if any(sc_font.text_length(line, fontsize=sc.zh) > text_w + 0.5 for line in zh_lines):
            pass_fits = False
        if any(kr.text_length(line, fontsize=sc.ko) > text_w + 0.5 for line in ko_lines):
            pass_fits = False
        h = 1.0
        h += _stack_h(len(py_lines), sc.py, sc.py_step)
        h += sc.gap_py_zh
        h += _stack_h(len(zh_lines), sc.zh, sc.zh_step)
        h += sc.gap_zh_ko
        h += _stack_h(len(ko_lines), sc.ko, sc.ko_step)
        h += sc.ko * 0.22 + sc.after
        phrase_plan.append({"py": py_lines, "zh": zh_lines, "ko": ko_lines, "h": h})
        y += h
    if y > FOOTER_Y - 8:
        pass_fits = False
    reason = ""
    if not word_fits:
        reason = "sidebar"
    elif y > FOOTER_Y - 8:
        reason = "passage"
    return Layout(sc, side, text_x, text_w, LEFT_MARGIN, phrase_plan, word_plan, y, pass_fits, reason)


def autofit(data: dict, fonts: dict) -> Layout:
    lo, hi = 8.0, 19.0
    best = None
    for _ in range(16):
        mid = (lo + hi) / 2
        lay = plan_layout(data, make_scale(mid), fonts)
        if lay.fits:
            best = lay
            lo = mid
        else:
            hi = mid
    if best is None:
        best = plan_layout(data, make_scale(lo), fonts)
    return best


def player_url(number: int) -> str:
    return f"{PAGES}{number:03d}&lang=zh"


def make_qr(path: Path, url: str) -> None:
    code = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=10, border=2)
    code.add_data(url)
    code.make(fit=True)
    image = code.make_image(fill_color="#1D3557", back_color="white")
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path)


def verify_qr(path: Path, url: str) -> None:
    result = subprocess.run(["zbarimg", "-q", "--raw", str(path)], capture_output=True, text=True, check=False)
    got = result.stdout.strip()
    if got != url:
        raise SystemExit(f"QR mismatch {path.name}: {got!r} != {url!r}")


def load() -> tuple[dict, list[tuple[dict, dict]]]:
    manifest = json.loads((CONTENT / "manifest.json").read_text(encoding="utf-8"))
    paired = []
    for meta in manifest["topics"]:
        data = json.loads((ROOT / meta["file"]).read_text(encoding="utf-8"))
        data["topic_number"] = meta["number"]
        data["topic_total"] = 100
        data.setdefault("category_ko", meta["section_ko"])
        data["category_zh"] = SECTION_ZH[meta["section_ko"]]
        if not data.get("topic_zh") or not data["words"][0].get("zh") or not data["phrases"][0].get("py"):
            raise SystemExit(f"topic {meta['number']} is missing Chinese text")
        paired.append((meta, data))
    if len(paired) != 100:
        raise SystemExit(f"expected 100 topics, found {len(paired)}")
    return manifest, paired


def page_corpus(data: dict) -> str:
    parts = [
        data.get("topic_zh", ""),
        data.get("topic_ko", ""),
        data.get("category_zh", ""),
        data.get("category_ko", ""),
        "听中文",
        "单词",
        "跟着读",
        "본문",
        "단어",
        "跟着读  ·  中文版",
    ]
    for word in data["words"]:
        parts.append(word["zh"])
        parts.append(word["ko"])
    for phrase in data["phrases"]:
        parts.append(phrase["zh"])
        parts.append(phrase["ko"])
    return "\n".join(parts)


def draw_phrase(page, y, item, lay, fonts) -> float:
    sc = lay.scale
    sc_font = fonts["sc"]
    nunito = fonts["nunito"]
    kr = fonts["kr"]
    py0 = y + 1.0 + sc.py * 0.82
    for i, line in enumerate(item["py"]):
        write_text(page, (lay.text_x, py0 + i * sc.py_step), line, nunito, sc.py, PY_COLOR)
    zh0 = py0 + sc.py_step * (len(item["py"]) - 1) + sc.gap_py_zh + sc.zh * 0.82
    page.draw_circle(
        (lay.pass_x0 + sc.bullet + 0.4, zh0 - sc.zh * 0.28),
        sc.bullet,
        fill=TEAL,
        color=TEAL,
        width=0,
    )
    for i, line in enumerate(item["zh"]):
        write_text(page, (lay.text_x, zh0 + i * sc.zh_step), line, sc_font, sc.zh, BODY)
    ko0 = zh0 + sc.zh_step * (len(item["zh"]) - 1) + sc.gap_zh_ko + sc.ko * 0.82
    for i, line in enumerate(item["ko"]):
        write_text(page, (lay.text_x, ko0 + i * sc.ko_step), line, kr, sc.ko, KO_BODY)
    return y + item["h"]


def draw_words(page, lay, data, fonts) -> None:
    sc = lay.scale
    side = lay.sidebar
    sc_font = fonts["sc_bold"]
    sc_med = fonts["sc"]
    nunito = fonts["nunito"]
    kr = fonts["kr"]
    page.draw_rect(side, fill=WHITE, color=CARD_STROKE, width=0.6, radius=0.04)
    write_text(page, (side.x0 + 8, side.y0 + sc.section * 1.05), "单词", sc_font, sc.section, TEAL)
    ww = sc_font.text_length("单词", fontsize=sc.section)
    write_text(page, (side.x0 + 8 + ww + 6, side.y0 + sc.section * 1.02), "단어", kr, sc.section * 0.82, KO_BODY)
    for i, cell in enumerate(lay.word_plan):
        row = fitz.Rect(side.x0 + 5, cell["y0"], side.x1 - 5, cell["y1"])
        if i % 2 == 0:
            page.draw_rect(row, fill=MINT, color=MINT, width=0, radius=0.08)
        x = row.x0 + sc.pad_x
        cursor = cell["y0"] + sc.pad_y
        for n, line in enumerate(cell["zh"]):
            write_text(page, (x, cursor + sc.word_zh * 0.96 + n * sc.word_zh * 1.28), line, sc_font, sc.word_zh, NAVY)
        cursor += len(cell["zh"]) * sc.word_zh * 1.28 + 3.2
        for n, line in enumerate(cell["py"]):
            write_text(page, (x, cursor + sc.word_py * 1.08 + n * sc.word_py * 1.48), line, nunito, sc.word_py, PY_COLOR)
        cursor += len(cell["py"]) * sc.word_py * 1.48 + 3.2
        for n, line in enumerate(cell["ko"]):
            write_text(page, (x, cursor + sc.word_ko * 0.96 + n * sc.word_ko * 1.30), line, kr, sc.word_ko, KO_BODY)


def build_topic(data: dict, pdf_path: Path, qr_path: Path) -> Layout:
    corpus = page_corpus(data)
    sc_path = subset_sc(corpus, 500, f"sc500-{data['topic_number']:03d}.ttf")
    sc_bold_path = subset_sc(corpus, 700, f"sc700-{data['topic_number']:03d}.ttf")
    kr_path = subset_korean_font(corpus, 500, f"zhbook-kr-{data['topic_number']:03d}.ttf")
    nunito_path = pinyin_font()
    nunito_sb = FONT_DIR / "Nunito-SemiBold.ttf"
    for label, path, text in (
        ("sc", sc_path, "".join(ch for ch in corpus if "\u4e00" <= ch <= "\u9fff" or ch in "，。！？、；：《》")),
        ("kr", kr_path, "".join(ch for ch in corpus if "\uac00" <= ch <= "\ud7a3")),
        ("py", nunito_path, "".join(py_display(item.get("py") or "") for item in data["words"] + data["phrases"])),
    ):
        bad = missing_glyphs(path, text)
        if bad:
            raise SystemExit(f"topic {data['topic_number']} missing {label} glyphs: {bad}")
    fonts = {
        "sc": fitz.Font(fontfile=str(sc_path)),
        "sc_bold": fitz.Font(fontfile=str(sc_bold_path)),
        "kr": fitz.Font(fontfile=str(kr_path)),
        "nunito": fitz.Font(fontfile=str(nunito_path)),
        "nunito_sb": fitz.Font(fontfile=str(nunito_sb)),
        "nunito_reg": fitz.Font(fontfile=str(FONT_DIR / "Nunito-Regular.ttf")),
    }
    lay = autofit(data, fonts)
    if not lay.fits:
        raise SystemExit(
            f"topic {data['topic_number']} does not fit at {lay.scale.zh:.2f}pt ({lay.reason})"
        )
    doc = fitz.open()
    page = doc.new_page(width=A4.width, height=A4.height)
    page.draw_rect(A4, fill=CREAM, color=CREAM)
    page.draw_rect(fitz.Rect(0, 0, A4.width, 12), fill=TEAL, color=TEAL)

    badge = fitz.Rect(34, 32, 66, 64)
    page.draw_rect(badge, fill=TEAL, color=TEAL)
    num = str(data["topic_number"])
    nw = fonts["nunito_sb"].text_length(num, fontsize=12)
    write_text(page, ((badge.x0 + badge.x1) / 2 - nw / 2, 54.2), num, fonts["nunito_sb"], 12, WHITE)

    cat_zh = data.get("category_zh", "")
    cat_ko = data.get("category_ko", "")
    write_text(page, (78, 34.2), cat_zh, fonts["sc"], 8, TEAL)
    cat_w = fonts["sc"].text_length(cat_zh, fontsize=8)
    write_text(page, (78 + cat_w + 6, 34.0), f"·  {cat_ko}", fonts["kr"], 8, KO_UI)

    title = data["topic_zh"]
    title_size = 18.0
    while title_size > 12 and fonts["sc_bold"].text_length(title, fontsize=title_size) > 400:
        title_size -= 0.5
    write_text(page, (78, 56), title, fonts["sc_bold"], title_size, NAVY)
    write_text(page, (78, 74), data.get("topic_ko", ""), fonts["kr"], 11, KO_BODY)

    page.draw_rect(QR_CARD, fill=WHITE, color=WHITE)
    page.insert_image(QR_IMAGE, filename=str(qr_path), keep_proportion=True)
    label = "听中文"
    lw = fonts["sc"].text_length(label, fontsize=8)
    write_text(page, ((QR_CARD.x0 + QR_CARD.x1) / 2 - lw / 2, 107.2), label, fonts["sc"], 8, NAVY)

    draw_words(page, lay, data, fonts)
    write_text(page, (lay.pass_x0, CONTENT_TOP + lay.scale.section * 1.02), "跟着读", fonts["sc_bold"], lay.scale.section, TEAL)
    hw = fonts["sc_bold"].text_length("跟着读", fontsize=lay.scale.section)
    write_text(page, (lay.pass_x0 + hw + 6, CONTENT_TOP + lay.scale.section * 0.98), "본문", fonts["kr"], lay.scale.section * 0.85, KO_BODY)

    y = CONTENT_TOP + lay.scale.section * 1.55 + 2
    for item in lay.phrase_plan:
        y = draw_phrase(page, y, item, lay, fonts)

    footer = "跟着读  ·  中文版"
    write_text(page, (LEFT_MARGIN, 824), footer, fonts["sc"], 8, MUTED)
    pn = f"{data['topic_number']} / {data.get('topic_total', 100)}"
    pw = fonts["nunito_reg"].text_length(pn, fontsize=8)
    write_text(page, (RIGHT_EDGE - pw, 824), pn, fonts["nunito_reg"], 8, MUTED)

    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    doc.subset_fonts()
    doc.save(str(pdf_path), deflate=True, garbage=4)
    doc.close()
    print(
        f"{data['topic_number']:03d} zh={lay.scale.zh:.2f} "
        f"bottom={lay.passage_bottom:.0f} {pdf_path.name}"
    )
    return lay


def draw_cover(path: Path, sc: fitz.Font, sc_bold: fitz.Font, kr: fitz.Font) -> None:
    nunito_sb = fitz.Font(fontfile=str(FONT_DIR / "Nunito-SemiBold.ttf"))
    doc = fitz.open()
    page = doc.new_page(width=A4.width, height=A4.height)
    page.draw_rect(A4, fill=CREAM, color=CREAM)
    page.draw_rect(fitz.Rect(0, 0, A4.width, 12), fill=TEAL, color=TEAL)
    page.draw_circle(fitz.Point(80, 70), 70, fill=(0.847, 0.953, 0.933), color=(0.847, 0.953, 0.933))
    page.draw_circle(fitz.Point(540, 760), 90, fill=(0.992, 0.910, 0.847), color=(0.992, 0.910, 0.847))
    page.draw_rect(fitz.Rect(48, 160, A4.width - 48, 690), fill=WHITE, color=WHITE)

    def center(text, font, size, y, color):
        writer = fitz.TextWriter(page.rect)
        width = font.text_length(text, fontsize=size)
        writer.append(((A4.width - width) / 2, y), text, font=font, fontsize=size)
        writer.write_text(page, color=color)

    center("ELEMENTARY   ·   中文版", nunito_sb, 11, 240, TEAL)
    page.draw_line(
        fitz.Point(A4.width / 2 - 36, 258),
        fitz.Point(A4.width / 2 + 36, 258),
        color=(0.914, 0.769, 0.416),
        width=3,
    )
    center("跟着读", sc_bold, 40, 320, NAVY)
    center("초등 중국어 듣고 따라 읽기", kr, 16, 368, KO_BODY)
    center("米娜 13岁  ·  妹妹 11岁  ·  100个主题", sc, 13, 414, NAVY)
    lines = [
        "每个单词和每句话都有拼音。",
        "中文上面是拼音，下面是韩语意思。",
        "右边的单词从上到下读。",
        "扫右上角二维码，用中文播放。",
    ]
    y = 480
    for line in lines:
        center(line, sc, 13, y, (0.141, 0.188, 0.267))
        y += 28
    pill = fitz.Rect(A4.width / 2 - 78, 620, A4.width / 2 + 78, 652)
    page.draw_rect(pill, fill=TEAL, color=TEAL, radius=0.5)
    center("100 主题", sc_bold, 14, 642, WHITE)
    write_text(page, (LEFT_MARGIN, 824), "跟着读  ·  中文版", sc, 8, MUTED)
    doc.subset_fonts()
    doc.save(str(path), deflate=True, garbage=4)
    doc.close()


def draw_toc(path: Path, manifest: dict, sc: fitz.Font, sc_bold: fitz.Font, kr: fitz.Font) -> int:
    nunito_sb = fitz.Font(fontfile=str(FONT_DIR / "Nunito-SemiBold.ttf"))
    doc = fitz.open()
    page = None
    y = 0.0
    right = A4.width - 34

    def new_page():
        nonlocal page, y
        page = doc.new_page(width=A4.width, height=A4.height)
        page.draw_rect(A4, fill=CREAM, color=CREAM)
        page.draw_rect(fitz.Rect(0, 0, A4.width, 12), fill=TEAL, color=TEAL)
        write_text(page, (34, 52), "目录", sc_bold, 22, NAVY)
        write_text(page, (100, 50), "차례", kr, 14, KO_BODY)
        write_text(page, (34, 824), "跟着读  ·  中文版", sc, 8, MUTED)
        y = 78

    new_page()
    for section in manifest["sections"]:
        items = [t for t in manifest["topics"] if section["start"] <= t["number"] <= section["end"]]
        if y > 736:
            new_page()
        color = SECTION_COLOR.get(section["ko"], TEAL)
        band_h = 22
        gap_after_band = 18
        page.draw_rect(fitz.Rect(34, y, right, y + band_h), fill=color, color=color, radius=0.12)
        zh = SECTION_ZH[section["ko"]]
        write_text(page, (42, y + 15.5), zh, sc_bold, 11, WHITE)
        zw = sc_bold.text_length(zh, fontsize=11)
        write_text(page, (42 + zw + 10, y + 15.2), section["ko"], kr, 10, WHITE)
        y += band_h + gap_after_band
        for item in items:
            zh_title = item["topic_zh"]
            ko_title = item["topic_ko"]
            zh_w = sc.text_length(zh_title, fontsize=10)
            ko_w = kr.text_length(ko_title, fontsize=9)
            need_two = 62 + zh_w + 14 + ko_w > right
            row_h = 30 if need_two else 16
            if y + row_h > 804:
                new_page()
            write_text(page, (34, y), f"{item['number']:02d}", nunito_sb, 9, TEAL)
            write_text(page, (62, y), zh_title, sc, 10, NAVY)
            if need_two:
                y += 14
                write_text(page, (62, y), ko_title, kr, 9, KO_BODY)
                y += 16
            else:
                write_text(page, (right - ko_w, y), ko_title, kr, 9, KO_BODY)
                y += 16
        y += 8
    doc.subset_fonts()
    doc.save(str(path), deflate=True, garbage=4)
    doc.close()
    return fitz.open(str(path)).page_count


def check_pages(topics: list[tuple[dict, dict]]) -> None:
    """Every topic page is one A4 sheet, text is present, and nothing spills off the page."""
    problems = []
    for meta, data in topics:
        path = TOPIC_DIR / f"{meta['number']:03d}_{meta['slug']}_zh.pdf"
        doc = fitz.open(str(path))
        if doc.page_count != 1:
            problems.append(f"{path.name} pages={doc.page_count}")
            doc.close()
            continue
        page = doc[0]
        if abs(page.rect.width - A4.width) > 1 or abs(page.rect.height - A4.height) > 1:
            problems.append(f"{path.name} size {page.rect}")
        text = page.get_text()
        for phrase in data["phrases"]:
            if phrase["zh"] not in text and phrase["zh"].replace(" ", "") not in text.replace(" ", ""):
                # Wrapped lines still contain the characters in order in the text layer,
                # but get_text may insert newlines. Compare without whitespace.
                if "".join(phrase["zh"].split()) not in "".join(text.split()):
                    problems.append(f"{path.name} missing sentence {phrase['zh']}")
                    break
        flat = "".join(text.split())
        if data["words"][0]["zh"] not in flat:
            problems.append(f"{path.name} missing word {data['words'][0]['zh']}")
        if data["topic_zh"] not in flat:
            problems.append(f"{path.name} missing title")
        if not any(ch in text for ch in "āáǎàēéěèīíǐìōóǒòūúǔùǖǘǚǜüńň"):
            problems.append(f"{path.name} no tone marks")
        for block in page.get_text("dict")["blocks"]:
            x0, y0, x1, y1 = block["bbox"]
            if x1 > A4.width + 1 or x0 < -1 or y1 > A4.height - 4:
                problems.append(f"{path.name} overflow bbox {block['bbox']}")
                break
        clip = page.get_pixmap(matrix=fitz.Matrix(2, 2), clip=QR_IMAGE, alpha=False)
        qr_file = Path(tempfile.gettempdir()) / f"zhqr-{meta['number']:03d}.png"
        clip.save(str(qr_file))
        doc.close()
        try:
            verify_qr(qr_file, player_url(meta["number"]))
        except SystemExit as exc:
            problems.append(str(exc))
    if problems:
        raise SystemExit("page check failed:\n" + "\n".join(problems[:30]))
    print(f"Checked {len(topics)} topic pages")


def main() -> int:
    manifest, topics = load()
    cover_text = (
        "跟着读中文版小学主题米娜妹妹每个单词和每句话都有拼音韩语意思右边从上到下"
        "扫右上角二维码用中文播放听中文目录人物地方和风景我的东西爱好和兴趣学校生活"
        "日常生活健康和食物四季차례"
        + "".join(SECTION_ZH.values())
        + "".join(item["topic_zh"] for item in manifest["topics"])
        + "".join(item["topic_ko"] for item in manifest["topics"])
        + "".join(section["ko"] for section in manifest["sections"])
    )
    sc_path = subset_sc(cover_text, 500, "zh-cover-sc.ttf")
    sc_bold_path = subset_sc(cover_text, 700, "zh-cover-sc-bold.ttf")
    kr_path = subset_korean_font(cover_text, 500, "zh-cover-kr.ttf")
    sc_chars = "".join(ch for ch in cover_text if "\u4e00" <= ch <= "\u9fff")
    kr_chars = "".join(ch for ch in cover_text if "\uac00" <= ch <= "\ud7a3")
    for label, path, chars in (("cover-sc", sc_path, sc_chars), ("cover-kr", kr_path, kr_chars)):
        bad = missing_glyphs(path, chars)
        if bad:
            raise SystemExit(f"{label} missing {bad}")
    sc = fitz.Font(fontfile=str(sc_path))
    sc_bold = fitz.Font(fontfile=str(sc_bold_path))
    kr = fitz.Font(fontfile=str(kr_path))

    TOPIC_DIR.mkdir(parents=True, exist_ok=True)
    for meta, data in topics:
        url = player_url(meta["number"])
        qr_path = QR_DIR / f"{meta['number']:03d}_{meta['slug']}_zh.png"
        make_qr(qr_path, url)
        verify_qr(qr_path, url)
        pdf_path = TOPIC_DIR / f"{meta['number']:03d}_{meta['slug']}_zh.pdf"
        build_topic(data, pdf_path, qr_path)

    cover = PDF_DIR / "_cover.pdf"
    toc = PDF_DIR / "_toc.pdf"
    draw_cover(cover, sc, sc_bold, kr)
    toc_pages = draw_toc(toc, manifest, sc, sc_bold, kr)
    book = fitz.open()
    for part in (cover, toc):
        src = fitz.open(str(part))
        book.insert_pdf(src)
        src.close()
    for meta, _data in topics:
        src = fitz.open(str(TOPIC_DIR / f"{meta['number']:03d}_{meta['slug']}_zh.pdf"))
        book.insert_pdf(src)
        src.close()
    out = PDF_DIR / "listen_and_repeat_zh.pdf"
    book.set_metadata({"title": "跟着读 · 中文版", "author": "Listen and Repeat"})
    book.save(str(out), deflate=True, garbage=4)
    pages = book.page_count
    book.close()
    cover.unlink(missing_ok=True)
    toc.unlink(missing_ok=True)
    check_pages(topics)
    print(f"Book {out} pages={pages} toc={toc_pages} bytes={out.stat().st_size}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
