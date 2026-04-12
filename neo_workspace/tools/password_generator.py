def run_tool(inputs: dict) -> dict:
    import os
    import random
    import string
    import json
    from datetime import datetime
    
    output_dir = inputs.get("output_dir", "/tmp")
    
    try:
        # Parse inputs with defaults
        count = int(inputs.get("count", 10))
        min_length = int(inputs.get("min_length", 10))
        max_length = int(inputs.get("max_length", 20))
        include_special = bool(inputs.get("include_special", True))
        include_numbers = bool(inputs.get("include_numbers", True))
        include_uppercase = bool(inputs.get("include_uppercase", True))
        
        print(f"Generating {count} passwords...")
        print(f"Length range: {min_length}-{max_length} characters")
        print(f"Options: special={include_special}, numbers={include_numbers}, uppercase={include_uppercase}")
        
        # Validate inputs
        if count <= 0:
            return {"ok": False, "output": "", "files": [], "error": "Count must be positive"}
        if min_length <= 0 or max_length <= 0:
            return {"ok": False, "output": "", "files": [], "error": "Length must be positive"}
        if min_length > max_length:
            return {"ok": False, "output": "", "files": [], "error": "min_length cannot be greater than max_length"}
        if max_length < 4:
            return {"ok": False, "output": "", "files": [], "error": "max_length must be at least 4"}
        
        # Define character sets
        lowercase = string.ascii_lowercase
        uppercase = string.ascii_uppercase if include_uppercase else ""
        digits = string.digits if include_numbers else ""
        special = "!@#$%^&*()_+-=[]{}|;:,.<>?" if include_special else ""
        
        # Combine character sets
        all_chars = lowercase + uppercase + digits + special
        
        if not all_chars:
            return {"ok": False, "output": "", "files": [], "error": "At least one character set must be enabled"}
        
        # Ensure we have at least one character from each enabled set
        required_sets = []
        if lowercase:
            required_sets.append(lowercase)
        if uppercase:
            required_sets.append(uppercase)
        if digits:
            required_sets.append(digits)
        if special:
            required_sets.append(special)
        
        passwords = []
        
        for i in range(count):
            # Random length within range
            length = random.randint(min_length, max_length)
            
            # Start with at least one character from each required set
            password_chars = []
            for char_set in required_sets:
                password_chars.append(random.choice(char_set))
            
            # Fill the rest with random characters from all sets
            remaining_length = length - len(password_chars)
            if remaining_length > 0:
                password_chars.extend(random.choices(all_chars, k=remaining_length))
            
            # Shuffle to avoid predictable patterns
            random.shuffle(password_chars)
            
            password = ''.join(password_chars)
            passwords.append(password)
            
            print(f"Password {i+1}: {password}")
        
        # Create output string
        result = f"Generated {count} secure passwords:\n\n"
        for i, password in enumerate(passwords, 1):
            result += f"{i:2d}. {password} (length: {len(password)})\n"
        
        result += f"\nOptions used:\n"
        result += f"- Length range: {min_length}-{max_length} characters\n"
        result += f"- Include uppercase: {include_uppercase}\n"
        result += f"- Include numbers: {include_numbers}\n"
        result += f"- Include special characters: {include_special}\n"
        
        # Create JSON file with passwords
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        json_filename = f"passwords_{timestamp}.json"
        json_path = os.path.join(output_dir, json_filename)
        
        json_data = {
            "generated_at": datetime.now().isoformat(),
            "count": count,
            "min_length": min_length,
            "max_length": max_length,
            "include_special": include_special,
            "include_numbers": include_numbers,
            "include_uppercase": include_uppercase,
            "passwords": passwords
        }
        
        with open(json_path, 'w') as f:
            json.dump(json_data, f, indent=2)
        
        print(f"\nPasswords saved to: {json_path}")
        
        return {
            "ok": True, 
            "output": result, 
            "files": [json_path], 
            "error": ""
        }
        
    except ValueError as e:
        return {"ok": False, "output": "", "files": [], "error": f"Invalid input value: {str(e)}"}
    except Exception as e:
        return {"ok": False, "output": "", "files": [], "error": str(e)}