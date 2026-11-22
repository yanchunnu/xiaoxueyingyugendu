#!/usr/bin/env python3
"""Build QR codes, per-topic pages, and the combined book PDF.

Topic pages use scripts/make_page_pdf.py (right-hand word column, auto-fit type).
"""

from __future__ import annotations

import html
import json
import subprocess
import sys
from pathlib import Path

import fitz
import qrcode

sys.path.insert(0, str(Path(__file__).resolve().parent))

from contentlib import CONTENT, ROOT  # noqa: E402
from make_page_pdf import (  # noqa: E402
    CREAM,
    FONT_DIR,
    KO_BODY,
    LEFT_MARGIN,
    MUTED,
    NAVY,
    TEAL,
    WHITE,
    build,
    subset_korean_font,
)

PAGES = "https://yanchunnu.github.io/xiaoxueyingyugendu/player.html?t="
QR_DIR = ROOT / "qr"
PDF_DIR = ROOT / "pdf"
TOPIC_PDF_DIR = PDF_DIR / "topics"
A4 = fitz.paper_rect("a4")

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


def player_url(number: int) -> str:
    return f"{PAGES}{number:03d}"


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
        data.setdefault("category_en", meta["section_en"])
        paired.append((meta, data))
    return manifest, paired


def _font(path: Path) -> fitz.Font:
    return fitz.Font(fontfile=str(path))


def draw_cover(path: Path, kr: fitz.Font, kr_med: fitz.Font) -> None:
    varela = _font(FONT_DIR / "VarelaRound-Regular.ttf")
    nunito_sb = _font(FONT_DIR / "Nunito-SemiBold.ttf")
    doc = fitz.open()
    page = doc.new_page(width=A4.width, height=A4.height)
    page.draw_rect(A4, fill=CREAM, color=CREAM)
    page.draw_rect(fitz.Rect(0, 0, A4.width, 12), fill=TEAL, color=TEAL)
    page.draw_circle(fitz.Point(80, 70), 70, fill=(0.847, 0.953, 0.933), color=(0.847, 0.953, 0.933))
    page.draw_circle(fitz.Point(540, 760), 90, fill=(0.992, 0.910, 0.847), color=(0.992, 0.910, 0.847))
    card = fitz.Rect(48, 160, A4.width - 48, 680)
    page.draw_rect(card, fill=WHITE, color=WHITE, radius=0.04)
    def center(text, font, size, y, color):
        writer = fitz.TextWriter(page.rect)
        width = font.text_length(text, fontsize=size)
        writer.append(((A4.width - width) / 2, y), text, font=font, fontsize=size)
        writer.write_text(page, color=color)

    center("ELEMENTARY ENGLISH   ·   GRADE 3–4", nunito_sb, 11, 250, TEAL)
    page.draw_line(fitz.Point(A4.width / 2 - 36, 268), fitz.Point(A4.width / 2 + 36, 268), color=(0.914, 0.769, 0.416), width=3)
    center("Listen and Repeat", varela, 32, 330, NAVY)
    center("초등 영어 듣고 따라 읽기", kr_med, 20, 378, KO_BODY)
    center("초등학교 3–4학년   ·   100가지 주제", kr, 12, 420, (0.141, 0.188, 0.267))
    lines = [
        "단어를 듣고, 세 번 따라 말해 보세요.",
        "문장을 듣고, 바로 따라 읽어 보세요.",
        "오른쪽 위 QR 코드를 찍으면",
        "그 주제의 음원이 재생됩니다.",
    ]
    y = 490
    for line in lines:
        center(line, kr, 13, y, (0.141, 0.188, 0.267))
        y += 26
    pill = fitz.Rect(A4.width / 2 - 78, 610, A4.width / 2 + 78, 642)
    page.draw_rect(pill, fill=TEAL, color=TEAL, radius=0.5)
    center("100 TOPICS", nunito_sb, 12, 632, WHITE)
    footer = "Listen and Repeat   ·   듣고 따라 말하기"
    tw2 = fitz.TextWriter(page.rect)
    tw2.append((LEFT_MARGIN, 818), footer, font=kr, fontsize=8)
    tw2.write_text(page, color=MUTED)
    path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(path), deflate=True)
    doc.close()


