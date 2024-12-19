import sys
import json
import os
import subprocess
import gzip
import csv
import requests
from datetime import datetime

RESULTS_DIR = "/opt/splunk/var/run/splunk/dispatch"  # Default path for dispatch directory in Splunk
TOCSV_CMD = ["splunk", "cmd", "splunkd", "toCsv"]
WEBHOOK_URL = "http://10.1.1.1:8001"  # Replace with your webhook URL
PENDING_WEBHOOK_FILE = "./pending_webhooks.json"  # Store pending webhooks in the script's directory

def load_pending_webhooks():
    """Load pending webhooks from a file."""
    if os.path.exists(PENDING_WEBHOOK_FILE):
        with open(PENDING_WEBHOOK_FILE, "r") as file:
            return json.load(file)
    return []

def save_pending_webhooks():
    """Save pending webhooks to a file."""
    with open(PENDING_WEBHOOK_FILE, "w") as file:
        json.dump(PENDING_WEBHOOKS, file)

def filter_mv_fields(data):
    """Remove fields starting with __mv_ and their values."""
    if not data:
        return data

    headers = data[0]
    filtered_headers = [header for header in headers if not header.startswith("__mv_")]

    filtered_data = [
        [row[i] for i in range(len(headers)) if not headers[i].startswith("__mv_")]
        for row in data
    ]

    return filtered_data

def send_webhook(sid, search_name, extracted_data):
    """Send extracted data to a webhook."""
    payload = {
        "sid": sid,
        "search_name": search_name,
        "results": extracted_data
    }
    try:
        response = requests.post(WEBHOOK_URL, json=payload, headers={"Content-Type": "application/json"})
        if 200 <= response.status_code < 300:
            sys.stderr.write(f"INFO Webhook sent successfully, status: {response.status_code}\n")
            return True
        else:
            sys.stderr.write(f"ERROR Webhook failed with status: {response.status_code}\n")
            return False
    except Exception as e:
        sys.stderr.write(f"ERROR Failed to send webhook: {e}\n")
        return False

def retry_pending_webhooks():
    """Retry sending any pending webhooks."""
    global PENDING_WEBHOOKS
    for webhook in PENDING_WEBHOOKS[:]:  # Iterate over a copy of the list
        sid, search_name, extracted_data = webhook
        if send_webhook(sid, search_name, extracted_data):
            PENDING_WEBHOOKS.remove(webhook)

if __name__ == "__main__":
    # Load pending webhooks at the start
    PENDING_WEBHOOKS = load_pending_webhooks()

    # Check for --execute flag
    if len(sys.argv) < 2 or sys.argv[1] != "--execute":
        sys.stderr.write("FATAL Unsupported execution mode (expected --execute flag)\n")
        sys.exit(1)
    try:
        # Read input settings from stdin
        settings = json.loads(sys.stdin.read())

        # Extract SID and search_name
        sid = settings.get('sid', 'N/A')
        search_name = settings.get('search_name', 'N/A')

        # Define possible result file paths in the dispatch directory
        result_csv_gz = os.path.join(RESULTS_DIR, sid, "results.csv.gz")
        result_srs_gz = os.path.join(RESULTS_DIR, sid, "results.srs.gz")

        extracted_data = []
        if os.path.exists(result_csv_gz):
            # Extract data from results.csv.gz
            sys.stderr.write(f"INFO Extracting results from {result_csv_gz}\n")
            with gzip.open(result_csv_gz, 'rt') as src:
                reader = csv.reader(src)
                for row in reader:
                    extracted_data.append(row)
            sys.stderr.write(f"INFO Extracted {len(extracted_data)} rows from {result_csv_gz}\n")
        elif os.path.exists(result_srs_gz):
            # Convert and extract data from results.srs.gz using splunkd toCsv
            sys.stderr.write(f"INFO Converting and extracting results.srs.gz for SID {sid}\n")
            result = subprocess.run(TOCSV_CMD + [result_srs_gz], stdout=subprocess.PIPE, check=True, text=True)
            extracted_data = [line.split(',') for line in result.stdout.splitlines() if line]
            sys.stderr.write(f"INFO Extracted {len(extracted_data)} rows from results.srs.gz\n")
        else:
            sys.stderr.write(f"ERROR No results file found for SID: {sid}\n")
            sys.exit(2)

        # Filter out __mv_ fields
        extracted_data = filter_mv_fields(extracted_data)

        # Retry pending webhooks before sending new one
        retry_pending_webhooks()

        # Send extracted data to webhook
        if not send_webhook(sid, search_name, extracted_data):
            PENDING_WEBHOOKS.append((sid, search_name, extracted_data))

    except subprocess.CalledProcessError as e:
        sys.stderr.write(f"ERROR Failed to convert results.srs.gz: {e}\n")
        sys.exit(3)
    except Exception as e:
        sys.stderr.write(f"ERROR Unexpected error: {e}\n")
        sys.exit(3)
    finally:
        # Save pending webhooks after processing
        save_pending_webhooks()
