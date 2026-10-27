import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from policy_agent.research import run_research
from policy_agent.skills import list_skills, get_skill

app = FastAPI(title="Climate Policy Agent API", version="2.0.0",
              description="Live multi-source search, webpage extraction and evidence-linked policy passages.")
origin = os.getenv("FRONTEND_ORIGIN", "*").strip()
app.add_middleware(CORSMiddleware,
    allow_origins=["*"] if origin == "*" else [x.strip() for x in origin.split(",") if x.strip()],
    allow_credentials=False, allow_methods=["GET","POST","OPTIONS"], allow_headers=["*"])

class AskRequest(BaseModel):
    question: str = Field(min_length=5, max_length=500)
    location: str = Field(default="India", max_length=100)
    max_results: int = Field(default=8, ge=4, le=10)

@app.get("/")
def root():
    return {"name":"Climate Policy Agent API","status":"ok",
            "serper_configured":bool(os.getenv("SERPER_API_KEY")),"docs":"/docs",
            "mcp_server":"backend/mcp_server.py"}

@app.get("/health")
def health():
    return {"status":"ok","serper_configured":bool(os.getenv("SERPER_API_KEY"))}

@app.get("/api/skills")
def skills():
    return list_skills()

@app.get("/api/skills/{name}")
def skill(name: str):
    try:
        return get_skill(name)
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc

@app.post("/api/ask")
def ask(req: AskRequest):
    try:
        return run_research(req.question, req.location, req.max_results)
    except RuntimeError as exc:
        message = str(exc)
        code = 503 if "SERPER_API_KEY is missing" in message else 502
        raise HTTPException(code, message) from exc
