import os
import re
from collections import Counter
from typing import Dict

def run_tool(inputs: Dict) -> Dict:
    """
    Count the occurrences of each IP address and get the top 5.

    Args:
    inputs (Dict): A dictionary containing the input data.
        - ip_addresses (str): The output from step 2, which is expected to be a string containing IP addresses.
        - chat_id (str): The chat ID, which is not used in this tool.
        - task (str): The task description, which is not used in this tool.

    Returns:
    Dict: A dictionary containing the results.
        - ok (bool): Whether the tool executed successfully.
        - output (str): The top 5 IP addresses and their counts.
        - files (list[str]): A list of output files, which is empty in this case.
        - error (str): An error message if the tool failed, otherwise an empty string.
    """

    output_dir = inputs.get("output_dir", "/tmp")
    try:
        # Extract the IP addresses from the input string
        ip_addresses = inputs.get("ip_addresses", "")
        ip_address_list = re.findall(r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b', ip_addresses)

        # Count the occurrences of each IP address
        ip_address_counts = Counter(ip_address_list)

        # Get the top 5 IP addresses
        top_5_ip_addresses = ip_address_counts.most_common(5)

        # Create the output string
        output = "Top 5 IP addresses:\n"
        for ip_address, count in top_5_ip_addresses:
            output += f"{ip_address}: {count}\n"

        print("Top 5 IP addresses counted successfully.")

        return {"ok": True, "output": output, "files": [], "error": ""}
    except Exception as e:
        return {"ok": False, "output": "", "files": [], "error": str(e)}