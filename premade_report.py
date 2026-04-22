from db.templates import get_template_by_id

def create_premade_report(device_id, customer_id, template_id, premade_report_file):
    file_content = premade_report_file.read().decode('utf-8', errors='replace')

    template = get_template_by_id(template_id)
    
    # Extract outputs for found commands
    all_results = []
    
    for item in template["command"]:
        if item.get("type") == "Header":
            all_results.append({
                "type": "Header",
                "text": item.get("text", ""),
                "status": "success",
            })
            continue
        
        command = item.get("command", "")
        description = item.get("description", "")
        
        if not command:
            continue
        
        # Search for command in file content
        if command in file_content:
            # Extract output between this command and next command/prompt
            cmd_index = file_content.find(command)
            
            # Find where output ends (next command or CLI prompt)
            output_start = cmd_index + len(command)
            
            # Look for next command or common CLI prompts
            next_markers = ["\n" + cmd for cmd in [c.get("command", "") for c in template["command"] if c.get("command")]]
            next_markers.extend(["\nuser@", "\nroot@", "\n>", "\n#"])
            
            output_end = len(file_content)
            for marker in next_markers:
                marker_pos = file_content.find(marker, output_start)
                if marker_pos != -1 and marker_pos < output_end:
                    output_end = marker_pos
            
            output = file_content[output_start:output_end].strip()
            
            all_results.append({
                "type": "Command",
                "command": command,
                "description": description,
                "output": output,
                "status": "success",
            })
    
    return all_results
