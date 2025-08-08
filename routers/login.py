from datetime import timedelta
from typing import Annotated
from database.structure import get_session
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodels.user_usage import User, UserInput, UserLogin
from authentication.jwt_hashing import create_access_token, verify_password, get_hashed_password
from sqlmodel import Session, select




router = APIRouter()

@router.post('/login')
def login_user(user : UserLogin,
               session: Session = Depends(get_session)):
    
    query = select(User).where(User.email == user.email)
    login_user : User = session.exec(query).first()
    if not User:
            raise_error_404()
    
    if not verify_password(user.password, login_user.password,):
        raise_error_404()
        
    access_token = create_access_token(data={'sub':login_user.email, 'id' : login_user.id})
    return {'access_token': access_token, 'token_type': 'bearer'}
    
    
@router.post('/')
def signup_user(user:UserInput, session: Session = Depends(get_session)):
    
        signup = User(name=user.name, email=user.email, password=get_hashed_password(user.password))
        existing_email = select(User).where(User.email == user.email)
        check_existing_email : User = session.exec(existing_email).first()
        if check_existing_email:
            raise HTTPException(status_code= 400, detail='Email already exists')
        
        session.add(signup)
        session.commit()
        session.refresh(signup)
        return "User succesfully signed up"
    
def raise_error_404():
    raise HTTPException(
    status_code=status.HTTP_404_NOT_FOUND,
    detail="User not found",
    headers={"WWW-Authenticate": "Bearer"}
    )
        