import os
import random
from datetime import datetime, timedelta

def generate_log_line(log_format):
    """Generate a single log line based on the given format."""
    if log_format == "web_server":
        # Generate a random IP address
        ip_address = ".".join(str(random.randint(0, 255)) for _ in range(4))
        
        # Generate a random date and time
        date = datetime.now() - timedelta(days=random.randint(0, 30))
        date_str = date.strftime("%d/%b/%Y:%H:%M:%S")
        
        # Generate a random request method and URL
        methods = ["GET", "POST", "PUT", "DELETE"]
        method = random.choice(methods)
        url = f"/{random.randint(1, 1000)}"
        
        # Generate a random status code
        status_code = random.randint(200, 500)
        
        # Generate a random user agent
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3",
            "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/51.0.2704.103 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:53.0) Gecko/20100101 Firefox/53.0"
        ]
        user_agent = random.choice(user_agents)
        
        # Generate the log line
        log_line = f"{ip_address} - - [{date_str}] \"{method} {url} HTTP/1.1\" {status_code} - \"{user_agent}\""
        
        return log_line

def analyze_log_file(file_path):
    """Analyze the log file and return the top 5 most frequent IP addresses."""
    ip_addresses = {}
    
    try:
        with open(file_path, "r") as file:
            for line in file:
                ip_address = line.split()[0]
                if ip_address in ip_addresses:
                    ip_addresses[ip_address] += 1
                else:
                    ip_addresses[ip_address] = 1
    except Exception as e:
        print(f"Error analyzing log file: {str(e)}")
        return []
    
    # Get the top 5 most frequent IP addresses
    top_5_ip_addresses = sorted(ip_addresses.items(), key=lambda x: x[1], reverse=True)[:5]
    
    return top_5_ip_addresses

def run_tool(inputs: dict) -> dict:
    import os
    output_dir = inputs.get("output_dir", "/tmp")
    try:
        num_lines = inputs.get("num_lines", 500)
        log_format = inputs.get("log_format", "web_server")
        
        # Generate the log file
        log_file_path = os.path.join(output_dir, "log.txt")
        with open(log_file_path, "w") as file:
            for _ in range(num_lines):
                log_line = generate_log_line(log_format)
                file.write(log_line + "\n")
        
        print("Log file generated successfully.")
        
        # Analyze the log file
        top_5_ip_addresses = analyze_log_file(log_file_path)
        
        # Print the top 5 most frequent IP addresses
        print("Top 5 most frequent IP addresses:")
        for ip_address, count in top_5_ip_addresses:
            print(f"{ip_address}: {count}")
        
        result = "Log file generated and analyzed successfully."
        return {"ok": True, "output": result, "files": [log_file_path], "error": ""}
    except Exception as e:
        return {"ok": False, "output": "", "files": [], "error": str(e)}