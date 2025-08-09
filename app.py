from flask import Flask, request, jsonify
import requests
import os
from datetime import datetime

app = Flask(__name__)

# Load Splunk HEC settings from environment variables
SPLUNK_HEC_URL = os.getenv('SPLUNK_HEC_URL')
SPLUNK_HEC_TOKEN = os.getenv('SPLUNK_HEC_TOKEN')


def send_log_to_splunk(source, message):
    if not SPLUNK_HEC_URL or not SPLUNK_HEC_TOKEN:
        print("Splunk HEC URL or Token not configured.")
        return

    # If message is string, wrap it in an object
    if isinstance(message, str):
        event_data = {"message": message}
    elif isinstance(message, dict):
        event_data = message
    else:
        # fallback to string conversion inside object
        event_data = {"message": str(message)}

    payload = {
      "event": {"message": "test log"},
      "sourcetype": "_json"
    }

    headers = {
        "Authorization": f"Splunk {SPLUNK_HEC_TOKEN}",
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(
            SPLUNK_HEC_URL,
            json=payload,
            headers=headers,
            verify=False
        )
        if response.status_code != 200:
            print(f"Failed to send log to Splunk: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"Error sending log to Splunk: {e}")




@app.route("/", methods=["GET"])
def index():
    # Send a log to Splunk whenever someone visits /
    send_log_to_splunk("render-app", f"Homepage visited from {request.remote_addr}")
    return "Hello from Render logging app!"


@app.route("/log", methods=["POST"])
def log():
    data = request.get_json()

    if not data:
        return jsonify({"error": "Invalid JSON"}), 400

    send_log_to_splunk("client", data)
    return jsonify({"status": "success"}), 200


@app.route("/health", methods=["GET"])
def health():
    send_log_to_splunk("render-app", "Health check endpoint hit")
    return "OK", 200


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
