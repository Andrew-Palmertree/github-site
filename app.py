# Andrew Palmertree
# 8-24-2025
# Main Python script that runs the logic on Render to determine if a certain webpage is visited.

from flask import Flask, request, jsonify, render_template
import requests
import os
import uuid
from better_profanity import profanity
from cleantext import clean

app = Flask(__name__)

# Initialize better-profanity
profanity.load_censor_words()

# Environment variables for Splunk and Render Tunnel URL to local machine
SPLUNK_HEC_URL = os.getenv('SPLUNK_HEC_URL')
SPLUNK_HEC_TOKEN = os.getenv('SPLUNK_HEC_TOKEN')
DEPLOY_HOOK = os.getenv('DEPLOY_HOOK')
DEPLOY_URL = os.getenv('DEPLOY_URL')

# Functions
def normalize_text(text):
# clean up weird spelling
    return clean(
        text,
        lower=True,
        no_punct=True,
        replace_with_punct="",
        replace_with_email="",
        replace_with_url=""
    )

def contains_profanity(text):
    # Check if a message contains profanity after normalization.
    normalized = normalize_text(text)
    return profanity.contains_profanity(normalized)

def send_log_to_splunk(source, message):
    # Send logs to Splunk via HTTP Event Collector (HEC).
    if not SPLUNK_HEC_URL or not SPLUNK_HEC_TOKEN:
        print("Splunk HEC URL or Token not configured.")
        return

    channel = str(uuid.uuid4())

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
        response = requests.post(
            SPLUNK_HEC_URL,
            json=payload,
            headers=headers,
            verify=False
        )

        if response.status_code != 200:
            print(f"Failed to send log to Splunk: {response.status_code} - {response.text}")
            return

        # confirm ack from Splunk
        response_json = response.json()
        ack_id = response_json.get("ackId")

        if not ack_id:
            print("No ackId in response from Splunk")
            return

        ack_url = SPLUNK_HEC_URL.replace("/event", "/ack") + f"?channel={channel}"
        ack_body = {"acks": [ack_id]}
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

# Routes for the URL https://github-site.onrender.com

@app.route("/", methods=["GET"])
def index():
    send_log_to_splunk("render-app", f"Homepage visited from {request.remote_addr}")
    return "Hello from Render logging app!"

@app.route("/home", methods=["GET"])
def home():
    send_log_to_splunk("render-app", "Home page request")
    return render_template("home.html", name="Andrew Palmertree")

# Sends events to Splunk
@app.route("/log", methods=["POST"])
def log():
    data = request.get_json()

    if not data or "message" not in data:
        return jsonify({"status": "error", "message": "Invalid JSON"}), 400

    source = data.get("source", "client")
    message = data["message"]

    try:
        # Profanity check
        if contains_profanity(message):
            return jsonify({
                "status": "error",
                "message": "Your message contains inappropriate language."
            }), 400

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Profanity check failed: {e}"
        }), 500

    # Safe message → send to Splunk
    send_log_to_splunk(source, message)

    return jsonify({"status": "success"}), 200

@app.route("/health", methods=["GET"])
def health():
    send_log_to_splunk("render-app", "Health check endpoint hit")
    return "OK", 200

# Main
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
