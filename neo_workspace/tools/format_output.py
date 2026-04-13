def run_tool(inputs: dict) -> dict:
    import os
    import re
    output_dir = inputs.get("output_dir", "/tmp")
    
    try:
        # Get inputs
        data = inputs.get("data", "")
        format_type = inputs.get("format_type", "numbered_list")
        title = inputs.get("title", "Generated Passwords")
        dep_1_output = inputs.get("dep_1_output", "")
        
        print(f"Starting format_output tool...")
        print(f"Format type: {format_type}")
        print(f"Title: {title}")
        
        # Use either data or dep_1_output as source
        source_text = dep_1_output if dep_1_output else data
        
        if not source_text:
            return {"ok": False, "output": "", "files": [], 
                   "error": "No input data provided"}
        
        print("Parsing input data...")
        
        # Extract passwords from the input text
        passwords = []
        options_info = []
        
        # Look for password lines (lines with numbers and passwords)
        lines = source_text.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            # Match patterns like "1. password (length: XX)" or "1. password"
            match = re.match(r'^\s*\d+\.\s+(.+?)(?:\s*\(length:\s*\d+\))?$', line)
            if match:
                password = match.group(1).strip()
                if password:
                    passwords.append(password)
            
            # Collect options/configuration information
            if line.startswith('- ') or ':' in line and 'length' not in line.lower():
                options_info.append(line)
        
        print(f"Found {len(passwords)} passwords")
        
        # Format based on format_type
        result = ""
        
        if format_type == "numbered_list":
            result += f"# {title}\n\n"
            for i, pwd in enumerate(passwords, 1):
                result += f"{i:2d}. {pwd} (length: {len(pwd)})\n"
        
        elif format_type == "bulleted_list":
            result += f"# {title}\n\n"
            for pwd in passwords:
                result += f"• {pwd} (length: {len(pwd)})\n"
        
        elif format_type == "table":
            result += f"# {title}\n\n"
            result += "| # | Password | Length |\n"
            result += "|---|----------|--------|\n"
            for i, pwd in enumerate(passwords, 1):
                result += f"| {i} | `{pwd}` | {len(pwd)} |\n"
        
        elif format_type == "simple":
            result += f"{title}:\n\n"
            for pwd in passwords:
                result += f"{pwd}\n"
        
        elif format_type == "json":
            import json
            data_dict = {
                "title": title,
                "passwords": passwords,
                "count": len(passwords),
                "passwords_with_length": [{"password": pwd, "length": len(pwd)} for pwd in passwords]
            }
            if options_info:
                data_dict["options"] = options_info
            result = json.dumps(data_dict, indent=2)
        
        elif format_type == "csv":
            result = f"# {title}\n\n"
            result += "Number,Password,Length\n"
            for i, pwd in enumerate(passwords, 1):
                # Escape quotes in password for CSV
                escaped_pwd = pwd.replace('"', '""')
                result += f'{i},"{escaped_pwd}",{len(pwd)}\n'
        
        else:
            # Default to numbered_list
            result += f"# {title}\n\n"
            for i, pwd in enumerate(passwords, 1):
                result += f"{i:2d}. {pwd} (length: {len(pwd)})\n"
        
        # Add options information if available
        if options_info and format_type not in ["json", "csv"]:
            result += "\n---\n\n"
            result += "Options used:\n"
            for option in options_info:
                result += f"{option}\n"
        
        # Save to file if requested
        files = []
        if output_dir and os.path.exists(output_dir):
            filename = f"formatted_passwords_{format_type}.txt"
            filepath = os.path.join(output_dir, filename)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(result)
            files.append(filepath)
            print(f"Saved formatted output to: {filepath}")
        
        print(f"Formatting complete. Generated {len(passwords)} passwords in {format_type} format.")
        
        return {"ok": True, "output": result, "files": files, "error": ""}
        
    except Exception as e:
        error_msg = f"Error in format_output: {str(e)}"
        print(error_msg)
        return {"ok": False, "output": "", "files": [], "error": error_msg}