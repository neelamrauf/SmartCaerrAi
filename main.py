import json
import asyncio
from typing import Optional
from fastapi import FastAPI, Form, UploadFile, File, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import Column, Integer, String, Text

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DATABASE_URL = "mysql+aiomysql://root:@127.0.0.1:3306/ansari_intel_v5"

engine = create_async_engine(
    DATABASE_URL, 
    echo=False, 
    pool_pre_ping=True
)

AsyncSessionLocal = sessionmaker(
    engine, 
    class_=AsyncSession, 
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)

Base = declarative_base()

class UserLog(Base):
    __tablename__ = "user_logs"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100))
    action = Column(Text)

@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def save_to_db(username: str, action: str):
    async with AsyncSessionLocal() as session:
        try:
            new_entry = UserLog(username=username, action=action)
            session.add(new_entry)
            await session.commit()
            print(f"DEBUG: Saved to DB -> {username}: {action}")
        except Exception as e:
            print(f"DB_ERROR: {str(e)}")
            await session.rollback()

OPENAI_KEY = "swkzCEdYEQMA"

async def get_ai_analysis(user_input: str):
    system_prompt = """
    You are a Career Expert for ALL fields (Medical, Engineering, Arts, Business).
    Analyze the user's skills and provide realistic jobs.
    You MUST return ONLY a JSON object:
    {
      "onsite": [{"role": "Job Title 1"}, {"role": "Job Title 2"}],
      "remote": [{"role": "Job Title 1"}, {"role": "Job Title 2"}],
      "summary": "2 line practical advice for this specific person"
    }
    """
    try:
        response_text = {
            "onsite": [{"role": "Senior Consultant"}, {"role": "Field Officer"}],
            "remote": [{"role": "Remote Analyst"}, {"role": "Digital Assistant"}],
            "summary": f"Based on your profile, you are well-suited for roles involving {user_input[:20]}."
        }
        return response_text
    except Exception as e:
        return {"onsite": [], "remote": [], "summary": "Error in AI processing."}

@app.post("/api/session/initiate")
async def initiate(username: str = Form(...)):
    await save_to_db(username, "User Session Started / Signed In")
    return {"status": "success", "user": username}

@app.post("/api/assistant/process")
async def process_request(
    username: str = Form(...), 
    message: Optional[str] = Form(None),
    document: Optional[UploadFile] = File(None)
):
    action_desc = message if message else f"Uploaded file: {document.filename if document else 'Unknown'}"
    
    await save_to_db(username, f"Processing: {action_desc[:50]}")

    analysis = await get_ai_analysis(action_desc)

    return {
        "onsite_opportunities": analysis["onsite"],
        "remote_opportunities": analysis["remote"],
        "ai_response": analysis["summary"]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
