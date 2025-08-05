from flask import Flask, request, jsonify
import json

app = Flask(__name__)

@app.route('/log', methods=['POST'])
def log():
    data = request.json
    print("Log received:", json.dumps(data, indent=2))
    # Here you can send the data to Splunk via HTTP Event Collector if you want.
    return jsonify({'status': 'received'}), 200

@app.route('/health', methods=['GET'])
def health():
    return "OK", 200
