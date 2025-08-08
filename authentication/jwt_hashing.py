from datetime import datetime, timedelta
from typing import Dict
from database.structure import get_session
from decouple import config
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer,HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlmodels.user_usage import User
from sqlmodel import Session, select
import bcrypt
from typing import Annotated, Optional
from datetime import timedelta, timezone
# Hashing logic

pwd = CryptContext(schemes = ['bcrypt'], deprecated = 'auto')
def get_hashed_password(password:str):
    return pwd.hash(password)

def verify_password(plain_pass:str, hashed_pass : str):
    return pwd.verify(plain_pass, hashed_pass)


# JWT Logic

SECRET_KEY: str = config('SECRET_KEY', cast=str, default='secret')
ALGORITHM: str = config('ALGORITHM', cast=str, default='HS256')
ACCESS_TOKEN_EXPIRE_MINUTES = 3000000

bearer_scheme = HTTPBearer()

def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) +( expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt



def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(bearer_scheme)],
    session: Session = Depends(get_session),
    #required_role: Optional[str] = None
):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str | None = payload.get("sub")
        user_id: int | None = payload.get("id")
        if username is None or user_id is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials")
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials")

    query = select(User).where(User.email == username, User.id == user_id)
    user = session.exec(query).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Could not find user.....")

    return user