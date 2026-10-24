"""Private, version-specific PDF generation from immutable financial snapshots."""

import io
import json
from decimal import Decimal
from pathlib import Path
from xml.sax.saxutils import escape

import reportlab
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import LongTable, Paragraph, SimpleDocTemplate, Spacer, TableStyle

from app.services.estimates import detail


def render_pdf(db, estimate, version=None):
    data = detail(db, estimate, version)
    doc = data["document"]
    clinic = json.loads(doc["clinic_snapshot"])
    patient = json.loads(doc["patient_snapshot"])
    font = "EstimateFont"
    if font not in pdfmetrics.getRegisteredFontNames():
        candidates = [
            Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
            Path(reportlab.__file__).parent / "fonts/Vera.ttf",
        ]
        pdfmetrics.registerFont(TTFont(font, str(next(p for p in candidates if p.exists()))))
    styles = getSampleStyleSheet()
    for name in ("Normal", "Title", "Heading1", "Heading2"):
        styles[name].fontName = font
    styles["Normal"].fontSize = 9
    styles["Normal"].leading = 13

    def p(value, style="Normal"):
        return Paragraph(escape(str(value or "")).replace("\n", "<br/>"), styles[style])

    out = io.BytesIO()
    story = [
        p(clinic["name"], "Title"),
        p("Treatment estimate " + estimate.number, "Heading1"),
        p(f"Version {doc['version']} · Status {doc['status']} · {doc['currency']}"),
        p("Patient: " + patient["name"]),
    ]
    address = ", ".join(
        str(clinic[k]) for k in ("address", "city", "state", "country") if clinic.get(k)
    )
    if address:
        story.append(p(address))
    story += [
        p(
            "Issued: "
            + str(doc["issue_date"])
            + " · Valid until: "
            + str(doc["valid_until"] or "Not specified")
        ),
        Spacer(1, 16),
    ]
    rows = [[p(h) for h in ["Treatment", "Qty", "Unit price", "Discount", "Tax", "Line total"]]]
    precision = int(doc["minor_units"])

    def money(v):
        return f"{Decimal(v):.{precision}f}"

    for item in data["items"]:
        rows.append(
            [
                p(item["description"]),
                p(format(Decimal(item["quantity"]).normalize(), "f")),
                p(money(item["unit_price"])),
                p(money(item["discount"])),
                p(money(item["tax"])),
                p(money(item["total"])),
            ]
        )
    table = LongTable(rows, colWidths=[195, 50, 65, 55, 50, 65], repeatRows=1, splitInRow=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e5f3f6")),
                ("GRID", (0, 0), (-1, -1), 0.3, colors.lightgrey),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    story += [table, Spacer(1, 16)]
    for title, key in [
        ("Subtotal", "subtotal"),
        ("Discount", "discount"),
        ("Tax", "tax"),
        ("Total", "total"),
    ]:
        story.append(
            p(
                f'{title}: {money(doc[key])} {doc["currency"]}',
                "Heading2" if key == "total" else "Normal",
            )
        )
    if doc["terms"]:
        story += [Spacer(1, 12), p("Clinic terms", "Heading2"), p(doc["terms"])]
    if data["acknowledgement"]:
        a = data["acknowledgement"]
        story += [
            Spacer(1, 12),
            p(
                f"Administrative acknowledgement: {a['decision']} · {a['acknowledged_by_name']} · {a['method']}. This document is not an electronic signature."
            ),
        ]

    def footer(c, d):
        c.setFont(font, 8)
        c.drawString(32, 20, f'{estimate.number} · v{doc["version"]} · page {d.page}')

    SimpleDocTemplate(
        out, leftMargin=28, rightMargin=28, topMargin=28, bottomMargin=36, title=estimate.number
    ).build(story, onFirstPage=footer, onLaterPages=footer)
    return out.getvalue()
