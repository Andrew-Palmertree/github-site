from flask import Flask, request, jsonify, render_template
import requests
import os
import uuid

app = Flask(__name__)

SPLUNK_HEC_URL = os.getenv('SPLUNK_HEC_URL')  # e.g. https://splunk.company.com:8088/services/collector/event
SPLUNK_HEC_TOKEN = os.getenv('SPLUNK_HEC_TOKEN')


def send_log_to_splunk(source, message):
    if not SPLUNK_HEC_URL or not SPLUNK_HEC_TOKEN:
        print("Splunk HEC URL or Token not configured.")
        return False

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
            return False

        return True

    except Exception as e:
        print(f"Error sending log to Splunk: {e}")
        return False


@app.route("/home", methods=["GET"])
def home():
    return render_template("home.html", name="Andrew Palmertree")


@app.route("/log", methods=["POST"])
def log():
    data = request.get_json()
    if not data or "message" not in data:
        return jsonify({"error": "Message is required"}), 400

    success = send_log_to_splunk("web-app", data["message"])

    if success:
        return jsonify({"status": "success"}), 200
    else:
        return jsonify({"status": "error"}), 500


@app.route("/health", methods=["GET"])
def health():
    return "OK", 200


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
