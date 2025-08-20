from datetime import timedelta
from typing import Annotated
from database.structure import get_session
from fastapi import APIRouter, Depends, HTTPException, status, Query, File, UploadFile
from datetime import datetime, timedelta, date
from sqlmodels.user_usage import User, AppUsage, AppUserLink, UsageCreate, Timesheet, Projects, Tasks, Attendance, Screenshots
from authentication.jwt_hashing import create_access_token, verify_password, get_current_user, bearer_scheme
from sqlmodel import Session, select
from notifications.ws_router import active_connections
import redis
import json
from email.mime.text import MIMEText
import smtplib
import os

router = APIRouter(
    tags=['Employee']
)

r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

    
# Router for recieving data from the frontend and adding data to redis
@router.post('/start_activity_tracking', dependencies=[Depends(bearer_scheme)])
async def add_activity( usage: UsageCreate,session:Session = Depends(get_session),
                 current_user: User = Depends(get_current_user())) :
    
    if current_user.role != "employee":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail = "Only employees can perform this action")
    add_usage = AppUsage(
        employee_id = current_user.id ,
        role = current_user.role,
        device_id = usage.device_id,
        app = usage.app,
        duration = usage.duration,
        timestamp = usage.timestamp
           )

    email = current_user.username
    if add_usage.duration > 120 :
        connection = active_connections.get(email)
        if connection:
            print("Active Connection", active_connections)
            print("Target email", email) 
            await connection.send_text(f"You've been on this app for more than 2 hours its time for a break!")  
        else:
            print(f"No websocket with email {email} logged in..") 
    
    data = add_usage.model.dump() # converts add_udasage to dict
    queue_name = f"queue_usage_{add_usage.device_id}"
    r.rpush(queue_name, json.dumps(data)) # adds the value to right end of queue and converts to a json string
    # also name the queue "queue_usage"
    email = current_user.email
    connection = active_connections.get(email)
        
    if connection:
            print("Active Connection", active_connections)
            print("Target email", email) 
            await connection.send_text("Activity tracking has started successfully")  
    else:
            print(f"No websocket with email {email} logged in..") 
    return "Record queued succesfully"


# Router for syncing data from redis to the database
@router.post("/sync")
async def sync_activity(device_id : str, session:Session = Depends(get_session),
               current_user : User = Depends(get_current_user())):
    
    if current_user.role != "employee":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail = "Only employees can perform this action")
    count = 0
    queue_name = f"queue_usage_{device_id}"
    while True:
        msg = r.lpop(queue_name) # removes entries from left FIFO
        if not msg:
            break
        data = json.loads(msg) # Decodes JSON string
        sync_activity = AppUsage(**data) # Unpacking
        session.add(sync_activity) # Now adding to the db
        session.refresh(sync_activity) # After refresh id is generated not before
        count += 1
        link = AppUserLink(user_id= data["employee_id"], app_id=sync_activity.id) 
        session.add(link)
    session.commit()
    email = current_user.email
    connection = active_connections.get(email)
        
    if connection:
            print("Active Connection", active_connections)
            print("Target email", email) 
            await connection.send_text("Activity has been synced with database")  
    else:
            print(f"No websocket with email {email} logged in..") 
    return f"Synced {count} records"
        
# Router for stoping the activity tracking        
@router.post('/stop_activity_tracking')
async def stop_tracking(device_id : str, session:Session = Depends(get_session),
               current_user : User = Depends(get_current_user())):
            
    if current_user.role != "employee":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail = "Only employees can perform this action")
    count = 0
    queue_name = f"queue_usage_{device_id}"
    while True:
        msg = r.lpop(queue_name) # removes entries from left FIFO
        if not msg:
            break
        data = json.loads(msg) # Decodes JSON string
        sync_activity = AppUsage(**data) # Unpacking
        session.add(sync_activity)
        session.refresh(sync_activity) # After refresh id is generated not before
        count += 1
        link = AppUserLink(user_id= data["employee_id"], app_id=sync_activity.id) 
        session.add(link)
    session.commit()
    email = current_user.email
    connection = active_connections.get(email)
        
    if connection:
            print("Active Connection", active_connections)
            print("Target email", email) 
            await connection.send_text("Activity tracking has been stopped")  
    else:
            print(f"No websocket with email {email} logged in..") 
    return f"Synced {count} records"        
        
