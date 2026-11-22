#!/usr/bin/env python3
"""Build QR codes, the combined book PDF, per-topic PDFs, and index.html.

QR codes point at the raw GitHub URL for that topic's MP3:

    https://raw.githubusercontent.com/yanchunnu/xiaoxueyingyugendu/main/audio/NNN_slug.mp3

Those URLs play in a phone browser only after the file is on the public
default branch. This repository is private, so the link will 404 for
anyone who is not signed in until the repo is made public.
"""

from __future__ import annotations

import html
import json
import subprocess
import sys
import urllib.request
from pathlib import Path

import qrcode
from fontTools.subset import Options, Subsetter
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont
from reportlab.lib.colors import Color, HexColor, white
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont as RLFont
from reportlab.pdfgen import canvas

sys.path.insert(0, str(Path(__file__).resolve().parent))

from contentlib import CONTENT, ROOT, appears  # noqa: E402

AUDIO_BASE = "https://raw.githubusercontent.com/yanchunnu/xiaoxueyingyugendu/main/audio/"
QR_DIR = ROOT / "qr"
PDF_DIR = ROOT / "pdf"
TOPIC_PDF_DIR = PDF_DIR / "topics"
FONT_DIR = ROOT / "fonts"
BUILD_FONT = ROOT / "build" / "fonts"
NOTO_URL = "https://github.com/google/fonts/raw/main/ofl/notosanskr/NotoSansKR%5Bwght%5D.ttf"

PAGE_W, PAGE_H = A4
LEFT = 34
RIGHT = 30

NAVY = HexColor("#1D3557")
TEAL = HexColor("#1F8A7D")
CORAL = HexColor("#E76F51")
CREAM = HexColor("#FFF8F0")
INK = HexColor("#243044")
KO = HexColor("#3D6F8F")
MUTED = HexColor("#6E8296")
LINE = HexColor("#E6DDD2")
CARD = HexColor("#FFFFFF")
ROW = HexColor("#F4FBFA")
GOLD = HexColor("#E9C46A")

SECTION_COLOR = {
    "인물 묘사": HexColor("#1F8A7D"),
    "장소·풍경 묘사": HexColor("#2E9B6A"),
    "개인 물건": HexColor("#D46A4C"),
    "취미·관심사": HexColor("#C4922A"),
    "학교생활": HexColor("#3D6F9A"),
    "일상생활": HexColor("#6D5BD0"),
    "건강과 음식": HexColor("#E08A2C"),
    "사계절": HexColor("#2A8FB8"),
}


def audio_url(filename: str) -> str:
    return AUDIO_BASE + filename


def ensure_noto() -> Path:
    dest = FONT_DIR / "NotoSansKR-var.ttf"
    cached = BUILD_FONT / "NotoSansKR-var.ttf"
    if dest.exists():
        return dest
    if cached.exists():
        return cached
    BUILD_FONT.mkdir(parents=True, exist_ok=True)
    print("Downloading Noto Sans KR…")
    urllib.request.urlretrieve(NOTO_URL, cached)
    return cached


def subset_noto(source: Path, weight: int, text: str, dest: Path) -> None:
    if dest.exists() and dest.stat().st_size > 1000:
        # Rebuild every run so a content change cannot keep a stale subset.
        dest.unlink()
    font = instantiateVariableFont(TTFont(str(source)), {"wght": weight}, inplace=False)
    options = Options()
    options.layout_features = ["*"]
    options.name_IDs = ["*"]
    options.notdef_outline = True
    options.recommended_glyphs = True
    subsetter = Subsetter(options=options)
    subsetter.populate(text=text)
    subsetter.subset(font)
    dest.parent.mkdir(parents=True, exist_ok=True)
    font.save(str(dest))


