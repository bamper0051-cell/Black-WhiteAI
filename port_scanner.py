import socket
import sys

def scan_ports(host, start_port=1, end_port=1024):
    open_ports = []
    for port in range(start_port, end_port + 1):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(0.5)
        result = sock.connect_ex((host, port))
        if result == 0:
            open_ports.append(port)
        sock.close()
    return open_ports

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python port_scanner.py <host> [start_port] [end_port]")
        sys.exit(1)
    host = sys.argv[1]
    start_port = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    end_port = int(sys.argv[3]) if len(sys.argv) > 3 else 1024
    print(f"Scanning {host} from port {start_port} to {end_port}...")
    open_ports = scan_ports(host, start_port, end_port)
    if open_ports:
        print(f"Open ports: {open_ports}")
    else:
        print("No open ports found in the specified range.")