# Starting timesheet and adding to the queue
@router.post('/add_timesheet')
async def add_timesheet(project_id : int,task_id : int,
             session: Session = Depends(get_session),current_user: User = Depends(get_current_user())):
    
    if current_user.role != "employee":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail = "Only employees can perform this action")
    status_now = "Active"
    
    new_timesheet = Timesheet(
        employee_id=current_user.id,
        current_date = date.today(),
        project_id=project_id,
        task_id=task_id,
        start_time = datetime.now() ,
        stop_time = None,
        total_hrs = 0.0,
        status = status_now
    ) 
    
    data = new_timesheet.model_dump()
    queue =f"timesheet_{current_user.id}"
    r.rpush(queue, json.dumps(
        data,
        default = lambda x: x.isoformat() if isinstance(x,(date, datetime)) else x
        )
            ) 
    if new_timesheet.status == "Active":
        mark_present = Attendance(
        employee_id = current_user.id ,
        current_date = date.today() ,
        status = "Present"
        )
    session.add(mark_present)
    session.commit()
    session.refresh(mark_present)
    
    email = current_user.email
    connection = active_connections.get(email)
        
    if connection:
            print("Active Connection", active_connections)
            print("Target email", email) 
            await connection.send_text(f"Timsheet started and attendence successfully marked")  
    else:
            print(f"No websocket with email {email} logged in..") 
    
    project = session.exec(select(Projects).where(Projects.id == project_id)).first()
    client_email = session.exec(select(User).where(User.id == project.client_id)).first()
    
    send_attendance_email(client_email.email)
            
    return {'message' : 'Timesheet started and attendance marked'} 

def send_attendance_email(to_email : str):

    from_email = 'admin1@gmail.com'
    message = MIMEText(f'Attendance has been updated, you can go check it out.')
    message['Subject'] = 'Attendance'
    message['From'] = from_email
    message['To'] = to_email
    with smtplib.SMTP('localhost', 1025) as smtp:
        smtp.send_message(message)  


# Syncing queue with db
@router.post('/sync_queue')
async def sync_timesheet(session: Session = Depends(get_session),
               current_user: User = Depends(get_current_user())):
    
    if current_user.role != "employee":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail = "Only employees can perform this action")
    
    count = 0
    queue =f"timesheet_{current_user.id}"
    while True:
        msg = r.lpop(queue)
        if not msg:
            break

        data = json.loads(msg)
        # Converting back to datetime objects
        if isinstance(data['current_date'], str):
            data['current_date'] = datetime.strptime(data['current_date'], '%Y-%m-%d').date()
        if isinstance(data['start_time'], str):
            data['start_time'] = datetime.fromisoformat(data['start_time'])
        if not data.get('stop_time'):
          data['stop_time'] = datetime.now()
        if 'total_hrs' not in data or  data['total_hrs'] == 0: 
            data['total_hrs'] = round((data['stop_time'] - data['start_time']).total_seconds()/3600, 2) 
                  
        data['status'] = "Inactive"          
                   
        sync_data = Timesheet(**data)
        session.add(sync_data)
        session.commit()
        session.refresh(sync_data)
        count += 1
        
    email = current_user.email
    connection = active_connections.get(email)
        
    if connection:
            print("Active Connection", active_connections)
            print("Target email", email) 
            await connection.send_text("Timsheet synced successfully")  
    else:
            print(f"No websocket with email {email} logged in..") 
    return {'message' : f'Synced {count} timesheet(s) from the queue'}

# Viewing tasks
@router.get('/view_tasks')
def get_tasks(session : Session = Depends(get_session),
              current_user : User= Depends(get_current_user())):
    
    fetch_tasks = session.exec(select(Tasks).where(Tasks.assigned_to == current_user.id)).all()
    if not fetch_tasks:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail = "No task available for you")
    
    return  fetch_tasks   