def collect_chars(topics: list[tuple[dict, dict]]) -> str:
    chars = set("0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz")
    chars.update(" .,!?;:'\"“”‘’()-–—·•~/&+%#[]")
    static = [
        "Listen and Repeat",
        "듣고 따라 말하기",
        "음원 듣기",
        "Words",
        "단어",
        "Let's Read",
        "본문",
        "초등 영어 듣고 따라 읽기",
        "초등학교 3–4학년",
        "100가지 주제",
        "차례",
        "뜻",
        "English",
        "참 잘했어요",
        "단어를 듣고 세 번 따라 말해 보세요.",
        "문장을 듣고 바로 따라 읽어 보세요.",
        "QR 코드를 찍으면 그 주제의 음원이 재생됩니다.",
    ]
    for item in static:
        chars.update(item)
    for meta, data in topics:
        for key in ("topic", "topic_ko", "section_ko", "section_en", "title_spoken"):
            chars.update(str(meta.get(key, "")))
            chars.update(str(data.get(key, "")))
        for word in data["words"]:
            chars.update(word["en"])
            chars.update(word["ko"])
        for phrase in data["phrases"]:
            chars.update(phrase["en"])
            chars.update(phrase["ko"])
        for line in data["full_passage_lines"]:
            chars.update(line["en"])
            chars.update(line["ko"])
        chars.update(data.get("closing_ko") or "")
    return "".join(sorted(chars))


def register_fonts(text: str) -> None:
    source = ensure_noto()
    regular = BUILD_FONT / "NotoSansKR-Regular.ttf"
    bold = BUILD_FONT / "NotoSansKR-Bold.ttf"
    print("Subsetting Korean fonts…")
    subset_noto(source, 400, text, regular)
    subset_noto(source, 700, text, bold)
    pdfmetrics.registerFont(RLFont("Nunito", str(FONT_DIR / "Nunito-Regular.ttf")))
    pdfmetrics.registerFont(RLFont("NunitoBold", str(FONT_DIR / "Nunito-Bold.ttf")))
    pdfmetrics.registerFont(RLFont("Varela", str(FONT_DIR / "VarelaRound-Regular.ttf")))
    pdfmetrics.registerFont(RLFont("Noto", str(regular)))
    pdfmetrics.registerFont(RLFont("NotoBold", str(bold)))


def fit_size(text: str, font: str, max_size: float, min_size: float, max_w: float) -> float:
    size = max_size
    while size > min_size and pdfmetrics.stringWidth(text, font, size) > max_w:
        size -= 0.4
    return size


def wrap_tokens(text: str, font: str, size: float, max_w: float) -> list[list[str]]:
    words = text.split()
    if not words:
        return [[]]
    lines: list[list[str]] = []
    cur: list[str] = []
    for word in words:
        trial = " ".join(cur + [word])
        if cur and pdfmetrics.stringWidth(trial, font, size) > max_w:
            lines.append(cur)
            cur = [word]
        else:
            cur.append(word)
    if cur:
        lines.append(cur)
    return lines


def highlight_spans(text: str, highlights: list[str]) -> list[tuple[int, int]]:
    import re

    spans = []
    for word in sorted(set(highlights), key=len, reverse=True):
        esc = re.escape(word)
        if " " in word:
            pattern = rf"(?<!\w){esc}(?!\w)"
        else:
            pattern = rf"(?<!\w){esc}(?:s|es|ed|ing|d)?(?!\w)"
        for match in re.finditer(pattern, text, flags=re.IGNORECASE):
            spans.append((match.start(), match.end()))
    return spans


def draw_english(c: canvas.Canvas, text: str, highlights: list[str], x: float, y: float, max_w: float, size: float) -> float:
    spans = highlight_spans(text, highlights)
    lines = wrap_tokens(text, "Nunito", size, max_w)
    space = pdfmetrics.stringWidth(" ", "Nunito", size)
    cursor = 0
    # Map wrapped lines back onto the original string by walking words.
    words = text.split()
    word_i = 0
    # Precompute start index of each word in `text`.
    starts = []
    search = 0
    for word in words:
        at = text.find(word, search)
        starts.append(at)
        search = at + len(word)
    for line in lines:
        cx = x
        for j, word in enumerate(line):
            if j:
                cx += space
            start = starts[word_i]
            word_i += 1
            marked = any(s < start + len(word) and e > start for s, e in spans)
            c.setFillColor(CORAL if marked else INK)
            c.setFont("Nunito", size)
            c.drawString(cx, y, word)
            width = pdfmetrics.stringWidth(word, "Nunito", size)
            if marked:
                c.setStrokeColor(CORAL)
                c.setLineWidth(1.15)
                c.line(cx, y - 1.6, cx + width, y - 1.6)
            cx += width
        y -= size + 3
    return y


