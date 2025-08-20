from datetime import timedelta, date, datetime
from typing import Annotated
from database.structure import get_session
from fastapi import APIRouter, Depends, HTTPException, status, Query
from datetime import datetime, timedelta
from sqlmodels.user_usage import User, UserInput,AppUsage, Timesheet, Attendance, Timesheet,AppUserLink, Screenshots, Projects, Tasks, Payroll
from authentication.jwt_hashing import create_access_token, verify_password, get_current_user, bearer_scheme, get_hashed_password
from sqlmodel import Session, select
from notifications.ws_router import active_connections
from sqlmodel import SQLModel, delete
router = APIRouter(
    tags=['Admin']
)

@router.post('/create_users')
async def create_users(user:UserInput,
            session: Session = Depends(get_session), current_user : User = Depends(get_current_user())):
    
    if current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Only admins are authorised to perform this action")
                
    else:    
        create = User(name=user.name, role = user.role,email=user.email,
                      password=get_hashed_password(user.password),hourly_rate=user.hourly_rate)
        
        existing_email = select(User).where(User.email == user.email)
        check_existing_email : User = session.exec(existing_email).first()
        if check_existing_email:
            raise HTTPException(status_code= 400, detail='Email already exists')
        if create.role not in ("employee","client"):
            raise HTTPException(status_code=status.HTTP_406_NOT_ACCEPTABLE,
                                  detail = "Role should be a client or an employee")
        
        session.add(create)
        session.commit()
        session.refresh(create)
        email = current_user.email
        connection = active_connections.get(email)
        
        if connection:
            print("Active Connection", active_connections)
            print("Target email", email) 
            await connection.send_text(f"{create.role} successfuly created")  
        else:
            print(f"No websocket with email {email} logged in..") 
        return f"{create.role} succesfully created"
    
# Get Activity    
@router.get('/get_user_activity')
def view_user_activity( employee_id : int ,session:Session = Depends(get_session),
                    current_user : User = Depends(get_current_user())):
    
    if current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Only admins are authorised to perform this action")
        
    query = select(AppUsage).where(AppUsage.employee_id == employee_id, AppUsage.role == "employee")    
    get_activity = session.exec(query).all()
    if get_activity is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail = f"No employee by id {employee_id} found")
    return get_activity    

# Get employee timesheet
@router.get('/get_user_timesheet')
def view_user_timesheet(employee_id : int ,session:Session = Depends(get_session),
                    current_user : User = Depends(get_current_user())):
    
    if current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Only admins are authorised to perform this action")
    
    query = select(Timesheet).where(Timesheet.employee_id == employee_id)    
    get_timesheet = session.exec(query).all()
    if get_timesheet is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail = f"No employee by id {employee_id} found")
    return get_timesheet


# Get employee attendance
@router.post('/get_user_attendance')
def view_user_attendance(employee_id : int ,session:Session = Depends(get_session),
                    current_user : User = Depends(get_current_user())):  
        
    if current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Only admins are authorised to perform this action")
    
    query = select(Attendance).where(Attendance.employee_id == employee_id)    
    get_attendance = session.exec(query).all()
    if get_attendance is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail = f"No employee by id {employee_id} found")
    return get_attendance  


#Viewing payroll
@router.get('/get_user_payroll')
def view_user_payroll(employee_id : int ,session:Session = Depends(get_session),
                    current_user : User = Depends(get_current_user())):
    
    if current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Only admins are authorised to perform this action")
    
    query = select(Payroll).where(Payroll.employee_id == employee_id)    
    get_payroll = session.exec(query).all()
    if get_payroll is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail = f"No employee by id {employee_id} found")
    return get_payroll

# Viewing screenshots
@router.get('/view_screenshot')
def view_screenshot(employee_id:int,
            session:Session = Depends(get_session), current_user : User = Depends(get_current_user())):
    
    if current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Only admins are authorised to perform this action")
    
    query = session.exec(select(Screenshots).where(Screenshots.employee_id == employee_id)).all()
    if not query:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail = "No screenshots found related to this employee")
    return query

@router.delete('/delete_client')
async def delete_client( client_id : int,
    session:Session = Depends(get_session), current_user : User = Depends(get_current_user())):
    
    if current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Only admins are authorised to perform this action")
    
    client = session.get(User, client_id)
    if not client or client.role != 'client': 
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail = f"No client with id {client_id} found")
        
    employees = session.exec(
        select(User.id).where(User.company_id == client_id)
        ).all()
    
    employee_ids = employees 
    session.exec(delete(Timesheet).where(Timesheet.employee_id.in_(employee_ids)))
    session.exec(delete(Attendance).where(Attendance.employee_id.in_(employee_ids)))
    session.exec(delete(AppUsage).where(AppUsage.employee_id.in_(employee_ids)))
    session.exec(delete(Payroll).where(Payroll.employee_id.in_(employee_ids)))
    session.exec(delete(Screenshots).where(Screenshots.employee_id.in_(employee_ids)))
    session.exec(delete(AppUserLink).where(AppUserLink.user_id.in_(employee_ids)))   
    
    projects = session.exec(select(Projects).where(Projects.client_id==client_id)).first()
    session.exec(delete(Tasks).where(Tasks.project_id == projects.id))
    session.exec(delete(Projects).where(Projects.client_id == client_id))
    
    session.delete(client) 
    session.commit()          
        
    email = current_user.email
    connection = active_connections.get(email)
    
    if connection:
        print("Active Connection", active_connections)
        print("Target email", email) 
        await connection.send_text(f"Client and all their related data successfuly removed")  
    else:
        print(f"No websocket with email {email} logged in..") 
        
    return {'message' : 'Client and all their related data has been removed'}    
    