# Viewing tasks
@router.get('/view_attendance')
def get_attendance(session : Session = Depends(get_session),
              current_user : User= Depends(get_current_user())):
    
    fetch_attendance = session.exec(select(Attendance).where(Attendance.employee_id == current_user.id)).all()
    if not fetch_attendance:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail = "Your attendance hasn't been marked")
    
    return  fetch_attendance       
    
# Viewing timesheet
@router.get('/view_timesheet')
def get_timesheet(session : Session = Depends(get_session),
              current_user : User= Depends(get_current_user())):
    
    fetch_timesheet = session.exec(select(Attendance).where(Attendance.employee_id == current_user.id)).all()
    if not fetch_timesheet:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                            detail = "Your timesheet hasnt been synced yet")
    
    return  fetch_timesheet       
            
# For updating tasks
@router.put('/update_task')
def update_task(task_id : int,updates : str,
                session: Session = Depends(get_session), current_user : User = Depends(get_current_user())):
    
    if current_user.role != "employee":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail = "Only employees can perform this action")
    
    query = select(Tasks).where(Tasks.id == task_id)
    execute = session.exec(query).first()
    if not execute:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail = f"No task by id {task_id} found")
    else:
        execute.status = updates.lower()    
        
    project = session.exec(select(Projects).where(Projects.id == execute.project_id)).first()
    client = select(User).where(User.id == project.client_id)
    get_client = session.exec(client).first()
        
    session.add(execute)
    session.commit()
    session.refresh(execute)
    send_task_email(get_client.email, current_user.id, task_id,
                    project.id)    
    return {'message' : 'Task status updated successfully'}


def send_task_email(to_email : str, employee_id :int, task_id :int,
                    project_id : int):

    from_email = 'admin1@gmail.com'
    message = MIMEText(f' Employee with id {employee_id} has updated their task status id {task_id} with project id {project_id}')
    message['Subject'] = 'Task Status'
    message['From'] = from_email
    message['To'] = to_email
    with smtplib.SMTP('localhost', 1025) as smtp:
        smtp.send_message(message)  

# Router for recieving the screenshot from frontend and saving it to the database
@router.post('/upload_screenshot')
async def upload_screenshot( timesheet_id : int, file : UploadFile = File(),
        session : Session = Depends(get_session), current_user : User = Depends(get_current_user())):
        
    content = await file.read()
    directory = "screenshots"
    os.makedirs(directory, exist_ok=True)
    
    filename = f"{current_user.id}_{datetime.utcnow().isoformat().replace(':','-')}.png"
    file_path = os.path.join(directory, filename)
    
    with open(file_path, "wb") as f: # write binary mode 
        f.write(content)
        
    screenshot = Screenshots(
        employee_id=current_user.id,
        timesheet_id=timesheet_id,
        filepath=file_path,
        timestamp=date.today()
    )   
    
    session.add(screenshot)
    session.commit()
    session.refresh(screenshot)
    
    query = select(Timesheet).where(Timesheet.id == timesheet_id)
    execute = session.exec(query).first()
    project = session.exec(select(Projects).where(Projects.id == execute.project_id)).first()
    client = select(User).where(User.id == project.client_id)
    get_client = session.exec(client).first()
    
    email = current_user.email
    connection = active_connections.get(email)
    if connection:
            print("Active Connection", active_connections)
            print("Target email", email) 
            await connection.send_text("Screenshot saved successfully")  
    else:
            print(f"No websocket with email {email} logged in..") 
    
    send_screenshot_email(get_client.email, current_user.id)
    return {"message": "Screenshot received and saved"}
    
def send_screenshot_email(to_email : str, employee_id :int):

    from_email = 'admin1@gmail.com'
    message = MIMEText(f' Employee with id {employee_id} has uploaded a screenshot')
    message['Subject'] = 'Screenshot Update'
    message['From'] = from_email
    message['To'] = to_email
    with smtplib.SMTP('localhost', 1025) as smtp:
        smtp.send_message(message)  