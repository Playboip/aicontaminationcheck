from flask import Flask, render_template, request
import requests
import uuid
import os
import json
from datetime import datetime, timedelta

app = Flask(__name__)

EMAIL_ADDRESS = os.environ.get("COPYLEAKS_EMAIL")
API_KEY = os.environ.get("COPYLEAKS_API_KEY")

def get_auth_token():
    if os.path.exists("auth_token.json"):
        with open("auth_token.json", "r") as f:
            token_data = json.load(f)
            # The token is valid for 48 hours, so we check if it's expired
            if datetime.utcnow() < datetime.fromisoformat(token_data[".expires"][:-1]):
                return token_data

    login_url = "https://id.copyleaks.com/v3/account/login/api"
    login_payload = {
        "email": EMAIL_ADDRESS,
        "key": API_KEY
    }
    login_response = requests.post(login_url, json=login_payload)
    if login_response.ok:
        token_data = login_response.json()
        with open("auth_token.json", "w") as f:
            json.dump(token_data, f)
        return token_data
    else:
        # Handle the case where login fails
        print(f"Failed to get auth token: {login_response.status_code} {login_response.text}")
        return None

auth_token = get_auth_token()

def is_generated_by_ai(paragraph):
    if len(paragraph) < 255:
        return "Text is too short to be analyzed. Please enter at least 255 characters."
    scan_id = str(uuid.uuid4())
    scan_url = f"https://api.copyleaks.com/v2/writer-detector/{scan_id}/check"
    scan_payload = {
        "text": paragraph,
        "sandbox": False
    }
    headers = {
        "Authorization": f"Bearer {auth_token['access_token']}",
        "Content-Type": "application/json"
    }
    try:
        scan_response = requests.post(scan_url, json=scan_payload, headers=headers)
        response_json = scan_response.json()
        if 'summary' in response_json:
            ai_score = response_json['summary']['ai']
            if ai_score > 0.5:
                return 'Likely AI-generated'
            else:
                return 'Likely human-generated'
        elif 'ErrorCode' in response_json and response_json['ErrorCode'] == 'not-enough-credits':
            return "Error: Not enough credits to perform the scan."
        else:
            return "Error: Could not determine AI score."
    except Exception as e:
        return "Error: An unexpected error occurred."

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/check', methods=['POST'])
def check():
    text = request.form['text']
    result = is_generated_by_ai(text)
    return render_template('result.html', result=result)

if __name__ == '__main__':
    app.run(debug=True)
