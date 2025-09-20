#!/bin/bash

# Kill any old ngrok process
pkill -f "ngrok http" 2>/dev/null || true

# Start ngrok in background
nohup /usr/local/bin/ngrok http --url=frank-gazelle-totally.ngrok-free.app 8088 > ~/ngrok.log 2>&1 &
echo "ngrok started with domain: frank-gazelle-totally.ngrok-free.app"

# Splunk screenshot script
echo "Starting Splunk screenshot script..."
/usr/bin/python3 /home/andrew/splunk_screenshot.py
