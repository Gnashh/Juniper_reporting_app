from fpdf import FPDF
from db.devices import get_device_by_id
from db.customer import get_customer_by_id
from db.templates import get_template_by_id
from db.reports import get_report_by_id
from datetime import datetime
from io import BytesIO
import tempfile
import os

def generate_pdf(report_id):
    report = get_report_by_id(report_id)

    customer_name = get_customer_by_id(report["customer_id"])["name"]
    template_name = get_template_by_id(report["template_id"])["name"]
    device_serial = get_device_by_id(report['device_id'])['serial_number']
    jump_host = get_customer_by_id(report['customer_id'])['jump_host_ip'] or None
    customer_logo = get_customer_by_id(report['customer_id'])['images'] or None

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15) # This sets the automatic page break to True and sets the margin to 15. This means that the PDF will automatically create a new page when the content exceeds the page size.
    
    # Cover page
    pdf.add_page()
    
    # Handle customer logo if exists
    if customer_logo:
        # Create temporary file for customer logo
        with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as tmp_file:
            tmp_file.write(customer_logo)
            tmp_logo_path = tmp_file.name
        
        try:
            pdf.image(tmp_logo_path, x=12.5, y=10, w=50, h=50)
        finally:
            os.unlink(tmp_logo_path)  # Delete temp file
    
    pdf.image('Juniper_reporting_app\IMG\ipnetcropped.jpg', x=125, y=15, w=80, h=20) # Logo image, x and y coordinates are for centering the image on the page, w and h are for resizing the image.
    pdf.set_font("Courier", 'B', size=20) # Title font size
    pdf.ln(100) # Line spacing, this is for adjusting the vertical position of the title.
    pdf.cell(0, 10, f"Monthly Report for {customer_name}", ln=True, align='C') # Title, ln=True means that the text will be centered on the page.
    pdf.ln(10) # Line spacing
    
    pdf.set_font("Courier", size=12)
    pdf.cell(0, 8, f"Customer: {customer_name}", ln=True, align='C')
    if jump_host:
        pdf.cell(0, 8, f"Jump Host: {jump_host}", ln=True, align='C')
    pdf.cell(0, 8, f"Device: {device_serial}", ln=True, align='C')
    pdf.cell(0, 8, f"Template: {template_name}", ln=True, align='C')
    pdf.ln(15)
    pdf.set_font("Courier", size=10)
    pdf.cell(0, 6, f"Generated: {datetime.now()}", ln=True, align='C') # This is the date and time that the report was generated.
    
    # Split by separator and process each command
    commands = report["result"].split("=" * 80)
    
    for command_output in commands:
        command_output = command_output.strip()
        if not command_output:
            continue
        
        # New page for each command
        pdf.add_page()
        
        # Parse command line
        lines = command_output.split('\n', 1)
        command_name = lines[0].replace("Command:", "").strip() if lines else "Unknown Command"
        output = lines[1].strip() if len(lines) > 1 else ""
        
        # Command header with background
        pdf.set_fill_color(230, 230, 230)
        pdf.set_font("Courier", 'B', size=11)
        pdf.cell(0, 8, f"Command: {command_name}", ln=True, fill=True)
        pdf.ln(3)
        
        # Command output
        pdf.set_font("Courier", size=8)
        if output:
            pdf.multi_cell(w=0, h=4, txt=output, border=1)
        else:
            pdf.set_text_color(128, 128, 128)
            pdf.cell(0, 6, "(No output)", ln=True)
            pdf.set_text_color(0, 0, 0)
    
    filename = f"Report_{report_id}_{customer_name}_{template_name}_{device_serial}.pdf" # This is the file name that will be generated. It includes the report ID, customer name, template name, and device serial number.
    pdf.output(filename, "F") # This will save the PDF to the file system.
    return filename
