import os
import ssl
import socket
from datetime import datetime
from requests import get
from tabulate import tabulate

def run_tool(inputs: dict) -> dict:
    output_dir = inputs.get("output_dir", "/tmp")
    try:
        # Get the list of domains from the input
        domains = inputs.get("domains", [])

        # Initialize the table data
        table_data = []

        # Iterate over each domain
        for domain in domains:
            print(f"Checking SSL certificate for {domain}...")
            try:
                # Get the SSL certificate for the domain
                context = ssl.create_default_context()
                with socket.create_connection((domain, 443)) as sock:
                    with context.wrap_socket(sock, server_hostname=domain) as ssock:
                        # Get the SSL certificate
                        cert = ssock.getpeercert()

                        # Get the expiration date of the certificate
                        expires_on = datetime.strptime(cert['notAfter'], '%b %d %H:%M:%S %Y %Z')

                        # Calculate the number of days until the certificate expires
                        days_until_expiration = (expires_on - datetime.now()).days

                        # Add the data to the table
                        table_data.append([domain, expires_on.strftime('%Y-%m-%d'), days_until_expiration])

            except Exception as e:
                # If there's an error, add a row to the table with the error message
                table_data.append([domain, "Error", str(e)])

        # Create the Markdown table
        markdown_table = tabulate(table_data, headers=["Domain", "Expires On", "Days Until Expiration"], tablefmt="markdown")

        # Save the table to a file
        output_file = os.path.join(output_dir, "ssl_certificates.md")
        with open(output_file, "w") as f:
            f.write(markdown_table)

        # Return the result
        return {"ok": True, "output": markdown_table, "files": [output_file], "error": ""}

    except Exception as e:
        return {"ok": False, "output": "", "files": [], "error": str(e)}