def draw_toc(path: Path, manifest: dict, kr: fitz.Font, kr_med: fitz.Font) -> None:
    nunito = _font(FONT_DIR / "Nunito-Regular.ttf")
    nunito_sb = _font(FONT_DIR / "Nunito-SemiBold.ttf")
    varela = _font(FONT_DIR / "VarelaRound-Regular.ttf")
    doc = fitz.open()
    page = None
    y = 0

    def new_page():
        nonlocal page, y
        page = doc.new_page(width=A4.width, height=A4.height)
        page.draw_rect(A4, fill=CREAM, color=CREAM)
        page.draw_rect(fitz.Rect(0, 0, A4.width, 12), fill=TEAL, color=TEAL)
        tw = fitz.TextWriter(page.rect)
        tw.append((34, 52), "Contents", font=varela, fontsize=22)
        tw.write_text(page, color=NAVY)
        tw = fitz.TextWriter(page.rect)
        tw.append((168, 50), "차례", font=kr_med, fontsize=14)
        tw.write_text(page, color=KO_BODY)
        tw = fitz.TextWriter(page.rect)
        tw.append((34, 818), "Listen and Repeat   ·   듣고 따라 말하기", font=kr, fontsize=8)
        tw.write_text(page, color=MUTED)
        y = 78

    new_page()
    right = A4.width - 34
    for section in manifest["sections"]:
        items = [t for t in manifest["topics"] if section["start"] <= t["number"] <= section["end"]]
        if y > 780:
            new_page()
        color = SECTION_COLOR.get(section["ko"], TEAL)
        page.draw_rect(fitz.Rect(34, y, right, y + 20), fill=color, color=color, radius=0.15)
        tw = fitz.TextWriter(page.rect)
        tw.append((42, y + 14), f"{section['ko']}    {section['en']}", font=kr_med, fontsize=10)
        tw.write_text(page, color=WHITE)
        y += 28
        for item in items:
            if y > 800:
                new_page()
            tw = fitz.TextWriter(page.rect)
            tw.append((34, y), f"{item['number']:02d}", font=nunito_sb, fontsize=9)
            tw.write_text(page, color=TEAL)
            tw = fitz.TextWriter(page.rect)
            tw.append((62, y), item["topic"], font=nunito, fontsize=9)
            tw.write_text(page, color=NAVY)
            ko = item["topic_ko"]
            kw = kr.text_length(ko, fontsize=9)
            tw = fitz.TextWriter(page.rect)
            tw.append((right - kw, y), ko, font=kr, fontsize=9)
            tw.write_text(page, color=KO_BODY)
            y += 16
        y += 8
    doc.save(str(path), deflate=True)
    doc.close()


