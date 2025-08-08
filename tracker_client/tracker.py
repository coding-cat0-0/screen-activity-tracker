import win32gui
import os
import time
import requests
from datetime import datetime
import uuid

def get_active_window_title():
    return win32gui.GetWindowText(win32gui.GetForegroundWindow())

def load_token():
    if os.path.exists("auth_token.txt"):
        with open("auth_token.txt", "r") as f:
            return f.read().strip()

def create_or_get_id():
    if os.path.exists('device_id.txt'):
        with open('device_id.txt', 'r') as f:
            return f.read().strip()

        
def send_usage(data):
    token = load_token()
    if token:
     try:    
        headers = {"Authorization" : f"Bearer {token}"}
        res = requests.post("http://localhost:8000/add_activity", json=data, headers=headers)
        print(f"Status: {res.status_code}")
        print(f"Response: {res.text}")

        if res.status_code == 200:
            print(" Usage successfully stored in DB")
        else:
            print(" Backend rejected the data")
     except Exception as e:
        print(f"Error sending usage: {e}")
    

device_id = create_or_get_id()
current_app = get_active_window_title()
start_time = time.time()

while True:
    time.sleep(1)
    new_app = get_active_window_title()
    if new_app != current_app:
        duration = int(time.time() - start_time)
    
        data = {
            "device_id": device_id,
            "app" : current_app,
            "duration": duration,
            "timestamp" : start_time
        }
    
        send_usage(data)    
        current_app = new_app
        start_time = time.time()
        
