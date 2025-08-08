from datetime import timedelta
from typing import Annotated
from database.structure import get_session
from fastapi import APIRouter, Depends, HTTPException, status

from sqlmodels.user_usage import User, AppUsage, AppUserLink, UsageCreate
from authentication.jwt_hashing import create_access_token, verify_password, get_current_user, bearer_scheme
from sqlmodel import Session, select


router = APIRouter(
    tags=['Your Activity']
)

@router.get('/activity', dependencies=[Depends(bearer_scheme)])
def see_activity( session:Session = Depends(get_session),
                 current_user: User = Depends(get_current_user)) :
    activity = (select(AppUsage)
    .join(AppUserLink, AppUsage.id == AppUserLink.app_id) # joins usage table with the link table
    .where(AppUserLink.user_id == current_user.id)) # filters by the current user leaving behind rows only 
    # where the user is linked to the app
    user_activity = session.exec(activity).all() # fetches them all
    
    return user_activity

@router.post('/add_activity', dependencies=[Depends(bearer_scheme)])
def add_activity( usage: UsageCreate,session:Session = Depends(get_session),
                 current_user: User = Depends(get_current_user)) :
    add_usage = AppUsage(
        id = usage.id,
        device_id = usage.device_id,
        app = usage.app,
        duration = usage.duration,
        timestamp = usage.timestamp,
        user_id = current_user.id 
    )
    session.add(add_usage)
    session.commit()
    session.refresh(add_usage)
    # Need to update the link table as well
    link = AppUserLink(user_id=current_user.id, app_id=add_usage.id)
    session.add(link)
    session.commit()
    
    return "Record added succesfully"