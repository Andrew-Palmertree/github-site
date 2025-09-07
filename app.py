from flask import Flask, request, jsonify, render_template
import requests
import os
import uuid
import re
from better_profanity import profanity
from profanity_filter import ProfanityFilter
from detoxify import Detoxify  # AI-based profanity detection

app = Flask(__name__)

# Load better-profanity
profanity.load_censor_words()

# Initialize profanity-filter
pf = ProfanityFilter()

# Initialize AI model (Detoxify)
detox_model = Detoxify('original')

# Environment variables
SPLUNK_HEC_URL = os.getenv('SPLUNK_HEC_URL')
SPLUNK_HEC_TOKEN = os.getenv('SPLUNK_HEC_TOKEN')
DEPLOY_HOOK = os.getenv('DEPLOY_HOOK')
DEPLOY_URL = os.getenv('DEPLOY_URL')


def send_log_to_splunk(source, message):
    if not SPLUNK_HEC_URL or not SPLUNK_HEC_TOKEN:
        return
    channel = str(uuid.uuid4())
    payload = {
        "host": "render-app",
        "source": source,
        "sourcetype": "_json",
        "event": {"message": message}
    }
    headers = {
        "Authorization": f"Splunk {SPLUNK_HEC_TOKEN}",
        "Content-Type": "application/json",
        "X-Splunk-Request-Channel": channel
    }
    try:
        requests.post(SPLUNK_HEC_URL, json=payload, headers=headers, verify=False)
    except Exception as e:
        print(f"Error sending log: {e}")


def contains_profanity_ai(message):
    """
    Hybrid profanity detection:
    1. better-profanity → simple blacklist
    2. profanity-filter → fuzzy matches
    3. Detoxify → AI contextual detection
    4. Custom regex → obfuscated tricks
    """
    # Fast blacklist
    if profanity.contains_profanity(message):
        return True

    # Fuzzy filtering
    if pf.is_profane(message):
        return True

    # AI contextual detection
    scores = detox_model.predict(message)
    if scores.get("toxicity", 0) > 0.7:
        return True

    # Regex for obfuscations
    tricky_patterns = [
        r"f[\W_]*u[\W_]*c[\W_]*k",
        r"f[\W_]*u[\W_]+",
        r"sh[\W_]*i[\W_]*t",
        r"b[\W_]*i[\W_]*t[\W_]*ch",
        r"a[\W_]*s[\W_]*s[\W_]*hole"
    ]
    for pattern in tricky_patterns:
        if re.search(pattern, message, re.IGNORECASE):
            return True

    return False


@app.route("/log", methods=["POST"])
def log():
    data = request.get_json()
    if not data or "message" not in data:
        return jsonify({"status": "error", "message": "Invalid JSON"}), 400

    source = data.get("source", "client")
    message = data["message"]

    try:
        if contains_profanity_ai(message):
            return jsonify({
                "status": "error",
                "message": "Your message contains inappropriate language."
            }), 400
    except Exception as e:
        return jsonify({"status": "error", "message": f"Profanity check failed: {e}"}), 500

    send_log_to_splunk(source, message)
    return jsonify({"status": "success"}), 200
