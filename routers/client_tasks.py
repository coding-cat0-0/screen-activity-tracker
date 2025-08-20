from datetime import timedelta, date, datetime
from typing import Annotated
from database.structure import get_session
from fastapi import APIRouter, Depends, HTTPException, status, Query
from datetime import datetime, timedelta
from sqlmodels.user_usage import User, UserInput,UpdateUser,AppUsage, Timesheet,AppUserLink, Attendance,UsageCreate, Timesheet, ProjectInput, Projects, Tasks, Payroll,Screenshots, UpdateTask, UpdateProject
from authentication.jwt_hashing import create_access_token, verify_password, get_current_user, bearer_scheme, get_hashed_password
from sqlmodel import Session, select, delete
from notifications.ws_router import active_connections
from email.mime.text import MIMEText
import smtplib
import asyncio
from notifications.ws_router import active_connections

router = APIRouter(
    tags=['Client']
)

# Creating employess
@router.post('/create_employees')
def create_employees(user:UserInput,
            session: Session = Depends(get_session), current_user : User = Depends(get_current_user())):
    
    if current_user.role != "client":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Only clients are authorised to perform this action")
                
    else:    
        create = User(name=user.name, role = user.role,company_id = current_user.id, email=user.email,
                      password=get_hashed_password(user.password),hourly_rate=user.hourly_rate)
        
        existing_email = select(User).where(User.email == user.email)
        check_existing_email : User = session.exec(existing_email).first()
        if check_existing_email:
            raise HTTPException(status_code= 400, detail='Email already exists')
        if create.role != "employee":

            raise HTTPException(status_code=status.HTTP_406_NOT_ACCEPTABLE,
                                detail = "Role should be employee")
        
        session.add(create)
        session.commit()
        session.refresh(create)
        return "Employee succesfully created"
    
# Posting projects    
@router.post('/post_projects')
async def upload_projects(enter_projects : ProjectInput,
                    session:Session = Depends(get_session), current_user : User = Depends(get_current_user())):
    
    if current_user.role != "client":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Only clients are authorised to perform this action")       
    else:
        upload = Projects(
            client_id= current_user.id,
            name = enter_projects.name,
            description = enter_projects.description,
            status = None
        )    
        session.add(upload)
        session.commit()
        session.refresh(upload)
        
        email = current_user.email
# Websocket logic for running task in the background   
        if email in active_connections:
            asyncio.create_task(
                send_notification(
                    email,
                    "Project posted successfully"
            )
        )
        
        return {'message' : 'Project has been posted successfully'}
    
async def send_notification(email:str, message:str):
    #print(f"Sending notification to {email}: {message}")
    if email in active_connections:
        await active_connections[email].send_json({
            "type": "project posted",
            "message": message
        })     
    
# Posting tasks    
@router.post('/post_tasks')
async def upload_tasks(project_id : int, name :str, description : str, employee_id : int,
    session:Session = Depends(get_session), current_user : User = Depends(get_current_user())):
    
    if current_user.role != "client":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Only clients are authorised to perform this action")
    
    else:
        query = select(Projects).where(Projects.id == project_id)
        confirm = session.exec(query).first()
        user_query = select(User).where(User.id == employee_id, User.role == "employee")
        confirm_employee = session.exec(user_query).first()
        if confirm and confirm_employee:
            upload = Tasks(
                project_id= project_id,
                name = name,
                description = description,
                assigned_to= employee_id,
                status = "Inactive"
            )    
        session.add(upload)
        session.commit()
        session.refresh(upload)
        
        send_task_email(current_user.email, confirm_employee.email, project_id)
        
        email = current_user.email
        connection = active_connections.get(email)
        if connection:
            print("Active Connection", active_connections)
            print("Target email", email) 
            await connection.send_text(f"Email has been sent to{ confirm_employee.email}")  
        else:
            print(f"No websocket with email {email} logged in..") 
            
        return {'message' : 'Task has been uploaded successfully'}     

def send_task_email(from_email : str,to_email : str,
                    project_id : int):

    message = MIMEText(f'A task has been uploaded for you of  project id {project_id}')
    message['Subject'] = 'New Task'
    message['From'] = from_email
    message['To'] = to_email
    with smtplib.SMTP('localhost', 1025) as smtp:
        smtp.send_message(message)       
  