def draw_korean(c: canvas.Canvas, text: str, x: float, y: float, max_w: float, size: float, font: str = "Noto", color: Color = KO) -> float:
    # Character wrap so a long Korean gloss never overflows.
    lines: list[str] = []
    cur = ""
    for ch in text:
        trial = cur + ch
        if cur and pdfmetrics.stringWidth(trial, font, size) > max_w:
            lines.append(cur)
            cur = ch
        else:
            cur = trial
    if cur:
        lines.append(cur)
    c.setFillColor(color)
    c.setFont(font, size)
    for line in lines:
        c.drawString(x, y, line)
        y -= size + 2
    return y


def make_qr(path: Path, url: str) -> None:
    code = qrcode.QRCode(
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=2,
    )
    code.add_data(url)
    code.make(fit=True)
    image = code.make_image(fill_color="#1D3557", back_color="white")
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path)


def verify_qr(path: Path, url: str) -> None:
    result = subprocess.run(["zbarimg", "-q", "--raw", str(path)], capture_output=True, text=True, check=False)
    got = result.stdout.strip()
    if got != url:
        raise SystemExit(f"QR mismatch for {path.name}:\n  got {got!r}\n  expected {url!r}")


def footer(c: canvas.Canvas, label: str) -> None:
    c.setFillColor(MUTED)
    c.setFont("Noto", 8)
    c.drawString(LEFT, 22, "Listen and Repeat   ·   듣고 따라 말하기")
    c.setFont("Nunito", 8)
    c.drawRightString(PAGE_W - RIGHT, 22, label)


