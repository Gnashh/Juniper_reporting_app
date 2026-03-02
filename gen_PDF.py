"""
PDF Report Generator
===================
Generates professional PDF reports from stored report data.
Uses Groq/LLM for AI-generated summary and ReportLab for PDF layout.
"""

from db.devices import get_device_by_id
from db.customer import get_customer_by_id
from db.templates import get_template_by_id
from db.reports import get_report_by_id
from datetime import datetime
from groq import Groq
import tempfile
import os
import json
from dotenv import load_dotenv
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table,
    TableStyle, PageBreak, Image, Preformatted, KeepTogether
)
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics

# Load environment variables
load_dotenv()

# Groq client for AI summarization (uses GROQ_API_KEY from .env)
client = Groq(api_key=os.getenv('GROQ_API_KEY'))


def AI_report_summary(report):
    """Use Groq LLM to analyze report data and return structured JSON summary."""
    result = report["result"]

    user_prompt = """
Analyze the following router/switch system report.

Return ONLY valid JSON with no extra text.

Use this exact format:

{
  "summary_table": {
    "Device": "",
    "Model": "",
    "OS_version": "",
    "Uptime": "",
    "CPU_usage": "",
    "Memory_usage": "",
    "Temperature": "",
    "Power_status": "",
    "Alarms": "",
    "Overall_status": ""
  },
  "narrative_summary": ""
}

Rules:
- Use only data found in the report
- If a value is missing, use "Not Reported"
- Overall_status must be: Healthy, Warning, or Critical

Report Data:
""" + str(result)

    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        temperature=0.2,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a senior network engineer and technical report writer. \n"
                    "Your task is to analyze raw router/switch system reports and produce:\n"
                    "1) A simple summary table\n"
                    "2) A professional narrative explanation\n\n"
                    "Rules:\n"
                    "- Base your analysis ONLY on the provided data\n"
                    "- Do NOT assume or invent missing values\n"
                    "- If data is missing, return 'Not Reported'\n"
                    "- Keep the table simple and consistent\n"
                    "- Use professional networking terminology\n"
                    "- Ensure the narrative is clear and structured"
                )
            },
            {
                "role": "user",
                "content": user_prompt
            }
        ]
    )

    return response.choices[0].message.content


def _cli_table(text, cli_style, top_border=True, bottom_border=True):
    """
    Wrap a Preformatted CLI block in a styled Table that has a grey background.

    By creating one small Table per batch (instead of one giant Table for all
    output), each table is short enough for ReportLab to push to the next page
    individually — giving us the background colour without the gap problem.

    top_border / bottom_border control whether to draw the outer grey border on
    that edge, so consecutive batches look like one seamless block.
    """
    tbl = Table(
        [[Preformatted(text, cli_style)]],
        colWidths=[16 * cm],
    )

    # Build border commands selectively so batches appear continuous
    cmds = [
        ("BACKGROUND",    (0, 0), (-1, -1), colors.whitesmoke),
        ("LEFTPADDING",   (0, 0), (-1, -1), 6),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 6),
        ("TOPPADDING",    (0, 0), (-1, -1), 4 if top_border else 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4 if bottom_border else 0),
        ("VALIGN",        (0, 0), (-1, -1), "TOP"),
        # Always draw left/right borders
        ("LINEABOVE",    (0, 0), (-1, 0),  0.5, colors.grey) if top_border    else ("NOSPLIT", (0, 0), (-1, -1)),
        ("LINEBELOW",    (0, -1), (-1, -1), 0.5, colors.grey) if bottom_border else ("NOSPLIT", (0, 0), (-1, -1)),
        ("LINEBEFORE",   (0, 0), (0, -1),  0.5, colors.grey),
        ("LINEAFTER",    (-1, 0), (-1, -1), 0.5, colors.grey),
    ]

    tbl.setStyle(TableStyle(cmds))
    return tbl


