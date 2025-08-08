import os
import requests
import uuid


TOKEN = "auth_token.txt"
DEVICE = "device_id.txt"


def login_save_token():
    res = requests.post("http://localhost:8000/login", json = {
        "email" : "khawajab302@gmail.com",
        "password" : "User@001"
        })
    
    if res.status_code == 200:
        token = res.json()["access_token"]
        with open(TOKEN, 'w') as f:
            f.write(token)
        print("Token saved")    
    else:
        print("Login failed", res.text)
        
def create_save_device_id():
    if os.path.exists(DEVICE):
        print("Device ID already exists")
    else:
        device_id = int(uuid.uuid4())
        with open(DEVICE, 'w') as f:
            f.write(device_id)
            print("Device id saved")    
        
        return device_id 
    
if __name__ == "__main__":
    login_save_token()
    create_save_device_id()    