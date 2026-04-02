import socket
import sys
import struct

def sniff_packets(interface):
    try:
        sock = socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.ntohs(0x0003))
        sock.bind((interface, 0))
        print(f"Sniffing on interface {interface}... (Ctrl+C to stop)")
        packet_count = 0
        while True:
            packet = sock.recvfrom(65535)[0]
            packet_count += 1
            if packet_count % 10 == 0:
                print(f"Captured {packet_count} packets...")
    except PermissionError:
        print("Error: This script requires root privileges.")
        sys.exit(1)
    except KeyboardInterrupt:
        print(f"\nTotal packets captured: {packet_count}")
        sys.exit(0)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: sudo python network_sniffer.py <interface>")
        print("Example interfaces: eth0, wlan0, lo")
        sys.exit(1)
    interface = sys.argv[1]
    sniff_packets(interface)