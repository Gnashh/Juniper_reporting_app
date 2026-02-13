
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

client = Groq(api_key=os.getenv('GROQ_API_KEY'))

def report_summary(report):
    result = report["result"]
    device_serial = get_device_by_id(report['device_id'])['serial_number']
    
    user_prompt = """
Analyze the following router/switch system report.

Return ONLY valid JSON with no extra text.

Use this exact format:

{
  "summary_table": {
    "device": "",
    "model": "",
    "os_version": "",
    "uptime": "",
    "cpu_usage": "",
    "memory_usage": "",
    "temperature": "",
    "power_status": "",
    "alarms": "",
    "overall_status": ""
  },
  "narrative_summary": ""
}

Rules:
- Use only data found in the report
- If a value is missing, use "Not Reported"
- overall_status must be: Healthy, Warning, or Critical
- narrative_summary must be written in Bahasa Indonesia

Report Data:
""" + str(result)
    
    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        temperature=0.2,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a senior Indonesian network engineer and technical report writer. "
                    "(please use bahasa indonesia for the summary)\n\n"
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

    report = get_report_by_id(report_id)

    customer = get_customer_by_id(report["customer_id"])
    device = get_device_by_id(report["device_id"])
    template = get_template_by_id(report["template_id"])

    customer_name = customer["name"]
    device_serial = device["serial_number"]
    template_name = template["name"]
    template_desc = template.get("general_desc") or "No description provided"
    jump_host = customer.get("jump_host_ip") or "Not Reported"
    customer_logo = customer.get("images")

    filename = f"Report_{report_id}_{customer_name}_{template_name}_{device_serial}.pdf"

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
        fontSize=20,
        alignment=1,
        spaceAfter=20
    ))

    styles.add(ParagraphStyle(
        name="HeaderStyle",
        fontSize=14,
        spaceAfter=16,
        textColor=colors.darkblue
    ))

    styles.add(ParagraphStyle(
        name="BodyStyle",
        fontSize=10,
        leading=14,
        spaceAfter=8
    ))

    cli_style = ParagraphStyle(
        name="CLIStyle",
        fontName="Courier",
        fontSize=7,
        leading=8
    )

    story = []

    # ----------------------------
    # COVER PAGE
    # ----------------------------
    from reportlab.lib.utils import ImageReader
    from io import BytesIO

    if customer_logo:
        try:
            # Create temporary file for the logo (don't delete yet)
            tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
            tmp_file.write(customer_logo)
            tmp_file.close()
            tmp_path = tmp_file.name
            
            # Add logo to story
            story.append(Image(tmp_path, width=4 * cm, height=4 * cm))
            story.append(Spacer(1, 20))
            
        except Exception as e:
            # If logo fails, just skip it
            tmp_path = None
            pass
    else:
        tmp_path = None

    story.append(Paragraph(f"Monthly Report for {customer_name}", styles["TitleStyle"]))

    meta_data = [
        ["Customer", customer_name],
        ["Device Serial", device_serial],
        ["Template", template_name[:50] + "..." if len(template_name) > 50 else template_name],
        ["Description",Paragraph(template_desc, styles["BodyStyle"])],
        ["Jump Host", jump_host],
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
    story.append(Paragraph("System Summary (AI Generated)", styles["HeaderStyle"]))

    try:
        summary_json = report_summary(report)
        summary_data = json.loads(summary_json)
        
        # Summary table
        summary_table_data = summary_data.get("summary_table", {})
        table_rows = []
        for key, value in summary_table_data.items():
            # Truncate long values
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
        
    except Exception as e:
        story.append(Paragraph(f"AI Summary unavailable: {str(e)}", styles["BodyStyle"]))

    story.append(PageBreak())

    # ----------------------------
    # COMMAND OUTPUT SECTION
    # ----------------------------
    story.append(Paragraph("Command Outputs", styles["HeaderStyle"]))
    story.append(Spacer(1, 10))

    # Parse results
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

            story.append(Paragraph(
                f"Command {idx}: {result_data.get('command', 'Unknown')}",
                styles["HeaderStyle"]
            ))

            cmd_description = result_data.get("description", "")
            if cmd_description:
                story.append(Paragraph(
                    f"<b>Description:</b> {cmd_description}",
                    styles["BodyStyle"]
                ))

            output = result_data.get("output", "")

            # Wrap long lines to prevent overflow
            max_line_length = 95
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
            
            # Split into chunks if output is too long (max ~80 lines per page)
            lines = wrapped_output.split('\n')
            max_lines_per_page = 80
            
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
                        story.append(Paragraph("<i>(continued...)</i>", styles["BodyStyle"]))
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
