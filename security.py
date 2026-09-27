import bcrypt
from fastapi import Request, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session
from database import get_db
from models import User

def hash_password(password : str) -> str:
    password_bytes = password.encode()

    salt = bcrypt.gensalt()

    hashed_passw_bytes = bcrypt.hashpw(password_bytes,salt=salt)

    return hashed_passw_bytes.decode()

def verify_password(plain_passw: str, password_hash : str) -> bool:
    plain_bytes= plain_passw.encode()
    hash_bytes= password_hash.encode()

    return bcrypt.checkpw(plain_bytes, hash_bytes)

def get_curr_user(
        request : Request,
        db : Session = Depends(get_db)
) -> User | None:
    user_email = request.session.get("user")
    if not user_email:
        return None
    return db.scalar(select(User).where(User.email==user_email))