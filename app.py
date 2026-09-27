import io 
import json
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Form, UploadFile, File, Depends, status
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from sqlalchemy.orm import Session
import PyPDF2
import docx

from security import hash_password, verify_password, get_curr_user
from database import Base, engine, get_db
from models import User

@asynccontextmanager
def lifespan(app : FastAPI):
    Base.metadata.create_all(bind=engine)
    yield

app = FastAPI(lifespan=lifespan)
app.mount('/static', StaticFiles(directory="static"), name= 'static')
app.add_middleware(SessionMiddleware,secret_key="secret1234")

templates = Jinja2Templates(directory="templates")

@app.get("/", response_class=HTMLResponse)
def home(request : Request, current_user : User = Depends(get_curr_user)):
    if current_user:
        return RedirectResponse("/dashboard",status_code=status.HTTP_302_FOUND)
    return RedirectResponse("/login", status_code=status.HTTP_302_FOUND)
    