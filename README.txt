📱 PC Usage Tracker App — Overview & Instructions
This app tracks how long a user spends on different applications (like Chrome, VS Code, etc.) and sends that data to a FastAPI backend. Users log in once, and their activity is tracked only when they’re authenticated.

🔧 Libraries Used & Their Roles

Library	    Role
win32gui	Get the title of the currently active window on Windows
time	    Measure how long each app is being used
os	        Check for file existence, paths, and handle local config
requests	Send HTTP requests (like sending usage data to the FastAPI backend)
json	    Load and save config/token files in readable format
FastAPI	    Backend framework for APIs (login, signup, data upload, etc.)
SQLModel	ORM to interact with SQLite DB easily (stores user & usage records)
uvicorn	    Runs the FastAPI server (local development)

🔐 How Login Works

User logs in (or signs up) through FastAPI
The received JWT token is saved in auth_config.json

Next time the user opens the tracker:
If token exists → it sends usage data
If not → user must log in again