# Get Activity    
@router.get('/get_activity')
def view_activity( employee_id : int ,session:Session = Depends(get_session),
                    current_user : User = Depends(get_current_user())):
    
    if current_user.role != "client":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Only clients are authorised to perform this action")
        
    query = select(AppUsage).where(AppUsage.employee_id == employee_id, AppUsage.role == "employee")    
    get_activity = session.exec(query).all()
    if get_activity is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail = f"No employee by id {employee_id} found")
    return get_activity

# Get employee timesheet
@router.get('/get_timesheet')
def view_timesheet(employee_id : int ,session:Session = Depends(get_session),
                    current_user : User = Depends(get_current_user())):
    
    if current_user.role != "client":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Only clients are authorised to perform this action")
    
    query = select(Timesheet).where(Timesheet.employee_id == employee_id)    
    get_timesheet = session.exec(query).all()
    if get_timesheet is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail = f"No employee by id {employee_id} found")
    return get_timesheet

# Get employee attendance
@router.post('/get_attendance')
def view_attendance(employee_id : int ,session:Session = Depends(get_session),
                    current_user : User = Depends(get_current_user())):  
        
    if current_user.role != "client":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Only clients are authorised to perform this action")
    
    query = select(Attendance).where(Attendance.employee_id == employee_id)    
    get_attendance = session.exec(query).all()
    if get_attendance is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail = f"No employee by id {employee_id} found")
    return get_attendance  

# Generating payroll
@router.post('/payroll')
async def generate_payroll(employee_id : int,project_id: int, task_id : int, session:Session = Depends(get_session),
                 current_user : User = Depends(get_current_user())):
    
    if current_user.role != "client":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Only clients are authorised to perform this action")
    check_status = select(Projects).where(Projects.id == project_id,
                            Projects.status == "completed")
    check = session.exec(check_status).first()
    if check:
        query = select(Timesheet).where(Timesheet.employee_id == employee_id,
                    Timesheet.project_id == project_id, Timesheet.task_id == task_id)
        rows = session.exec(query).all()
        if not rows:
                    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail = f"No movie by id {employee_id} found") 
        total = sum(ts.total_hrs for ts in rows)
        
        employee = select(User).where(User.id == employee_id)
        execute = session.exec(employee).first()
        if execute is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail = f"No movie by id {employee_id} found") 
         
        pay = total * execute.hourly_rate  
        payroll = Payroll(
            employee_id = employee_id,
            project_id = project_id,
            task_id = task_id,
            project_status = "completed",           
            hours_worked= total,
            hourly_rate= execute.hourly_rate,
            total_amount = pay        
        )     
        session.add(payroll)
        session.commit()
        session.refresh(payroll)
        
        email = current_user.email
        connection = active_connections.get(email)
        
        if connection:
            print("Active Connection", active_connections)
            print("Target email", email) 
            await connection.send_text(f"Payroll successfuly uploaded")  
        else:
            print(f"No websocket with email {email} logged in..") 
                  
        return {'message' : 'payroll has been uploaded'}
    
    else:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail =f"Project with id {project_id} is either not completed or not found")

#Viewing payroll
@router.get('/get_payroll')
def view_payroll(employee_id : int ,session:Session = Depends(get_session),
                    current_user : User = Depends(get_current_user())):
    
    if current_user.role != "client":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Only clients are authorised to perform this action")
    
    query = select(Payroll).where(Payroll.employee_id == employee_id)    
    get_payroll = session.exec(query).all()
    if get_payroll is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail = f"No employee by id {employee_id} found")
    return get_payroll

# Viewing screenshots
@router.put('/update_project_status')
def update_project_status(project_id : int, update : str,
                          session:Session = Depends(get_session), current_user : User = Depends(get_current_user())):
    
    if current_user.role != "client":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Only clients are authorised to perform this action")
    
    update_project = select(Projects).where(Projects.id == project_id)
    change = session.exec(update_project).all()    
    if not change:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail = f"No project by id {project_id} found")
        
    query = select(Tasks).where(Tasks.project_id == project_id)
    rows = session.exec(query).all()
    for row in rows:
        if row.status != "Completed":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                                default = "Project status cannot be updated if it is not completed")
    for x in change:    
        x.status = update.lower()   

    session.commit()
   
    return {'message' : 'project status has been updated'}

# Router for getting screenshot
@router.get('/view_screenshot')
def view_screenshot(employee_id:int,
            session:Session = Depends(get_session), current_user : User = Depends(get_current_user())):
    
    if current_user.role != "client":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Only clients are authorised to perform this action")
    
    query = session.exec(select(Screenshots).where(Screenshots.employee_id == employee_id)).all()
    if not query:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail = "No screenshots found related to this employee")
    return query    

