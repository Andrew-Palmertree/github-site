from flask import Flask, request, jsonify, render_template
import requests
import os
import uuid
from better_profanity import profanity
from profanity_check import predict

app = Flask(__name__)

# Load better-profanity word list
profanity.load_censor_words()

SPLUNK_HEC_URL = os.getenv('SPLUNK_HEC_URL')  # Splunk HEC URL
SPLUNK_HEC_TOKEN = os.getenv('SPLUNK_HEC_TOKEN')
DEPLOY_HOOK = os.getenv('DEPLOY_HOOK')
DEPLOY_URL = os.getenv('DEPLOY_URL')


def send_log_to_splunk(source, message):
    if not SPLUNK_HEC_URL or not SPLUNK_HEC_TOKEN:
        print("Splunk HEC URL or Token not configured.")
        return

    channel = str(uuid.uuid4())  # Unique channel ID

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


@app.route("/", methods=["GET"])
def index():
    send_log_to_splunk("render-app", f"Homepage visited from {request.remote_addr}")
    return "Hello from Render logging app!"


@app.route("/home", methods=["GET"])
def home():
    send_log_to_splunk("render-app", "Home page request")
    return render_template("home.html", name="Andrew Palmertree")


@app.route("/log", methods=["POST"])
def log():
    data = request.get_json()

    if not data or "message" not in data:
        return jsonify({"status": "error", "message": "Invalid JSON"}), 400

    source = data.get("source", "client")
    message = data["message"]

    try:
        # First layer: better-profanity (fast)
        if profanity.contains_profanity(message):
            return jsonify({
                "status": "error",
                "message": "Your message contains inappropriate language."
            }), 400

        # Second layer: profanity-check (AI-based)
        if predict([message])[0] == 1:
            return jsonify({
                "status": "error",
                "message": "Your message was flagged by our AI profanity filter."
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


@app.route("/test-redeploy", methods=["GET"])
def test_redeploy():
    if not DEPLOY_HOOK:
        return jsonify({"status": "error", "message": "DEPLOY_HOOK is not configured"}), 500

    try:
        response = requests.get(DEPLOY_HOOK, timeout=5)

        if response.status_code == 200:
            return jsonify({
                "status": "success",
                "message": "Deploy hook is reachable ✅"
            }), 200
        else:
            return jsonify({
                "status": "warning",
                "message": f"Deploy hook responded, but not OK. Status: {response.status_code}",
                "response": response.text
            }), 200

    except requests.exceptions.RequestException as e:
        return jsonify({
            "status": "error",
            "message": f"Deploy hook is unreachable ❌: {str(e)}"
        }), 500


@app.route(DEPLOY_URL, methods=["POST"])
def redeploy():
    try:
        response = requests.post(DEPLOY_HOOK)
        if response.status_code == 200:
            return jsonify({"status": "success", "message": "Redeployment triggered successfully"})
        else:
            return jsonify({
                "status": "error",
                "message": f"Failed to trigger redeploy. Status: {response.status_code}",
                "response": response.text
            }), 500
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