def write_index(manifest: dict) -> None:
    parts = [
        "<!DOCTYPE html>",
        '<html lang="ko"><head><meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        "<title>초등 영어 듣고 따라 읽기</title>",
        "<style>",
        "body{margin:0;background:#FFF8F0;color:#243044;font-family:Nunito,'Noto Sans KR',sans-serif;}",
        "header{background:#1F8A7D;color:#fff;padding:28px 20px;} header h1{margin:0 0 6px;}",
        "main{max-width:880px;margin:0 auto;padding:20px;} h2{color:#1F8A7D;font-size:18px;}",
        "article{background:#fff;border-radius:12px;padding:12px 14px;margin:0 0 10px;}",
        "article strong{display:block;color:#1D3557;} article span{color:#3D6F8F;}",
        "audio{width:100%;margin-top:8px;} footer{max-width:880px;margin:0 auto;color:#6E8296;font-size:13px;padding:8px 20px 28px;}",
        "</style></head><body>",
        "<header><h1>Listen and Repeat</h1>",
        "<p>초등 영어 듣고 따라 읽기 · 민아 13살 6학년 · 100가지 주제</p></header><main>",
    ]
    for section in manifest["sections"]:
        parts.append(f"<section><h2>{html.escape(section['ko'])} · {html.escape(section['en'])}</h2>")
        for item in manifest["topics"]:
            if not section["start"] <= item["number"] <= section["end"]:
                continue
            src = html.escape(item["audio"])
            player = f"player.html?t={item['number']:03d}"
            parts.append(
                "<article>"
                f"<strong><a href=\"{player}\">{item['number']:02d}. {html.escape(item['topic'])}</a></strong>"
                f"<span>{html.escape(item['topic_ko'])}</span>"
                f"<p><a href=\"{player}\">따라 읽기 열기</a></p>"
                f'<audio controls preload="none" src="{src}"></audio></article>'
            )
        parts.append("</section>")
    parts.append("</main><footer>각 주제 QR은 raw.githubusercontent.com 의 MP3입니다. "
                 "저장소가 비공개이면 로그인하지 않은 휴대폰에서는 재생되지 않습니다. "
                 "이 페이지는 같은 폴더의 audio 파일을 재생합니다.</footer></body></html>")
    (ROOT / "index.html").write_text("\n".join(parts) + "\n", encoding="utf-8")


def main() -> int:
    manifest, topics = load()
    if len(topics) != 100:
        raise SystemExit(f"expected 100 topics, found {len(topics)}")
    corpus = " ".join(
        " ".join([
            meta["topic"], meta["topic_ko"], meta["section_ko"], meta["section_en"],
            "차례", "Contents", "음원 듣기", "듣고 따라 말하기", "초등 영어 듣고 따라 읽기",
        ])
        for meta, _ in topics
    )
    kr = fitz.Font(fontfile=str(subset_korean_font(corpus, 400, "book-kr-reg.ttf")))
    kr_med = fitz.Font(fontfile=str(subset_korean_font(corpus, 500, "book-kr-med.ttf")))

    QR_DIR.mkdir(parents=True, exist_ok=True)
    TOPIC_PDF_DIR.mkdir(parents=True, exist_ok=True)
    for meta, data in topics:
        url = player_url(meta["number"])
        qr_path = QR_DIR / f"{meta['number']:03d}_{meta['slug']}.png"
        make_qr(qr_path, url)
        verify_qr(qr_path, url)
        pdf_path = TOPIC_PDF_DIR / f"{meta['number']:03d}_{meta['slug']}.pdf"
        build(data, pdf_path, None, qr_path)
    print("QR codes verified: 100")

    cover = PDF_DIR / "_cover.pdf"
    toc = PDF_DIR / "_toc.pdf"
    draw_cover(cover, kr, kr_med)
    draw_toc(toc, manifest, kr, kr_med)

    book = fitz.open()
    for part in (cover, toc):
        src = fitz.open(str(part))
        book.insert_pdf(src)
        src.close()
    for meta, _data in topics:
        src = fitz.open(str(TOPIC_PDF_DIR / f"{meta['number']:03d}_{meta['slug']}.pdf"))
        book.insert_pdf(src)
        src.close()
    out = PDF_DIR / "listen_and_repeat.pdf"
    book.set_metadata({"title": "초등 영어 듣고 따라 읽기", "author": "Listen and Repeat"})
    book.save(str(out), deflate=True, garbage=4)
    book.close()
    cover.unlink(missing_ok=True)
    toc.unlink(missing_ok=True)
    write_index(manifest)
    print(f"Book {out} ({out.stat().st_size} bytes), topics {len(list(TOPIC_PDF_DIR.glob('*.pdf')))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
