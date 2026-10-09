import json

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from agents import route_question
from pipeline import run_research_pipeline, research_graph


app = FastAPI(
    title="Multi-Agent Research System",
    description="AI-powered research system using LangGraph, Gemini and Tavily",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# NEW: serve the frontend files
app.mount("/static", StaticFiles(directory="static"), name="static")


class ResearchRequest(BaseModel):
    topic: str


class ResearchResponse(BaseModel):
    topic: str
    route: str
    answer: str


# CHANGED: "/" now opens the frontend
@app.get("/")
def home():
    return FileResponse("static/index.html")


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.post("/route")
def check_route(request: ResearchRequest):
    topic = request.topic.strip()
    if not topic:
        raise HTTPException(status_code=400, detail="Topic cannot be empty.")
    try:
        return {"topic": topic, "route": route_question(topic)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Router failed: {str(e)}")


@app.post("/research", response_model=ResearchResponse)
def research(request: ResearchRequest):
    topic = request.topic.strip()
    if not topic:
        raise HTTPException(status_code=400, detail="Topic cannot be empty.")
    try:
        result = run_research_pipeline(topic)
        return {
            "topic": topic,
            "route": result.get("route", "UNKNOWN"),
            "answer": result.get("report", "")
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Research pipeline failed: {str(e)}")


# NEW: streams each agent's result to the frontend as it finishes
@app.post("/research/stream")
def research_stream(request: ResearchRequest):
    topic = request.topic.strip()
    if not topic:
        raise HTTPException(status_code=400, detail="Topic cannot be empty.")

    def events():
        try:
            for update in research_graph.stream({"topic": topic}, stream_mode="updates"):
                for node, data in update.items():
                    yield f"data: {json.dumps({'node': node, 'data': data}, default=str)}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'node': 'error', 'data': str(e)})}\n\n"

    return StreamingResponse(events(), media_type="text/event-stream")