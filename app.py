from flask import Flask, request, jsonify
import requests
import os

app = Flask(__name__)

SPLUNK_HEC_URL=http://<your-splunk-host>:8088/services/collector
SPLUNK_HEC_TOKEN=<your-Splunk-HEC-token>

# Load environment variables for security (set these in Render or .env file locally)
SPLUNK_HEC_URL = os.getenv('SPLUNK_HEC_URL')  # the name of the environment variable
SPLUNK_HEC_TOKEN = os.getenv('SPLUNK_HEC_TOKEN')  # the name of the environment variable

@app.route('/')
def home():
    return "<h1>Splunk Log Proxy</h1><p>POST JSON logs to <code>/log</code>.</p>"

@app.route('/health', methods=['GET'])
def health():
    return "OK", 200

@app.route('/log', methods=['POST'])
def log_to_splunk():
    if not SPLUNK_HEC_URL or not SPLUNK_HEC_TOKEN:
        return jsonify({'error': 'Splunk HEC URL or Token not configured'}), 500

    data = request.get_json()
    if not data:
        return jsonify({'error': 'No JSON data received'}), 400

    # Wrap in Splunk HEC format
    payload = {
        "event": data,
        "sourcetype": "_json",
        "host": request.remote_addr
    }

    headers = {
        'Authorization': f'Splunk {SPLUNK_HEC_TOKEN}'
    }

    try:
        response = requests.post(SPLUNK_HEC_URL, json=payload, headers=headers, verify=False)
        return jsonify({'splunk_response': response.text}), response.status_code
    except requests.exceptions.RequestException as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
