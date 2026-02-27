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
    TableStyle, PageBreak, Image, Preformatted, Paragraph
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
    device_serial = device["serial_number"]
    device_username = device["username"]
    template_desc = template.get("general_desc") or "No description provided"
    customer_logo = customer.get("images")

    filename = f"Report_{report_id}_{customer_name}_{device_serial}.pdf"

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
        leading=9
    )

    story = []

    # ----------------------------
    # COVER PAGE
    # ----------------------------
    from reportlab.lib.utils import ImageReader
    from io import BytesIO

    host_logo_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'IMG', 'ipnetcropped.jpg')

    # Write customer logo to a temp file
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

    # Build logo row: customer logo LEFT, host logo RIGHT
    left_cell = Image(tmp_path, width=3 * cm, height=3 * cm) if tmp_path else Paragraph("", styles["BodyStyle"])
    right_cell = Image(host_logo_path, width=10 * cm, height=4 * cm) if os.path.exists(host_logo_path) else Paragraph("", styles["BodyStyle"])

    logo_table = Table(
        [[left_cell, right_cell]],
        colWidths=[8.5 * cm, 8.5 * cm]
    )
    logo_table.setStyle(TableStyle([
        ("ALIGN",         (0, 0), (0, 0), "LEFT"),
        ("ALIGN",         (1, 0), (1, 0), "RIGHT"),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING",   (0, 0), (-1, -1), 0),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 0),
        ("TOPPADDING",    (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    story.append(logo_table)
    story.append(Spacer(1, 100))

    story.append(Paragraph(f"Monthly Report for {customer_name}", styles["TitleStyle"]))
    story.append(Spacer(1, 30))

    meta_data = [
        ["Customer", customer_name],
        ["Device Serial", device_serial],
        ["Device Hostname", device_username],
        ["Description",Paragraph(template_desc, styles["BodyStyle"])],
        ["Generated", datetime.now().strftime("%Y-%m-%d %H:%M:%S")]
    ]

    meta_table = Table(meta_data, colWidths=[4 * cm, 12 * cm])

    meta_table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("BACKGROUND", (0, 0), (0, -1), colors.whitesmoke),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
    ]))

    story.append(meta_table)
    story.append(PageBreak())

    # ----------------------------
    # AI SUMMARY SECTION
    # ----------------------------

    # Check if AI summary is enabled AND results exist (not empty)
    if report.get("aisummary") == 1 and report.get("result"):
        try:
            story.append(Paragraph("System Summary", styles["HeaderStyle"]))
            summary_json = AI_report_summary(report)
            
            # Validate JSON response
            if summary_json and summary_json.strip():
                summary_data = json.loads(summary_json)
                
                # Summary table
                summary_table_data = summary_data.get("summary_table", {})
                table_rows = []
                for key, value in summary_table_data.items():
                    value_str = str(value)
                    if len(value_str) > 60:
                        value_str = value_str[:60] + "..."
                    table_rows.append([key.replace('_', ' ').title(), value_str])
                
                if table_rows:
                    summary_table = Table(table_rows, colWidths=[6 * cm, 10 * cm])
                    summary_table.setStyle(TableStyle([
                        ("GRID", (0, 0), (-1, -1), 0.7, colors.black),
                        ("BACKGROUND", (0, 0), (0, -1), colors.lightgrey),
                        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                        ("LEFTPADDING", (0, 0), (-1, -1), 6),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                        ("TOPPADDING", (0, 0), (-1, -1), 6),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                        ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ]))
                    story.append(summary_table)
                    story.append(Spacer(1, 15))
                
                # Narrative summary
                narrative = summary_data.get("narrative_summary", "")
                if narrative:
                    story.append(Paragraph("<b>Narrative Summary:</b>", styles["BodyStyle"]))
                    for para in narrative.split("\n\n"):
                        if para.strip():
                            story.append(Paragraph(para.replace("\n", "<br/>"), styles["BodyStyle"]))
                
                story.append(PageBreak())
            else:
                # Skip AI summary section entirely - no page break
                pass
                
        except json.JSONDecodeError as e:
            # Skip AI summary section - no error message, no page break
            pass
        except Exception as e:
            # Skip AI summary section - no error message, no page break
            pass

    else:
        # AI summary not enabled - skip section entirely, no page break
        pass

    # ----------------------------
    # COMMAND OUTPUT SECTION
    # ----------------------------

    # Parse command results; handle both JSON string (from DB) and list
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
        for idx, result_data in enumerate(results, 1):
            if not isinstance(result_data, dict):
                continue
            
            # Check if it's a header
            if result_data.get("type") == "Header":
                story.append(Spacer(1, 20))
                story.append(Paragraph(
                    result_data.get("text", ""),
                    styles["HeaderStyle"]
                ))
                story.append(Spacer(1, 10))
                continue

            cmd_description = result_data.get("description", "")
            if cmd_description:
                story.append(Paragraph(
                    f"<b>Description:</b> {cmd_description}",
                    styles["BodyStyle"]
                ))

            output = result_data.get("output", "")

            # Wrap long lines to prevent PDF overflow
            max_line_length = 90
            wrapped_lines = []
            for line in output.split('\n'):
                if len(line) > max_line_length:
                    # Break long lines
                    while len(line) > max_line_length:
                        wrapped_lines.append(line[:max_line_length])
                        line = line[max_line_length:]
                    if line:
                        wrapped_lines.append(line)
                else:
                    wrapped_lines.append(line)
            
            wrapped_output = '\n'.join(wrapped_lines)
            
            # Paginate: split output into chunks to fit ~75 lines per page
            lines = wrapped_output.split('\n')
            max_lines_per_page = 75
            
            if len(lines) > max_lines_per_page:
                # Split into multiple chunks
                for i in range(0, len(lines), max_lines_per_page):
                    chunk = '\n'.join(lines[i:i + max_lines_per_page])
                    cli_block = Preformatted(chunk, cli_style)
                    
                    story.append(Table(
                        [[cli_block]],
                        colWidths=[16 * cm],
                        style=[
                            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                            ("BACKGROUND", (0, 0), (-1, -1), colors.whitesmoke),
                            ("LEFTPADDING", (0, 0), (-1, -1), 6),
                            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                            ("TOPPADDING", (0, 0), (-1, -1), 6),
                            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                            ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ]
                    ))
                    
                    # Add page break between chunks (except last one)
                    if i + max_lines_per_page < len(lines):
                        story.append(PageBreak())
            else:
                # Output fits on one page
                cli_block = Preformatted(wrapped_output, cli_style)
                
                story.append(Table(
                    [[cli_block]],
                    colWidths=[16 * cm],
                    style=[
                        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                        ("BACKGROUND", (0, 0), (-1, -1), colors.whitesmoke),
                        ("LEFTPADDING", (0, 0), (-1, -1), 6),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                        ("TOPPADDING", (0, 0), (-1, -1), 6),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ]
                ))

            story.append(PageBreak())

    # ----------------------------
    # BUILD PDF
    # ----------------------------
    doc.build(story)
    
    # Clean up temp logo file if it exists
    if customer_logo and tmp_path and os.path.exists(tmp_path):
        try:
            os.unlink(tmp_path)
        except:
            pass

    return filename
