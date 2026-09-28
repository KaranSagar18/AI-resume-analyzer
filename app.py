import io 
import json
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Form, UploadFile, File, Depends, status
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from sqlalchemy import select
from sqlalchemy.orm import Session
import PyPDF2
import docx

from security import hash_password, verify_password, get_curr_user
from database import Base, engine, get_db
from models import User, Report
from ai import analyze_resume

@asynccontextmanager
async def lifespan(app : FastAPI):
    Base.metadata.create_all(bind=engine)
    yield

app = FastAPI(lifespan=lifespan)
app.mount('/static', StaticFiles(directory="static"), name= 'static')
app.add_middleware(SessionMiddleware,secret_key="secret1234")

templates = Jinja2Templates(directory="templates")

@app.get("/", response_class=HTMLResponse)
async def home(
        request : Request, 
        current_user : User | None = Depends(get_curr_user)
    ):
    if current_user:
        return RedirectResponse("/dashboard",status_code=status.HTTP_302_FOUND)
    
    return RedirectResponse("/login", status_code=status.HTTP_302_FOUND)

@app.get("/signup", response_class=HTMLResponse)
async def signup_page(request : Request):
    return templates.TemplateResponse(
        request,
        "signup.html",
        {"error": None}
    )

@app.post("/signup", response_class= HTMLResponse)
async def signup_post(
    request : Request,
    email : str = Form(...),
    password : str = Form(...),
    db : Session = Depends(get_db)
):
    if db.scalar(select(User).where(User.email== email)):
        return templates.TemplateResponse(
            request,
            "signup.html",
            {"error" : "An account with this email already exists"}
        )
    
    new_user = User(
        email = email,
        hashed_password = hash_password(password)
    )
    db.add(new_user)
    db.commit()
    return RedirectResponse("/login", status.HTTP_201_CREATED)

@app.get("/login", response_class=HTMLResponse)
async def login_page(
    request : Request
):
    return templates.TemplateResponse(request,"login.html",{'error': None})

@app.post('/login', response_class= HTMLResponse)
async def login_post(
    request : Request,
    email : str = Form(...),
    password : str = Form(...),
    db : Session = Depends(get_db)
):
    user = db.scalar(select(User).where(User.email==email))
    if not user :
        return templates.TemplateResponse(
            request,
            "login.html",
            {"error" : "Invalid Email"}
        )
    if not verify_password(password, user.hashed_password):
        return templates.TemplateResponse(
            request,
            "login.html",
            {"error" : "Invalid Password"}
        )
    
    request.session['user'] = user.email
    return RedirectResponse("/dashboard",status.HTTP_302_FOUND)

@app.get('/logout')
async def logout(
    request : Request
):
    request.session.pop("user", None)
    return RedirectResponse("/login", status.HTTP_302_FOUND)

@app.get("/dashboard")
async def dahboard_page(
    request : Request,
    current_user : User | None = Depends(get_curr_user)
):
    if not current_user:
        return RedirectResponse('/login',status.HTTP_401_UNAUTHORIZED)

    return templates.TemplateResponse(
        request,
        'dashboard.html',
        {'user' : current_user.email}
    )

@app.post("/dashboard", response_class=HTMLResponse)
async def dashboard(
    request : Request,
    target_role : str = Form(...),
    resume_text : str | None = Form(None),
    resume_file : UploadFile | None = Form(None),
    current_user : User = Depends(get_curr_user),
    db : Session = Depends(get_db)
):
    if not current_user:
        return RedirectResponse("/login",status.HTTP_401_UNAUTHORIZED)
    extracted_content = (resume_text or "").strip()
    if resume_file and resume_file.filename:
        file_bytes = await resume_file.read() 
        filename = resume_file.filename.lower()
        if filename.endswith('.pdf'):
            reader = PyPDF2.PdfReader(io.BytesIO(file_bytes))
            extracted_content += "\n" + "\n".join([page.extract_text() or '' for page in reader.pages])
        elif filename.endswith('.docx','.doc'):
            doc = docx.Document(io.BytesIO(file_bytes))
            extracted_content += "\n" + "\n".join([p.text for p in doc.paragraphs])

        result = None

        if extracted_content.strip():
            result = analyze_resume(extracted_content,target_role)
            report = Report(
                user_id = current_user.id,
                resume_text = extracted_content,
                result = json.dumps(result)
            )
            db.add(report)
            db.commit()
        else:
            result = {"error": "Please provide resume text or upload a PDF/DOCX file."}

        return templates.TemplateResponse(
            request,
            "dashboard.html",
            {
                "user" : current_user.email,
                "result" : result
            }
        )

@app.get("/history")
def history(
    request : Request,
    current_user : User = Depends(get_curr_user),
    db : Session = Depends(get_db)
):
    if not current_user:
        return RedirectResponse("/login", status.HTTP_401_UNAUTHORIZED)
    user_reports = current_user.reports
    reports_data = [
        {
            "resume" : r.resume_text,
            "result" : json.loads(r.result) if r.result else {}
        }
        for r in user_reports
    ]
    reports_data = reports_data[::-1]
    return templates.TemplateResponse(
        request,
        'history.html',
        {'reports' : reports_data}
    )
    