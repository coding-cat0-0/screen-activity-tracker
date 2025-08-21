from datetime import datetime, date
from sqlmodel import SQLModel, Field, Relationship
from pydantic import field_validator 
import re
from typing import Optional

class UsageCreate(SQLModel):
    device_id : str
    app : str
    duration : int
    timestamp : datetime
    
class AppUserLink(SQLModel, table=True):
    app_id :int = Field(foreign_key="appusage.id", primary_key=True)
    user_id : int = Field(foreign_key="user.id", primary_key=True)      
    
class AppUsage(SQLModel, table=True):
    id : int = Field(default = None, primary_key=True)
    employee_id : int = Field(foreign_key="user.id") 
    role : str = Field(foreign_key="user.role")
    device_id : str
    app : str
    duration : int
    timestamp : datetime
    users : list["User"] = Relationship(back_populates="app_usage",link_model=AppUserLink)
    
  
class UserInput(SQLModel):
    name : str
    role : str 
    email : str
    password: str
    hourly_rate : Optional[int] = Field(default=None)
    @field_validator('email')
    def email_must_be_valid(cls, v):    
        if not re.search(r"\w+@(\w+\.)?\w+\.(com)$",v, re.IGNORECASE):
            raise ValueError("Invalid email format")
        else:
            return v
          
    @field_validator('password')    
    def password_must_be_strong(cls, p):
             if not re.search(r"^(?=.*[A-Z])(?=.*[a-z])(?=.*\d)(?=.*[!@#$%&*^_-])[A-Za-z\d!@#$%^&_*-]{8,}$",p):
                 raise ValueError("Invalid Password")
             else:
                    return p
                
class UserLogin(SQLModel):
    email : str
    password: str
    @field_validator('email')
    def email_must_be_valid(cls, v):    
        if not re.search(r"\w+@(\w+\.)?\w+\.(com)$",v, re.IGNORECASE):
            raise ValueError("Invalid email format")
        else:
            return v
          
    @field_validator('password')    
    def password_must_be_strong(cls, p):
             if not re.search(r"^(?=.*[A-Z])(?=.*[a-z])(?=.*\d)(?=.*[!@#$%&*^_-])[A-Za-z\d!@#$%^&_*-]{8,}$",p):
                 raise ValueError("Invalid Password")
             else:
                    return p
    
class ForgetPassword(SQLModel):
    otp : str
    email : str
    password : str 
    @field_validator('email')
    def email_must_be_valid(cls, v):    
        if not re.search(r"\w+@(\w+\.)?\w+\.(com)$",v, re.IGNORECASE):
            raise ValueError("Invalid email format")
        else:
            return v
    @field_validator('password')    
    def password_must_be_strong(cls, p):
             if not re.search(r"^(?=.*[A-Z])(?=.*[a-z])(?=.*\d)(?=.*[!@#$%&*^_-])[A-Za-z\d!@#$%^&_*-]{8,}$",p):
                 raise ValueError("Invalid Password")
             else:
                    return p    
                       
class UpdateUser(SQLModel):
    name : Optional[str]
    role:Optional[str]
    company_id : Optional[int]
    email : Optional[str]
    password : Optional[str]
    hourly_rate : Optional[str]
    
        
class User(SQLModel, table=True):
    id : int = Field(default = None, primary_key=True)
    name : str
    role : str = Field(default ="client")
    company_id :Optional[int] = Field(default=None, foreign_key="user.id")
    email : str
    password: str
    app_usage : list[AppUsage] = Relationship(back_populates= "users",
                link_model=AppUserLink)
    role : str = Field(default = "client", nullable = False)
    hourly_rate : int = Field(default=None, nullable= True)
    otp_code : str = Field(default=None, nullable= True)
    otp_created_at : datetime = Field(default=None, nullable= True)
    
class ProjectInput(SQLModel):
        name : str 
        description : str
        
class Projects(SQLModel, table=True):    
       id : int = Field(default=None, primary_key=True)
       client_id : int = Field(foreign_key="user.id")
       name : str = Field(default=None)
       description : str = Field(default=None)
       status: str = Field(default="None")
       
class UpdateProject(SQLModel):
    client_id : Optional[int]
    name : Optional[str]
    description : Optional[str]
    status : Optional[str]       
        
class Tasks(SQLModel, table=True):
    id : int = Field(default = None, primary_key=True)
    project_id : int = Field(foreign_key="projects.id")
    name : str = Field(default=None)
    description : str = Field(default=None)
    assigned_to : int = Field(foreign_key="user.id")
    status: str = Field(default="Inactive")
    
class UpdateTask(SQLModel):
    project_id : Optional[int]
    name : Optional[str]
    description : Optional[str]
    assigned_to : Optional[str]
    status : Optional[str]
        
class Timesheet(SQLModel, table=True):
    id : int = Field(default = None, primary_key=True)
    employee_id : int = Field(foreign_key="user.id")
    current_date : date = Field(default = date.today(), nullable = False)
    project_id : int = Field(foreign_key="projects.id")
    task_id :  int = Field(foreign_key="tasks.id")
    start_time : Optional[datetime] = Field(default = None, nullable = False)
    stop_time :  Optional[datetime] = Field(default = None, nullable = False)
    total_hrs : float = Field(default = 0.0)
    status : str = Field(default = "Inactive")
    
     
class Attendance(SQLModel, table=True):
    id : int = Field(default = None, primary_key=True)
    employee_id : int = Field(foreign_key="user.id")
    current_date : date = Field(default = date.today(), nullable = False)
    status : str = Field(default = "Absent")
    
class Payroll(SQLModel, table=True):
    id : int = Field(default = None, primary_key=True)
    employee_id : int = Field(foreign_key='user.id')
    project_id  : int = Field(foreign_key='projects.id')
    task_id : int = Field(foreign_key='tasks.id')
    project_status: str = Field(default="Inactive")
    hours_worked : int = Field(foreign_key='timesheet.total_hrs')
    hourly_rate  : int = Field(foreign_key='user.hourly_rate')
    total_amount : int = Field(default=None)
    
class Screenshots(SQLModel, table=True):
    id : int = Field(default = None, primary_key=True)
    employee_id : int = Field(foreign_key="user.id")
    timesheet_id : int = Field(foreign_key="timesheet.id")
    filepath : str = Field(default=None)
    timestamp : date = Field(default = date.today(), nullable = False)
        