def draw_topic(c: canvas.Canvas, meta: dict, data: dict, qr_path: Path, footer_label: str) -> None:
    section = meta["section_ko"]
    color = SECTION_COLOR.get(section, TEAL)
    number = int(meta["number"])
    c.setFillColor(CREAM)
    c.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)
    c.setFillColor(color)
    c.rect(0, PAGE_H - 12, PAGE_W, 12, fill=1, stroke=0)

    qr_size = 70
    qr_x = PAGE_W - RIGHT - qr_size
    qr_y = PAGE_H - 26 - qr_size
    c.setFillColor(white)
    c.roundRect(qr_x - 4, qr_y - 16, qr_size + 8, qr_size + 20, 6, fill=1, stroke=0)
    c.drawImage(ImageReader(str(qr_path)), qr_x, qr_y, qr_size, qr_size, mask="auto")
    c.setFillColor(NAVY)
    c.setFont("NotoBold", 8)
    c.drawCentredString(qr_x + qr_size / 2, qr_y - 12, "음원 듣기")

    badge_r = 16
    badge_x = LEFT + badge_r
    badge_y = PAGE_H - 48
    c.setFillColor(color)
    c.circle(badge_x, badge_y, badge_r, fill=1, stroke=0)
    c.setFillColor(white)
    c.setFont("NunitoBold", 12 if number < 100 else 10)
    c.drawCentredString(badge_x, badge_y - 4, str(number))

    title_x = badge_x + badge_r + 12
    title_w = qr_x - title_x - 12
    c.setFillColor(color)
    c.setFont("NotoBold", 8)
    c.drawString(title_x, PAGE_H - 34, f"{section}   ·   {meta['section_en']}")
    title_size = fit_size(data["topic"], "Varela", 20, 12, title_w)
    c.setFillColor(NAVY)
    c.setFont("Varela", title_size)
    c.drawString(title_x, PAGE_H - 56, data["topic"])
    c.setFillColor(KO)
    c.setFont("NotoBold", 11)
    c.drawString(title_x, PAGE_H - 74, data["topic_ko"])

    y = PAGE_H - 102
    content_w = PAGE_W - LEFT - RIGHT
    # Words card
    words = data["words"]
    rows = (len(words) + 1) // 2
    card_h = 22 + rows * 18 + 8
    c.setFillColor(CARD)
    c.setStrokeColor(LINE)
    c.setLineWidth(0.6)
    c.roundRect(LEFT, y - card_h, content_w, card_h, 8, fill=1, stroke=1)
    c.setFillColor(TEAL)
    c.setFont("NunitoBold", 10)
    c.drawString(LEFT + 12, y - 16, "Words")
    c.setFillColor(KO)
    c.setFont("NotoBold", 9)
    c.drawString(LEFT + 58, y - 16, "단어")
    row_y = y - 34
    col_w = (content_w - 24) / 2
    for i, word in enumerate(words):
        col = i % 2
        row = i // 2
        x = LEFT + 12 + col * col_w
        yy = row_y - row * 18
        if row % 2 == 0:
            c.setFillColor(ROW)
            c.rect(x - 4, yy - 4, col_w - 8, 16, fill=1, stroke=0)
        c.setFillColor(NAVY)
        c.setFont("NunitoBold", 10)
        c.drawString(x, yy, word["en"])
        en_w = pdfmetrics.stringWidth(word["en"], "NunitoBold", 10)
        c.setFillColor(KO)
        c.setFont("Noto", 9)
        c.drawString(x + en_w + 8, yy, word["ko"])
    y = y - card_h - 16

    c.setFillColor(TEAL)
    c.setFont("NunitoBold", 10)
    c.drawString(LEFT, y, "Let's Read")
    c.setFillColor(KO)
    c.setFont("NotoBold", 9)
    c.drawString(LEFT + 78, y, "본문")
    y -= 16

    text_w = content_w - 16
    for phrase in data["phrases"]:
        c.setFillColor(TEAL)
        c.circle(LEFT + 4, y + 3, 2.3, fill=1, stroke=0)
        y = draw_english(c, phrase["en"], phrase.get("highlights") or [], LEFT + 14, y, text_w, 12.5)
        y = draw_korean(c, phrase["ko"], LEFT + 14, y, text_w, 9.5)
        y -= 6
        if y < 40:
            raise RuntimeError(f"Topic {number} overflowed the page at {phrase['en']!r}")

    footer(c, footer_label)


def draw_cover(c: canvas.Canvas) -> None:
    c.setFillColor(CREAM)
    c.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)
    c.setFillColor(HexColor("#D8F3EE"))
    c.circle(70, PAGE_H - 40, 90, fill=1, stroke=0)
    c.setFillColor(HexColor("#FDE8D8"))
    c.circle(PAGE_W - 30, 120, 110, fill=1, stroke=0)
    c.setFillColor(HexColor("#FFF3C4"))
    c.circle(PAGE_W - 80, PAGE_H - 60, 50, fill=1, stroke=0)
    c.setFillColor(TEAL)
    c.rect(0, PAGE_H - 12, PAGE_W, 12, fill=1, stroke=0)

    c.setFillColor(white)
    c.roundRect(48, 150, PAGE_W - 96, 520, 18, fill=1, stroke=0)
    c.setFillColor(TEAL)
    c.setFont("NunitoBold", 11)
    c.drawCentredString(PAGE_W / 2, 620, "ELEMENTARY ENGLISH   ·   GRADE 3–4")
    c.setStrokeColor(GOLD)
    c.setLineWidth(3)
    c.line(PAGE_W / 2 - 36, 606, PAGE_W / 2 + 36, 606)
    c.setFillColor(NAVY)
    c.setFont("Varela", 32)
    c.drawCentredString(PAGE_W / 2, 550, "Listen and Repeat")
    c.setFillColor(KO)
    c.setFont("NotoBold", 20)
    c.drawCentredString(PAGE_W / 2, 508, "초등 영어 듣고 따라 읽기")
    c.setFillColor(INK)
    c.setFont("Noto", 12)
    c.drawCentredString(PAGE_W / 2, 470, "초등학교 3–4학년   ·   100가지 주제")

    lines = [
        "단어를 듣고, 세 번 따라 말해 보세요.",
        "문장을 듣고, 바로 따라 읽어 보세요.",
        "오른쪽 위 QR 코드를 찍으면",
        "그 주제의 음원이 재생됩니다.",
    ]
    y = 400
    for line in lines:
        c.setFont("Noto", 12)
        c.setFillColor(INK)
        c.drawCentredString(PAGE_W / 2, y, line)
        y -= 22
    c.setFillColor(TEAL)
    c.roundRect(PAGE_W / 2 - 70, 250, 140, 28, 14, fill=1, stroke=0)
    c.setFillColor(white)
    c.setFont("NunitoBold", 11)
    c.drawCentredString(PAGE_W / 2, 259, "100 TOPICS")
    footer(c, "")


