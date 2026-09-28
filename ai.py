import dotenv
import os 
import json
from google import genai
from google.genai import types
from pydantic import BaseModel

dotenv.load_dotenv()

GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

client = genai.Client(api_key=GEMINI_API_KEY) 

class ResumeAnalysis(BaseModel):
    skills : list[str]
    missing_skills : list[str]
    roadmap : list[str]
    interview_questions : list[str]

def analyze_resume(resume_text: str, target_role: str):
    prompt = f'''
    You are a technical hiring manager and senior engineer.
    Evaluate the following resume against the target role: "{target_role}".

    Strict Guidelines:
    1. Extract existing technical skills that match or complement the target role.
    2. Identify critical missing skills and gaps needed for the role.
    3. Generate a concrete preparation roadmap covering only the gap areas.
    4. Provide targeted interview questions relevant to the target role.

    Resume Content:
    {resume_text}
    '''
    try:
        response = client.models.generate_content(
            model='gemini-3.5-flash',
            contents= prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=ResumeAnalysis,
                temperature=0.3
            )
        )
        return json.loads(response.text)
    except Exception as e:
        return {
            "skills": [],
            "missing_skills": [],
            "roadmap": [],
            "interview_questions": [],
            "error": str(e)
        }