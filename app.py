from flask import Flask, request, jsonify
import requests
import os

app = Flask(__name__)

SPLUNK_HEC_URL=http://127.0.0.1:8088/services/collector
SPLUNK_HEC_TOKEN=<your-Splunk-HEC-token>

SPLUNK_HEC_URL = os.getenv('SPLUNK_HEC_URL')
SPLUNK_HEC_TOKEN = os.getenv('SPLUNK_HEC_TOKEN')

@app.route("/log", methods=["POST"])
def log():
    data = request.get_json()

    if not data:
        return jsonify({"error": "Invalid JSON"}), 400

    # Prepare payload for Splunk HEC
    payload = {
        "event": data,
        "sourcetype": "_json"
    }

    headers = {
        "Authorization": f"Splunk {SPLUNK_HEC_TOKEN}"
    }

    try:
        response = requests.post(SPLUNK_HEC_URL, json=payload, headers=headers, verify=False)
        if response.status_code != 200:
            return jsonify({"error": "Failed to forward to Splunk", "details": response.text}), 500
        return jsonify({"status": "success"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/")
def index():
    return "Hello from Render logging app!"
