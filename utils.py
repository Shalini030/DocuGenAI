from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch
from reportlab.lib import colors
import os
import re


def generate_pdf(content: str, filename: str) -> str:
    """Convert markdown-like content to a styled PDF."""

    os.makedirs("outputs", exist_ok=True)
    file_path = os.path.join("outputs", filename)

    doc = SimpleDocTemplate(
        file_path,
        pagesize=A4,
        rightMargin=0.8 * inch,
        leftMargin=0.8 * inch,
        topMargin=1 * inch,
        bottomMargin=1 * inch,
    )

    styles = getSampleStyleSheet()

    # Custom styles
    h1_style = ParagraphStyle(
        "H1", parent=styles["Heading1"],
        fontSize=18, spaceAfter=12, textColor=colors.HexColor("#1a1a2e")
    )
    h2_style = ParagraphStyle(
        "H2", parent=styles["Heading2"],
        fontSize=14, spaceAfter=8, textColor=colors.HexColor("#16213e")
    )
    h3_style = ParagraphStyle(
        "H3", parent=styles["Heading3"],
        fontSize=12, spaceAfter=6, textColor=colors.HexColor("#0f3460")
    )
    body_style = ParagraphStyle(
        "Body", parent=styles["Normal"],
        fontSize=10, spaceAfter=4, leading=14
    )
    code_style = ParagraphStyle(
        "Code", parent=styles["Code"],
        fontSize=8.5, backColor=colors.HexColor("#f4f4f4"),
        leftIndent=12, spaceAfter=6, leading=13,
        fontName="Courier"
    )
    bullet_style = ParagraphStyle(
        "Bullet", parent=styles["Normal"],
        fontSize=10, leftIndent=16, spaceAfter=3,
        bulletIndent=6, leading=13
    )

    story = []
    lines = content.split("\n")
    in_code_block = False
    code_buffer = []

    def flush_code():
        if code_buffer:
            for cl in code_buffer:
                safe = cl.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                story.append(Paragraph(safe or " ", code_style))
            story.append(Spacer(1, 6))
            code_buffer.clear()

    for line in lines:
        # Code block toggle
        if line.startswith("```"):
            if in_code_block:
                flush_code()
                in_code_block = False
            else:
                in_code_block = True
            continue

        if in_code_block:
            code_buffer.append(line)
            continue

        # Strip inline code backticks for PDF (replace with plain text)
        line = re.sub(r"`([^`]+)`", r"\1", line)
        # Strip bold/italic markers
        line = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", line)
        line = re.sub(r"\*(.+?)\*", r"<i>\1</i>", line)

        safe_line = line  # already processed above

        if line.startswith("# "):
            story.append(Spacer(1, 10))
            story.append(Paragraph(safe_line[2:], h1_style))
            story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#ccc")))
            story.append(Spacer(1, 4))

        elif line.startswith("## "):
            story.append(Spacer(1, 8))
            story.append(Paragraph(safe_line[3:], h2_style))
            story.append(Spacer(1, 2))

        elif line.startswith("### "):
            story.append(Spacer(1, 6))
            story.append(Paragraph(safe_line[4:], h3_style))

        elif line.startswith("- ") or line.startswith("* "):
            story.append(Paragraph(f"• {safe_line[2:]}", bullet_style))

        elif re.match(r"^\d+\. ", line):
            story.append(Paragraph(safe_line, bullet_style))

        elif line.strip() == "":
            story.append(Spacer(1, 6))

        else:
            story.append(Paragraph(safe_line, body_style))

    # Flush any remaining code
    flush_code()

    doc.build(story)
    return file_path