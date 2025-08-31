from flask import Flask, request, jsonify
import requests
import os
import uuid

app = Flask(__name__)

# Load Splunk HEC settings from environment variables
SPLUNK_HEC_URL = os.getenv('SPLUNK_HEC_URL')  # e.g. http://localhost:8088/services/collector/event
SPLUNK_HEC_TOKEN = os.getenv('SPLUNK_HEC_TOKEN')

@@ -14,6 +14,8 @@ def send_log_to_splunk(source, message):
        print("Splunk HEC URL or Token not configured.")
        return

    channel = str(uuid.uuid4())  # generate unique channel ID

    payload = {
        "host": "render-app",
        "source": source,
@@ -25,10 +27,12 @@ def send_log_to_splunk(source, message):

    headers = {
        "Authorization": f"Splunk {SPLUNK_HEC_TOKEN}",
        "Content-Type": "application/json"
        "Content-Type": "application/json",
        "X-Splunk-Request-Channel": channel
    }

    try:
        # Send event
        response = requests.post(
            SPLUNK_HEC_URL,
            json=payload,
@@ -37,6 +41,33 @@ def send_log_to_splunk(source, message):
        )
        if response.status_code != 200:
            print(f"Failed to send log to Splunk: {response.status_code} - {response.text}")
            return

        # Parse ackId from response
        response_json = response.json()
        ack_id = response_json.get("ackId")
        if not ack_id:
            print("No ackId in response from Splunk")
            return

        # Send acknowledgment POST
        ack_url = SPLUNK_HEC_URL.replace("/event", "/ack") + f"?channel={channel}"
        ack_body = {
            "acks": [ack_id]
        }
        ack_headers = {
            "Authorization": f"Splunk {SPLUNK_HEC_TOKEN}",
            "Content-Type": "application/json"
        }
        ack_response = requests.post(
            ack_url,
            json=ack_body,
            headers=ack_headers,
            verify=False
        )
        if ack_response.status_code != 200:
            print(f"Failed to send ack to Splunk: {ack_response.status_code} - {ack_response.text}")

    except Exception as e:
        print(f"Error sending log to Splunk: {e}")