def draw_toc(c: canvas.Canvas, manifest: dict) -> int:
    """Draw the table of contents. Returns the number of TOC pages."""
    topics = manifest["topics"]
    by_section: list[tuple[dict, list[dict]]] = []
    for section in manifest["sections"]:
        items = [t for t in topics if section["start"] <= t["number"] <= section["end"]]
        by_section.append((section, items))

    def new_page(first: bool) -> float:
        if not first:
            c.showPage()
        c.setFillColor(CREAM)
        c.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)
        c.setFillColor(TEAL)
        c.rect(0, PAGE_H - 12, PAGE_W, 12, fill=1, stroke=0)
        c.setFillColor(NAVY)
        c.setFont("Varela", 22)
        c.drawString(LEFT, PAGE_H - 48, "Contents")
        c.setFillColor(KO)
        c.setFont("NotoBold", 12)
        c.drawString(LEFT + 130, PAGE_H - 46, "차례")
        footer(c, "")
        return PAGE_H - 78

    y = new_page(True)
    pages = 1
    for section, items in by_section:
        if y < 80:
            y = new_page(False)
            pages += 1
        color = SECTION_COLOR.get(section["ko"], TEAL)
        c.setFillColor(color)
        c.roundRect(LEFT, y - 6, PAGE_W - LEFT - RIGHT, 20, 4, fill=1, stroke=0)
        c.setFillColor(white)
        c.setFont("NotoBold", 10)
        c.drawString(LEFT + 8, y, f"{section['ko']}    {section['en']}")
        y -= 26
        for item in items:
            if y < 42:
                y = new_page(False)
                pages += 1
            c.setFillColor(TEAL)
            c.setFont("NunitoBold", 9)
            c.drawString(LEFT, y, f"{item['number']:02d}")
            c.setFillColor(NAVY)
            c.setFont("Nunito", 9)
            c.drawString(LEFT + 28, y, item["topic"])
            c.setFillColor(KO)
            c.setFont("Noto", 9)
            c.drawRightString(PAGE_W - RIGHT, y, item["topic_ko"])
            y -= 15
        y -= 8
    return pages


def load_topics() -> tuple[dict, list[tuple[dict, dict]]]:
    manifest = json.loads((CONTENT / "manifest.json").read_text(encoding="utf-8"))
    paired = []
    for meta in manifest["topics"]:
        data = json.loads((ROOT / meta["file"]).read_text(encoding="utf-8"))
        paired.append((meta, data))
    return manifest, paired


