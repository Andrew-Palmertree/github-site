import time
import base64
import hashlib
import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from PIL import Image
import io

# Splunk Settings
DASHBOARD_URL = "http://localhost:8000/en-US/app/search/splunk_logger_dashboard"
USERNAME = "*****"
PASSWORD = "*****"

# GitHub Settings
GITHUB_REPO = "Andrew-Palmertree/github-site"
GITHUB_PATH = "static/images/splunk_logger_dashboard.png"
GITHUB_TOKEN = "*****"
BRANCH = "main"

# Selenium Chrome Headless Options
options = Options()
options.add_argument("--headless")
options.add_argument("--window-size=1920,1080")
options.add_argument("--ignore-certificate-errors")

# Functions

def upload_to_github(img_bytes):
    """Upload the given image bytes to GitHub."""
    content_b64 = base64.b64encode(img_bytes).decode("utf-8")
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{GITHUB_PATH}"

    # Get current file SHA if it exists
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json"
    }
    r = requests.get(url, headers=headers)
    sha = r.json().get("sha") if r.status_code == 200 else None

    data = {
        "message": "Update Splunk dashboard screenshot",
        "content": content_b64,
        "branch": BRANCH
    }
    if sha:
        data["sha"] = sha

    r = requests.put(url, headers=headers, json=data)
    if r.status_code in [200, 201]:
        print("Screenshot uploaded to GitHub!")
    else:
        print("Upload failed:", r.json())

def capture_dashboard(driver):
    """Capture the dashboard screenshot, crop it, and return bytes."""
    png = driver.get_screenshot_as_png()
    img = Image.open(io.BytesIO(png))

    # Crop top & bottom
    left, top, right, bottom = 0, 79, img.width, img.height - 100
    cropped_img = img.crop((left, top, right, bottom))

    buffer = io.BytesIO()
    cropped_img.save(buffer, format="PNG")
    return buffer.getvalue()

# Main Loop
driver = webdriver.Chrome(options=options)
last_hash = None

try:
    while True:
        driver.get(DASHBOARD_URL)

        # Handle login if present
        if "login" in driver.current_url.lower():
            driver.find_element("id", "username").send_keys(USERNAME)
            driver.find_element("id", "password").send_keys(PASSWORD)
            driver.find_element("css selector", "input[type='submit']").click()
            time.sleep(5)

        time.sleep(10)  # wait for dashboard to load fully

        # Capture screenshot and crop
        img_bytes = capture_dashboard(driver)

        # Compute SHA256 hash of the image
        current_hash = hashlib.sha256(img_bytes).hexdigest()

        if current_hash != last_hash:
            print("Change detected on dashboard!")
            last_hash = current_hash
            upload_to_github(img_bytes)
        else:
            print("No change detected...")

        time.sleep(300)  # wait 5 minute before checking again

finally:
    driver.quit()
