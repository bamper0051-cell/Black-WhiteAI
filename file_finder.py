import os
import sys

def find_sensitive_files(start_path, patterns=None):
    if patterns is None:
        patterns = ['.env', '.git', 'config', 'secret', 'password', 'key', 'credential']
    sensitive_files = []
    for root, dirs, files in os.walk(start_path):
        for file in files:
            file_path = os.path.join(root, file)
            if any(pattern in file.lower() for pattern in patterns):
                sensitive_files.append(file_path)
    return sensitive_files

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python file_finder.py <start_path>")
        sys.exit(1)
    start_path = sys.argv[1]
    if not os.path.exists(start_path):
        print(f"Path {start_path} does not exist.")
        sys.exit(1)
    print(f"Searching for sensitive files in {start_path}...")
    found = find_sensitive_files(start_path)
    if found:
        print("Found sensitive files:")
        for f in found:
            print(f"  {f}")
    else:
        print("No sensitive files found.")