def generate_pdf(report_id):
    """
    Generate a PDF report: cover page, AI summary, and command outputs.
    Returns the path to the generated PDF file.
    """
    report = get_report_by_id(report_id)
    customer = get_customer_by_id(report["customer_id"])
    device = get_device_by_id(report["device_id"])
    template = get_template_by_id(report["template_id"])

    customer_name = customer["name"]
    template_name = template["name"]
    device_serial = device["serial_number"]
    device_username = device["username"]
    template_desc = template.get("general_desc") or "No description provided"
    customer_logo = customer.get("images")

    filename = f"Report_{template_name}_{device_serial}.pdf"

    # ----------------------------
    # DOCUMENT SETUP
    # ----------------------------
    doc = SimpleDocTemplate(
        filename,
        pagesize=A4,
        rightMargin=2 * cm,
        leftMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm
    )

    styles = getSampleStyleSheet()

    styles.add(ParagraphStyle(
        name="TitleStyle",
        fontSize=22,
        alignment=1,
        spaceAfter=25
    ))

    styles.add(ParagraphStyle(
        name="HeaderStyle",
        fontSize=15,
        spaceAfter=18,
        textColor=colors.darkblue
    ))

    styles.add(ParagraphStyle(
        name="BodyStyle",
        fontSize=11,
        leading=15,
        spaceAfter=10
    ))

    cli_style = ParagraphStyle(
        name="CLIStyle",
        fontName="Courier",
        fontSize=8,
        leading=9,
        spaceBefore=0,
        spaceAfter=0,
    )

    story = []

    # ----------------------------
    # COVER PAGE
    # ----------------------------
    from reportlab.lib.utils import ImageReader
    from io import BytesIO

    host_logo_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'IMG', 'ipnetcropped.jpg')

    if customer_logo:
        try:
            tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
            tmp_file.write(customer_logo)
            tmp_file.close()
            tmp_path = tmp_file.name
        except Exception:
            tmp_path = None
    else:
        tmp_path = None

    left_cell  = Image(tmp_path, width=3 * cm, height=3 * cm) if tmp_path else Paragraph("", styles["BodyStyle"])
    right_cell = Image(host_logo_path, width=10 * cm, height=4 * cm) if os.path.exists(host_logo_path) else Paragraph("", styles["BodyStyle"])

    logo_table = Table([[left_cell, right_cell]], colWidths=[8.5 * cm, 8.5 * cm])
    logo_table.setStyle(TableStyle([
        ("ALIGN",         (0, 0), (0, 0),   "LEFT"),
        ("ALIGN",         (1, 0), (1, 0),   "RIGHT"),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING",   (0, 0), (-1, -1), 0),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 0),
        ("TOPPADDING",    (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    story.append(logo_table)
    story.append(Spacer(1, 100))
    story.append(Paragraph(f"{template_name}", styles["TitleStyle"]))
    story.append(Spacer(1, 30))

    meta_data = [
        ["Customer",        customer_name],
        ["Device Serial",   device_serial],
        ["Device Hostname", device_username],
        ["Description",     Paragraph(template_desc, styles["BodyStyle"])],
        ["Generated",       datetime.now().strftime("%Y-%m-%d %H:%M:%S")]
    ]

    meta_table = Table(meta_data, colWidths=[4 * cm, 12 * cm])
    meta_table.setStyle(TableStyle([
        ("GRID",          (0, 0), (-1, -1), 0.5, colors.grey),
        ("BACKGROUND",    (0, 0), (0, -1),  colors.whitesmoke),
        ("VALIGN",        (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING",   (0, 0), (-1, -1), 6),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 6),
        ("TOPPADDING",    (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("FONTSIZE",      (0, 0), (-1, -1), 9),
    ]))

    story.append(meta_table)
    story.append(PageBreak())

    # ----------------------------
    # AI SUMMARY SECTION
    # ----------------------------
    if report.get("aisummary") == 1 and report.get("result"):
        try:
            story.append(Paragraph("System Summary", styles["HeaderStyle"]))
            summary_json = AI_report_summary(report)

            if summary_json and summary_json.strip():
                summary_data = json.loads(summary_json)

                table_rows = []
                for key, value in summary_data.get("summary_table", {}).items():
                    value_str = str(value)
                    if len(value_str) > 60:
                        value_str = value_str[:60] + "..."
                    table_rows.append([key.replace('_', ' ').title(), value_str])

                if table_rows:
                    summary_table = Table(table_rows, colWidths=[6 * cm, 10 * cm])
                    summary_table.setStyle(TableStyle([
                        ("GRID",          (0, 0), (-1, -1), 0.7, colors.black),
                        ("BACKGROUND",    (0, 0), (0, -1),  colors.lightgrey),
                        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
                        ("LEFTPADDING",   (0, 0), (-1, -1), 6),
                        ("RIGHTPADDING",  (0, 0), (-1, -1), 6),
                        ("TOPPADDING",    (0, 0), (-1, -1), 6),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                        ("FONTSIZE",      (0, 0), (-1, -1), 9),
                    ]))
                    story.append(summary_table)
                    story.append(Spacer(1, 15))

                narrative = summary_data.get("narrative_summary", "")
                if narrative:
                    story.append(Paragraph("<b>Summary:</b>", styles["BodyStyle"]))
                    for para in narrative.split("\n\n"):
                        if para.strip():
                            story.append(Paragraph(para.replace("\n", "<br/>"), styles["BodyStyle"]))

                story.append(PageBreak())

        except (json.JSONDecodeError, Exception):
            pass

    # ----------------------------
    # MANUAL SUMMARY SECTION
    # ----------------------------
    if template.get("manual_summary_desc"):
        story.append(Paragraph("Manual Summary", styles["HeaderStyle"]))
        manual_table_data = template.get("manual_summary_table")
        if isinstance(manual_table_data, str):
            try:
                manual_table_data = json.loads(manual_table_data)
            except json.JSONDecodeError:
                manual_table_data = []

        if manual_table_data and isinstance(manual_table_data, list):
            table_rows = []
            for item in manual_table_data:
                if isinstance(item, dict):
                    field = item.get("field", "")
                    value = item.get("value", "")
                    if field:
                        table_rows.append([field, value])

            if table_rows:
                summary_table = Table(table_rows, colWidths=[6 * cm, 10 * cm])
                summary_table.setStyle(TableStyle([
                    ("GRID",          (0, 0), (-1, -1), 0.7, colors.black),
                    ("BACKGROUND",    (0, 0), (0, -1),  colors.lightgrey),
                    ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
                    ("LEFTPADDING",   (0, 0), (-1, -1), 6),
                    ("RIGHTPADDING",  (0, 0), (-1, -1), 6),
                    ("TOPPADDING",    (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                    ("FONTSIZE",      (0, 0), (-1, -1), 9),
                ]))
                story.append(summary_table)

        story.append(Spacer(1, 15))
        story.append(Paragraph(template["manual_summary_desc"], styles["BodyStyle"]))
        story.append(Spacer(1, 15))
        story.append(PageBreak())

    # ----------------------------
    # COMMAND OUTPUT SECTION
    # ----------------------------
    results = report["result"]

    if isinstance(results, str):
        try:
            results = json.loads(results)
        except json.JSONDecodeError:
            results = []

    if not isinstance(results, list):
        results = []

    if not results:
        story.append(Paragraph("No command results found.", styles["BodyStyle"]))
    else:
        command_entries = [r for r in results if isinstance(r, dict) and r.get("type") != "Header"]
        command_count   = len(command_entries)
        command_idx     = 0

        for result_data in results:
            if not isinstance(result_data, dict):
                continue

            # ── HEADER ────────────────────────────────────────────────────
            if result_data.get("type") == "Header":
                if story and not isinstance(story[-1], PageBreak):
                    story.append(PageBreak())
                story.append(Paragraph(result_data.get("text", ""), styles["HeaderStyle"]))
                story.append(Spacer(1, 10))
                continue

            # ── COMMAND ENTRY ──────────────────────────────────────────────
            command_idx += 1

            cmd_description = result_data.get("description", "")
            output          = result_data.get("output", "")

            # Wrap long lines so nothing overflows the page width
            max_line_length = 90
            wrapped_lines = []
            for line in output.split('\n'):
                while len(line) > max_line_length:
                    wrapped_lines.append(line[:max_line_length])
                    line = line[max_line_length:]
                wrapped_lines.append(line)

            # ------------------------------------------------------------------
            # Split output into small batches (BATCH lines each).
            # Each batch becomes its own small Table with grey background.
            # Small tables can be pushed to the next page individually, so
            # ReportLab never needs to leave a big blank gap.
            #
            # Consecutive batch-tables share borders so they look like one
            # continuous block: the first gets a top border, the last gets a
            # bottom border, middle ones get neither top nor bottom border.
            # ------------------------------------------------------------------
            BATCH = 70  # lines per table — small enough to fit partial pages

            batches = []
            for i in range(0, len(wrapped_lines), BATCH):
                batches.append('\n'.join(wrapped_lines[i:i + BATCH]))

            n = len(batches)

            # Build the CLI table flowables
            cli_flowables = []
            for i, batch_text in enumerate(batches):
                is_first = (i == 0)
                is_last  = (i == n - 1)
                cli_flowables.append(
                    _cli_table(batch_text, cli_style,
                               top_border=is_first,
                               bottom_border=is_last)
                )

            # Keep description label + first batch together (anti-orphan).
            # The remaining batches are added directly to the story so they
            # can flow freely across page boundaries.
            if cmd_description:
                desc_para = Paragraph(f"<b>Description:</b> {cmd_description}", styles["BodyStyle"])
                if cli_flowables:
                    story.append(KeepTogether([desc_para, cli_flowables[0]]))
                    for tbl in cli_flowables[1:]:
                        story.append(tbl)
                else:
                    story.append(desc_para)
            else:
                for tbl in cli_flowables:
                    story.append(tbl)

            # Page break between commands, not after the last one
            if command_idx < command_count:
                story.append(PageBreak())

    # ----------------------------
    # BUILD PDF
    # ----------------------------
    doc.build(story)

    # Clean up temp logo file
    if customer_logo and tmp_path and os.path.exists(tmp_path):
        try:
            os.unlink(tmp_path)
        except Exception:
            pass

    return filename
