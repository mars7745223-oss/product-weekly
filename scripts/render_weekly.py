"""Render common Markdown into a compact PDF baseline with local CJK fonts."""
import argparse
import html
import re
import warnings
from pathlib import Path
from urllib.parse import urlparse


def find_font(explicit=None):
    if explicit:
        font = Path(explicit).expanduser()
        if not font.is_file():
            raise ValueError("Font file not found: " + str(font))
        return font
    candidates = [
        Path("C:/Windows/Fonts/msyh.ttc"), Path("C:/Windows/Fonts/simhei.ttf"),
        Path("/System/Library/Fonts/PingFang.ttc"),
        Path("/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"),
        Path("/usr/share/fonts/truetype/arphic/uming.ttc"),
        Path.home() / ".fonts/NotoSansSC-Regular.ttf",
    ]
    for font in candidates:
        if font.is_file():
            return font
    raise ValueError("No supported local Chinese TrueType font found; pass --font PATH. Font files are not bundled.")


def inline(text, base):
    """Escape HTML first; expose only Markdown emphasis and validated links."""
    pieces, cursor = [], 0
    for match in re.finditer(r"\[([^\]]+)\]\(([^)]+)\)", text):
        pieces.append(html.escape(text[cursor:match.start()]))
        label, raw = match.groups()
        parsed = urlparse(raw)
        if parsed.scheme in {"http", "https", "mailto"}:
            target = raw
        elif not parsed.scheme:
            target = (base / raw).resolve().as_uri()
        else:
            raise ValueError("Unsupported link scheme: " + parsed.scheme)
        pieces.append('<link href="' + html.escape(target, quote=True)
                      + '" color="#398f98">' + html.escape(label) + "</link>")
        cursor = match.end()
    pieces.append(html.escape(text[cursor:]))
    rendered = "".join(pieces)
    rendered = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", rendered)
    rendered = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<i>\1</i>", rendered)
    rendered = re.sub(r"`([^`]+)`", r'<font color="#46575d">\1</font>', rendered)
    return rendered


def blocks(markdown):
    lines, n = markdown.splitlines(), 0
    while n < len(lines):
        line = lines[n].strip()
        if not line:
            n += 1
            continue
        if line.startswith("```"):
            language, body = line[3:].strip(), []
            n += 1
            while n < len(lines) and not lines[n].strip().startswith("```"):
                body.append(lines[n])
                n += 1
            if language in {"mermaid", "math", "latex"}:
                warnings.warn(language + " block rendered as literal text; use a dedicated figure renderer")
            yield "code", "\n".join(body)
            n += 1
        elif line.startswith("|") and n + 1 < len(lines) and re.fullmatch(r"[|\s:\-]+", lines[n + 1].strip()):
            rows = [line]
            n += 2
            while n < len(lines) and lines[n].strip().startswith("|"):
                rows.append(lines[n].strip())
                n += 1
            yield "table", [[cell.strip() for cell in row.strip("|").split("|")] for row in rows]
        elif re.fullmatch(r"!\[[^\]]*\]\([^)]+\)", line):
            match = re.fullmatch(r"!\[([^\]]*)\]\(([^)]+)\)", line)
            yield "image", match.groups()
            n += 1
        elif line.startswith("#") and re.match(r"^#{1,6}\s+", line):
            match = re.match(r"^(#{1,6})\s+(.*)", line)
            yield "heading", (len(match[1]), match[2])
            n += 1
        elif re.match(r"^([-*+] |\d+[.)] )", line):
            match = re.match(r"^([-*+]|\d+[.)])\s+(.*)", line)
            yield "list", (match[1], match[2])
            n += 1
        elif line in {"---", "***", "___"}:
            yield "rule", None
            n += 1
        else:
            paragraph = [line]
            n += 1
            while n < len(lines) and lines[n].strip():
                nxt = lines[n].strip()
                if nxt.startswith(("#", "|", "```", "![")) or re.match(r"^([-*+] |\d+[.)] )", nxt):
                    break
                paragraph.append(nxt)
                n += 1
            yield "paragraph", " ".join(paragraph)


def require_glyphs(text, charmap):
    missing = sorted({ch for ch in text if not ch.isspace() and ord(ch) not in charmap})
    if missing:
        preview = " ".join("U+%04X" % ord(ch) for ch in missing[:12])
        raise ValueError("Selected font lacks input text glyphs: " + preview + "; pass a font covering the document text")


