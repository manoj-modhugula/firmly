# Changes: module organization, naming, and safe diagnostics.
"""Firmly PDF exporter: safe Markdown tokens, readable pagination, no remote assets."""

import io
import re
from html import escape
from urllib.parse import urlsplit

from markdown_it import MarkdownIt
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import HRFlowable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

PARSER = MarkdownIt("commonmark", {"html": False}).enable("table")
INK = colors.HexColor("#202938")
MUTED = colors.HexColor("#5e6c83")
LINK = colors.HexColor("#496697")
STYLES = {
    "body": ParagraphStyle(
        "body",
        fontName="Helvetica",
        fontSize=10.5,
        leading=16,
        textColor=INK,
        spaceAfter=8,
        splitLongWords=True,
    ),
    "h1": ParagraphStyle(
        "h1", fontName="Helvetica-Bold", fontSize=23, leading=29, textColor=INK, spaceAfter=20
    ),
    "h2": ParagraphStyle(
        "h2",
        fontName="Helvetica-Bold",
        fontSize=16,
        leading=22,
        textColor=INK,
        spaceBefore=18,
        spaceAfter=10,
        keepWithNext=True,
    ),
    "h3": ParagraphStyle(
        "h3",
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=18,
        textColor=INK,
        spaceBefore=12,
        spaceAfter=6,
        keepWithNext=True,
    ),
    "bullet": ParagraphStyle(
        "bullet",
        fontName="Helvetica",
        fontSize=10.5,
        leading=16,
        textColor=INK,
        leftIndent=14,
        firstLineIndent=-10,
        spaceAfter=7,
    ),
    "cell": ParagraphStyle(
        "cell", fontName="Helvetica", fontSize=9, leading=13, textColor=INK, splitLongWords=True
    ),
}


def inline(tokens):
    result = []
    links = []
    for token in tokens or []:
        kind = token.type
        if kind == "text":
            result.append(escape(token.content))
        elif kind == "code_inline":
            result.append('<font name="Courier">' + escape(token.content) + "</font>")
        elif kind in {"softbreak", "hardbreak"}:
            result.append("<br/>")
        elif kind == "strong_open":
            result.append("<b>")
        elif kind == "strong_close":
            result.append("</b>")
        elif kind == "em_open":
            result.append("<i>")
        elif kind == "em_close":
            result.append("</i>")
        elif kind == "link_open":
            href = token.attrGet("href") or ""
            allowed = urlsplit(href).scheme in {"https", "http"}
            links.append(allowed)
            if allowed:
                result.append(f'<link href="{escape(href, quote=True)}" color="#496697">')
        elif kind == "link_close":
            if links and links.pop():
                result.append("</link>")
        elif kind == "image":
            result.append(escape(token.content))
        elif token.content:
            result.append(escape(token.content))
    return "".join(result)


def render_pdf(markdown, buffer):
    tokens = PARSER.parse(markdown)
    story = [
        Paragraph(
            "FIRMLY · COMPANY RESEARCH",
            ParagraphStyle(
                "brand",
                fontName="Helvetica",
                fontSize=9,
                leading=14,
                textColor=MUTED,
                spaceAfter=14,
            ),
        )
    ]
    heading = None
    list_depth = 0
    numbered = []
    table_rows = None
    table_row = []
    table_cell = False
    for token in tokens:
        kind = token.type
        if kind == "heading_open":
            heading = token.tag
        elif kind == "heading_close":
            heading = None
        elif kind in {"bullet_list_open", "ordered_list_open"}:
            list_depth += 1
            numbered.append(
                int(token.attrGet("start") or 1) if kind == "ordered_list_open" else None
            )
        elif kind in {"bullet_list_close", "ordered_list_close"}:
            list_depth = max(0, list_depth - 1)
            if numbered:
                numbered.pop()
        elif kind == "table_open":
            table_rows = []
        elif kind == "tr_open":
            table_row = []
        elif kind in {"th_open", "td_open"}:
            table_cell = True
        elif kind in {"th_close", "td_close"}:
            table_cell = False
        elif kind == "tr_close":
            if table_rows is not None:
                table_rows.append(table_row)
        elif kind == "table_close":
            if table_rows:
                columns = max(map(len, table_rows))
                rows = [
                    r + [Paragraph("", STYLES["cell"])] * (columns - len(r)) for r in table_rows
                ]
                table = Table(
                    rows, colWidths=[(A4[0] - 96) / columns] * columns, repeatRows=1, hAlign="LEFT"
                )
                table.setStyle(
                    TableStyle(
                        [
                            ("VALIGN", (0, 0), (-1, -1), "TOP"),
                            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#edf1f8")),
                            ("LINEBELOW", (0, 0), (-1, -1), 0.4, colors.HexColor("#dce3ee")),
                            ("LEFTPADDING", (0, 0), (-1, -1), 8),
                            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                            ("TOPPADDING", (0, 0), (-1, -1), 8),
                            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                        ]
                    )
                )
                story.extend([table, Spacer(1, 12)])
            table_rows = None
        elif kind == "inline":
            text = inline(token.children)
            if not text:
                continue
            if table_cell:
                table_row.append(Paragraph(text, STYLES["cell"]))
                continue
            style = (
                STYLES.get(heading, STYLES["h3"])
                if heading
                else STYLES["bullet" if list_depth else "body"]
            )
            if list_depth and not heading:
                counter = numbered[-1]
                prefix = f"{counter}." if counter is not None else "•"
                if counter is not None:
                    numbered[-1] += 1
                text = prefix + " " + text
            story.append(Paragraph(text, style))
        elif kind in {"fence", "code_block"}:
            for line in token.content.splitlines():
                story.append(Paragraph(escape(line) or " ", STYLES["body"]))
        elif kind == "hr":
            story.append(
                HRFlowable(
                    width="100%",
                    thickness=0.5,
                    color=colors.HexColor("#dce3ee"),
                    spaceBefore=10,
                    spaceAfter=10,
                )
            )

    def footer(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 9)
        canvas.setFillColor(MUTED)
        canvas.drawString(48, 28, "Firmly · Review the original sources for context")
        canvas.drawRightString(A4[0] - 48, 28, str(doc.page))
        canvas.restoreState()

    SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=48,
        rightMargin=48,
        topMargin=44,
        bottomMargin=48,
        title="Firmly company research",
        author="Firmly",
    ).build(story, onFirstPage=footer, onLaterPages=footer)


class ReportPDFExporter:
    def export_report(self, markdown_content, company_name=None):
        try:
            buffer = io.BytesIO()
            render_pdf(markdown_content, buffer)
            buffer.seek(0)
            name = (
                re.sub(r"[^a-zA-Z0-9_-]+", "-", company_name or "company").strip("-")[:80]
                or "company"
            )
            return True, (buffer, f"{name.lower()}-report.pdf")
        except Exception:
            return False, "PDF export failed. Your report remains available."
