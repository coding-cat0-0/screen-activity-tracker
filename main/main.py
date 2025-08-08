import uvicorn
from fastapi import FastAPI
from routers import login, activity
from sqlmodel import SQLModel
from database.structure import engine
from utils import login_save_token, create_save_device_id

app = FastAPI()

app.include_router(login.router)
app.include_router(activity.router)

 
@app.on_event("startup")
def on_startup() -> None:
    SQLModel.metadata.create_all(engine)