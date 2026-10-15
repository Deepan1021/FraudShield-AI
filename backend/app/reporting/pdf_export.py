"""PDF export using reportlab (optional dependency; a clear error is raised if it is missing)."""
from __future__ import annotations

import io
from xml.sax.saxutils import escape

from app.core.errors import ReportError

_REPLACE = {"∧": "AND", "→": "->", "–": "-", "—": "-", "≥": ">=", "≤": "<=", "×": "x"}
RISK_COLORS = {"LOW": "#0F766E", "MEDIUM": "#B45309", "HIGH": "#C2410C", "CRITICAL": "#9F1239"}


def _t(v) -> str:
    s = "-" if v is None else str(v)
    for k, r in _REPLACE.items():
        s = s.replace(k, r)
    return escape(s.encode("latin-1", "replace").decode("latin-1"))


def export_pdf(report: dict) -> bytes:
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib.units import mm
        from reportlab.platypus import KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    except ImportError as exc:
        raise ReportError("PDF export requires the 'reportlab' package (pip install reportlab).") from exc

    styles = getSampleStyleSheet()
    body = ParagraphStyle("body", parent=styles["BodyText"], fontSize=8.5, leading=11)
    cell = ParagraphStyle("cell", parent=body, fontSize=7.5, leading=9.5)
    head = ParagraphStyle("head", parent=cell, textColor=colors.white, fontName="Helvetica-Bold")
    h1 = ParagraphStyle("h1", parent=styles["Title"], fontSize=16, textColor=colors.HexColor("#0E1B2C"), alignment=0)
    h2 = ParagraphStyle("h2", parent=styles["Heading2"], fontSize=11, textColor=colors.HexColor("#0E1B2C"), spaceBefore=10, spaceAfter=4)
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=14 * mm, rightMargin=14 * mm, topMargin=14 * mm, bottomMargin=14 * mm,
                            title=_t(report["title"]), author="FraudShield AI")
    width = A4[0] - 28 * mm
    story = [Paragraph(_t(report["title"]), h1),
             Paragraph(f"Report {_t(report['report_id'])} &nbsp;|&nbsp; Generated {_t(report['generated_at'])} &nbsp;|&nbsp; "
                       f"Risk level: <b><font color='{RISK_COLORS.get(report['risk_level'], '#000000')}'>{_t(report['risk_level'])}</font></b>", body),
             Spacer(1, 4)]

    def table(rows, col_widths, header=True):
        t = Table(rows, colWidths=col_widths, repeatRows=1 if header else 0)
        style = [("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#C7CFD9")), ("VALIGN", (0, 0), (-1, -1), "TOP"),
                 ("LEFTPADDING", (0, 0), (-1, -1), 3), ("RIGHTPADDING", (0, 0), (-1, -1), 3),
                 ("TOPPADDING", (0, 0), (-1, -1), 2), ("BOTTOMPADDING", (0, 0), (-1, -1), 2)]
        if header:
            style += [("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0E1B2C"))]
        t.setStyle(TableStyle(style))
        return t

    for s in report["sections"]:
        block = [Paragraph(_t(s["title"]), h2)]
        d = s["data"]
        if s["type"] == "text":
            block.append(Paragraph(_t(d), body))
        elif s["type"] == "list":
            block += [Paragraph("&bull; " + _t(i), body) for i in d]
        elif s["type"] == "kv":
            rows = [[Paragraph(f"<b>{_t(k)}</b>", cell), Paragraph(_t(", ".join(map(str, v)) if isinstance(v, list) else v), cell)] for k, v in d]
            block.append(table(rows, [width * 0.3, width * 0.7], header=False))
        elif s["type"] == "table":
            n = len(d["columns"])
            weights = [1.0] * n
            weights[-1] = 2.2 if n > 3 else 1.5
            total = sum(weights)
            widths = [width * w / total for w in weights]
            rows = [[Paragraph(_t(c), head) for c in d["columns"]]] + [[Paragraph(_t(c), cell) for c in r] for r in d["rows"]]
            block.append(table(rows, widths))
        story.append(KeepTogether(block[:2]) if len(block) > 2 else block[0])
        story.extend(block[2:] if len(block) > 2 else block[1:])
    doc.build(story)
    return buf.getvalue()