def write_index(manifest: dict) -> None:
    parts = [
        "<!DOCTYPE html>",
        '<html lang="ko">',
        "<head>",
        '<meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        "<title>초등 영어 듣고 따라 읽기</title>",
        "<style>",
        "body{margin:0;background:#FFF8F0;color:#243044;font-family:'Nunito','Noto Sans KR',sans-serif;}",
        "header{background:#1F8A7D;color:white;padding:28px 20px;}",
        "header h1{margin:0 0 6px;font-size:28px;}",
        "header p{margin:0;line-height:1.5;}",
        "main{max-width:880px;margin:0 auto;padding:20px;}",
        "section{margin:0 0 28px;}",
        "h2{margin:0 0 10px;font-size:18px;color:#1F8A7D;}",
        "article{background:white;border-radius:12px;padding:12px 14px;margin:0 0 10px;box-shadow:0 1px 2px rgba(0,0,0,.05);}",
        "article strong{display:block;color:#1D3557;}",
        "article span{color:#3D6F8F;font-size:14px;}",
        "audio{width:100%;margin-top:8px;}",
        "footer{color:#6E8296;font-size:13px;padding:8px 20px 28px;max-width:880px;margin:0 auto;}",
        "</style>",
        "</head><body>",
        "<header><h1>Listen and Repeat</h1>",
        "<p>초등 영어 듣고 따라 읽기 · 초등학교 3–4학년 · 100가지 주제</p></header>",
        "<main>",
    ]
    for section in manifest["sections"]:
        parts.append(f"<section><h2>{html.escape(section['ko'])} · {html.escape(section['en'])}</h2>")
        for item in manifest["topics"]:
            if not section["start"] <= item["number"] <= section["end"]:
                continue
            src = html.escape(item["audio"])
            parts.append(
                "<article>"
                f"<strong>{item['number']:02d}. {html.escape(item['topic'])}</strong>"
                f"<span>{html.escape(item['topic_ko'])}</span>"
                f'<audio controls preload="none" src="{src}"></audio>'
                "</article>"
            )
        parts.append("</section>")
    parts.append("</main>")
    parts.append(
        "<footer>각 주제 페이지의 QR 코드는 "
        "raw.githubusercontent.com 의 MP3 주소입니다. "
        "저장소가 비공개이면 로그인하지 않은 휴대폰에서는 재생되지 않습니다. "
        "이 페이지의 재생기는 같은 폴더의 audio 파일을 사용합니다.</footer>"
    )
    parts.append("</body></html>")
    (ROOT / "index.html").write_text("\n".join(parts) + "\n", encoding="utf-8")


def main() -> int:
    manifest, topics = load_topics()
    if len(topics) != 100:
        raise SystemExit(f"expected 100 topics, found {len(topics)}")
    register_fonts(collect_chars(topics))

    QR_DIR.mkdir(parents=True, exist_ok=True)
    TOPIC_PDF_DIR.mkdir(parents=True, exist_ok=True)
    qr_paths = {}
    for meta, _data in topics:
        filename = Path(meta["audio"]).name
        url = audio_url(filename)
        path = QR_DIR / (Path(filename).stem + ".png")
        make_qr(path, url)
        verify_qr(path, url)
        qr_paths[meta["number"]] = path
    print(f"QR codes verified: {len(qr_paths)}")

    book_path = PDF_DIR / "listen_and_repeat.pdf"
    book = canvas.Canvas(str(book_path), pagesize=A4)
    book.setTitle("초등 영어 듣고 따라 읽기")
    book.setAuthor("Listen and Repeat")
    draw_cover(book)
    book.showPage()
    draw_toc(book, manifest)
    book.showPage()
    for meta, data in topics:
        draw_topic(book, meta, data, qr_paths[meta["number"]], f"{meta['number']} / 100")
        book.bookmarkPage(f"t{meta['number']}")
        book.addOutlineEntry(f"{meta['number']:02d}  {meta['topic']}", f"t{meta['number']}", level=0, closed=False)
        book.showPage()
        single = canvas.Canvas(str(TOPIC_PDF_DIR / f"{meta['number']:03d}_{meta['slug']}.pdf"), pagesize=A4)
        single.setTitle(f"{meta['number']:02d} {data['topic']}")
        draw_topic(single, meta, data, qr_paths[meta["number"]], f"{meta['number']:02d}")
        single.save()
    book.save()
    write_index(manifest)
    print(f"Book: {book_path} ({book_path.stat().st_size/1024/1024:.1f} MB)")
    print(f"Topic PDFs: {len(list(TOPIC_PDF_DIR.glob('*.pdf')))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