def render(input_path, output_path, font=None, title=None, cover_image=None):
    try:
        from reportlab.lib import colors
        from reportlab.lib.enums import TA_LEFT
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import ParagraphStyle
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        from reportlab.platypus import (
            SimpleDocTemplate, Paragraph, Table, TableStyle, Image, Spacer,
            PageBreak, HRFlowable)
    except ImportError as exc:
        raise ValueError("Install optional dependencies from requirements-pdf.txt") from exc
    input_path, output_path = Path(input_path), Path(output_path)
    markdown = input_path.read_text(encoding="utf-8-sig")
    selected = find_font(font)
    try:
        pdfmetrics.registerFont(TTFont("WeeklyCJK", str(selected), subfontIndex=0))
    except Exception as exc:
        raise ValueError("Font is not a compatible TrueType font; pass a CJK .ttf or supported .ttc: " + str(selected)) from exc
    registered = pdfmetrics.getFont("WeeklyCJK")
    require_glyphs(markdown + "产品周刊 · 事实与分析" + (title or ""), registered.face.charToGlyph)
    pdfmetrics.registerFontFamily("WeeklyCJK", normal="WeeklyCJK", bold="WeeklyCJK", italic="WeeklyCJK", boldItalic="WeeklyCJK")
    width, height = A4
    usable = width - 92
    style = ParagraphStyle("body", fontName="WeeklyCJK", fontSize=10.3,
                           leading=15.6, textColor=colors.HexColor("#172b34"),
                           spaceAfter=7, wordWrap="CJK", alignment=TA_LEFT)
    headings = {
        level: ParagraphStyle("h" + str(level), parent=style,
                              fontSize={1: 22, 2: 16, 3: 12.5}.get(level, 11),
                              leading={1: 29, 2: 22, 3: 18}.get(level, 16),
                              spaceBefore=14 if level != 1 else 0,
                              spaceAfter=7, keepWithNext=True,
                              textColor=colors.HexColor("#398f98"))
        for level in range(1, 7)}
    cellstyle = ParagraphStyle("cell", parent=style, fontSize=9, leading=13, spaceAfter=0)
    liststyle = ParagraphStyle("list", parent=style, leftIndent=12, firstLineIndent=-10)
    codestyle = ParagraphStyle("code", parent=style, fontSize=9, leading=13,
                               backColor=colors.HexColor("#edf5f5"), borderPadding=6)
    story = []
    if cover_image:
        path = Path(cover_image)
        if not path.is_file():
            raise ValueError("Cover image not found: " + str(path))
        story.append(Paragraph(inline(title or "产品周刊", input_path.parent), headings[1]))
        cover = Image(str(path))
        scale = min(usable / cover.imageWidth, (height - 170) / cover.imageHeight)
        cover.drawWidth, cover.drawHeight = cover.imageWidth * scale, cover.imageHeight * scale
        story.extend([Spacer(1, 10), cover, PageBreak()])
    for kind, value in blocks(markdown):
        if kind == "heading":
            level, text = value
            story.append(Paragraph(inline(text, input_path.parent), headings[level]))
        elif kind == "paragraph":
            story.append(Paragraph(inline(value, input_path.parent), style))
        elif kind == "list":
            marker, text = value
            marker = "-" if marker in {"-", "*", "+"} else marker
            story.append(Paragraph(html.escape(marker) + " " + inline(text, input_path.parent), liststyle))
        elif kind == "table":
            columns = len(value[0])
            if any(len(row) != columns for row in value):
                raise ValueError("Markdown table rows have unequal column counts")
            table = Table([[Paragraph(inline(cell, input_path.parent), cellstyle) for cell in row]
                           for row in value], colWidths=[usable / columns] * columns,
                          repeatRows=1, hAlign="LEFT")
            table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e3f1f1")),
                ("LINEBELOW", (0, 0), (-1, 0), .7, colors.HexColor("#78afb4")),
                ("LINEBELOW", (0, 1), (-1, -1), .3, colors.HexColor("#d5e4e5")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]))
            story.extend([table, Spacer(1, 8)])
        elif kind == "image":
            alt, raw = value
            if urlparse(raw).scheme in {"http", "https"}:
                raise ValueError("Use a local permitted image; remote images are not downloaded")
            path = (input_path.parent / raw).resolve()
            if not path.is_file():
                raise ValueError("Image not found: " + str(path))
            image = Image(str(path))
            scale = min(1, usable / image.imageWidth, (height - 160) / image.imageHeight)
            image.drawWidth, image.drawHeight = image.imageWidth * scale, image.imageHeight * scale
            story.extend([image, Paragraph(inline(alt, input_path.parent), cellstyle), Spacer(1, 8)])
        elif kind == "code":
            story.append(Paragraph(html.escape(value).replace("\n", "<br/>"), codestyle))
        elif kind == "rule":
            story.append(HRFlowable(width="100%", thickness=.5, color=colors.HexColor("#bdd7d9"), spaceAfter=7))
    if not story:
        raise ValueError("Input has no content")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(str(output_path), pagesize=A4, leftMargin=46, rightMargin=46,
                            topMargin=42, bottomMargin=43, title=title or input_path.stem,
                            author="产品周刊", pageCompression=1)

    def footer(canvas, document):
        canvas.setStrokeColor(colors.HexColor("#c8dddf"))
        canvas.setLineWidth(.4)
        canvas.line(46, 32, width - 46, 32)
        canvas.setFont("WeeklyCJK", 8)
        canvas.setFillColor(colors.HexColor("#637c85"))
        canvas.drawString(46, 20, "产品周刊 · 事实与分析")
        canvas.drawRightString(width - 46, 20, str(document.page))
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    return {"output": str(output_path), "font": str(selected), "renderer": "compact-baseline/1"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--font", type=Path)
    parser.add_argument("--title")
    parser.add_argument("--cover-image", type=Path)
    args = parser.parse_args()
    try:
        result = render(args.input, args.output, args.font, args.title, args.cover_image)
    except (OSError, ValueError) as exc:
        parser.exit(2, "Render failed: " + str(exc) + "\n")
    print(result["output"])


if __name__ == "__main__":
    main()