# Update task
@router.put('/update_task_details')
async def update_task_details(task_id :int, update_task : UpdateTask,
    session:Session= Depends(get_session), current_user : User = Depends(get_current_user())):
    
    query = session.exec(select(Tasks).where(Tasks.id == task_id)).first()
    if query:
        for key, value in update_task.model_dump(exclude_unset=True).items():
            if value not in (None, "", "string", 0):
                setattr(query, key, value)
        session.add(query)
        session.commit()
        
    else:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Task of id {task_id} not found") 
    email = current_user.email
    connection = active_connections.get(email)
        
    if connection:
            print("Active Connection", active_connections)
            print("Target email", email) 
            await connection.send_text(f"Task successfuly updated")   
    else:
            print(f"No websocket with email {email} logged in..") 
    return {'messgae' : 'Task has been updated'}    
        
# Update project details
@router.put('/update_project_details')
async def update_project_details(project_id :int, update_project : UpdateProject,
    session:Session= Depends(get_session), current_user : User = Depends(get_current_user())):
    
    query = session.exec(select(Projects).where(Projects.id == project_id)).first()
    if query:
        for key, value in update_project.model_dump(exclude_unset=True).items():
            if value not in (None, "", "string", 0):
                setattr(query, key, value)
        session.add(query)
        session.commit()
        
    else:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Project of id {project_id} not found") 
    
    email = current_user.email
    connection = active_connections.get(email)
        
    if connection:
            print("Active Connection", active_connections)
            print("Target email", email) 
            await connection.send_text(f"Project successfuly updated")  
    else:
            print(f"No websocket with email {email} logged in..") 
    
    return {'message' : 'Project has been updated'}   

# Update project details
@router.put('/update_employee_details')
async def update_employee_details(employee_id :int, update_employee : UpdateUser,
    session:Session= Depends(get_session), current_user : User = Depends(get_current_user())):
    
    query = session.exec(select(User).where(User.id == employee_id)).first()
    if query:
        for key, value in update_employee.model_dump(exclude_unset=True).items():
            if value not in (None, "", "string", 0):
                if key == "email":
                    existing_email = select(User).where(User.email == value)
                    check_existing_email : User = session.exec(existing_email).first()
                    if check_existing_email:
                        raise HTTPException(status_code= 400, detail='Email already exists')
                if key == "password":
                    value = get_hashed_password(value)
                setattr(query, key, value)
        session.add(query)
        session.commit()
         
    else:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Employee of id {employee_id} not found") 
    
    email = current_user.email
    connection = active_connections.get(email)
        
    if connection:
            print("Active Connection", active_connections)
            print("Target email", email) 
            await connection.send_text(f"Employee successfuly updated")  
    else:
            print(f"No websocket with email {email} logged in..") 
    
    return {'message' : 'Employee has been updated'}   
 

@router.delete('/delete_employee')
async def delete_employee( employee_id : int,
    session:Session = Depends(get_session), current_user : User = Depends(get_current_user())):
    
    if current_user.role != "client":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Only clients are authorised to perform this action")
    
    employee = session.get(User, employee_id)
    if not employee or employee.role != 'employee': 
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail = f"No employee with id {employee_id} found")
        
    session.exec(delete(Timesheet).where(Timesheet.employee_id == employee_id))
    session.exec(delete(Attendance).where(Attendance.employee_id == employee_id))
    session.exec(delete(AppUsage).where(AppUsage.employee_id == employee_id))
    session.exec(delete(Payroll).where(Payroll.employee_id == employee_id))
    session.exec(delete(Screenshots).where(Screenshots.employee_id == employee_id))
    session.exec(delete(AppUserLink).where(AppUserLink.user_id == employee_id))   
    
    projects = session.exec(select(Projects.id).where(Projects.client_id == current_user.id)).first()
    session.exec(delete(Tasks).where(Tasks.project_id == projects))
    session.delete(employee)
    session.delete(projects)
    session.commit()          
        
    email = current_user.email
    connection = active_connections.get(email)
    
    if connection:
        print("Active Connection", active_connections)
        print("Target email", email) 
        await connection.send_text(f"Employee and all their related data successfuly removed")  
    else:
        print(f"No websocket with email {email} logged in..") 
        

    return {'message' : 'Employee and all their related data has been removed'}     