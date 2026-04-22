import re
from db.templates import get_template_by_id

def create_premade_report(device_id, customer_id, template_id, premade_report_file):
    # Read and clean
    file_content = premade_report_file.read().decode('utf-8', errors='replace')
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    file_content = ansi_escape.sub('', file_content)
    file_content = file_content.replace('\r', '')
    file_content = re.sub(r'[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F]', '', file_content)

    template = get_template_by_id(template_id)
    all_results = []
    
    # Process template commands IN ORDER
    for item in template["command"]:
        if item.get("type") == "Header":
            all_results.append({
                "type": "Header",
                "text": item.get("text", ""),
                "status": "success",
            })
            continue
        
        cmd = item.get("command", "").strip()
        description = item.get("description", "")
        
        if not cmd:
            continue
        
        # Search for this command in the log file
        # Pattern: command appears after a prompt, optionally followed by | pipes
        # Example: "user@host> show system uptime | no-more"
        pattern = rf'[\w\-\.@]+\s*[>#]\s*{re.escape(cmd)}(?:\s*\|[^\n]*)?\s*\n(.*?)(?=[\w\-\.@]+\s*[>#]|$)'
        match = re.search(pattern, file_content, re.DOTALL)
        
        if match:
            output = match.group(1).strip()
            all_results.append({
                "type": "Command",
                "command": cmd,
                "description": description,
                "output": output,
                "status": "success",
            })
        # If command not found in log, skip it (don't add to results)
    
    return all_results
