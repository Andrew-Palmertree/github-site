from flask import Flask, request, jsonify
import requests
import os
import uuid
import base64

app = Flask(__name__)

SPLUNK_HEC_URL = os.getenv('SPLUNK_HEC_URL')  # e.g. https://localhost:8088/services/collector/event
SPLUNK_HEC_TOKEN = os.getenv('SPLUNK_HEC_TOKEN')

# SSL CERT & KEY from environment variables
SPLUNK_CERT_B64 = os.getenv("SPLUNK_CERT_B64")
SPLUNK_KEY_B64 = os.getenv("SPLUNK_KEY_B64")

CERT_FILE = "cert.pem"
KEY_FILE = "key.pem"

# Decode cert and key to files if provided
if SPLUNK_CERT_B64 and SPLUNK_KEY_B64:
    with open(CERT_FILE, "wb") as cert_file:
        cert_file.write(base64.b64decode(SPLUNK_CERT_B64))
    with open(KEY_FILE, "wb") as key_file:
        key_file.write(base64.b64decode(SPLUNK_KEY_B64))


def send_log_to_splunk(source, message):
    if not SPLUNK_HEC_URL or not SPLUNK_HEC_TOKEN:
        print("Splunk HEC URL or Token not configured.")
        return

    channel = str(uuid.uuid4())  # generate unique channel ID

    payload = {
        "host": "render-app",
        "source": source,
        "sourcetype": "_json",
        "event": {
            "message": message
        }
    }

    headers = {
        "Authorization": f"Splunk {SPLUNK_HEC_TOKEN}",
        "Content-Type": "application/json",
        "X-Splunk-Request-Channel": channel
    }

    try:
        # Send event
        response = requests.post(
            SPLUNK_HEC_URL,
            json=payload,
            headers=headers,
            verify=True,  # Enable SSL verification
            cert=(CERT_FILE, KEY_FILE)
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
            verify=True,
            cert=(CERT_FILE, KEY_FILE)
        )
        if ack_response.status_code != 200:
            print(f"Failed to send ack to Splunk: {ack_response.status_code} - {ack_response.text}")

    except Exception as e:
        print(f"Error sending log to Splunk: {e}")


@app.route("/", methods=["GET"])
def index():
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
    # Enable HTTPS for Flask using decoded certs
    app.run(host='0.0.0.0', port=10000, ssl_context=(CERT_FILE, KEY_FILE))
