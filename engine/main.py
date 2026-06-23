from __future__ import annotations

import json
import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from llm.ollama_client import OllamaClient, DEFAULT_MODEL
from pipeline.reframe_dialogue import finalize_alternative, send_message, start_session
from pipeline.runner import AnalysisPipeline, get_data_dir
from schemas.models import AnalysisRequest, ReframeCandidate

app = FastAPI(title="Chronos Engine")


class ReframeStartRequest(BaseModel):
    run_id: str = Field(alias="runId")
    candidate_id: str = Field(alias="candidateId")
    model: str = DEFAULT_MODEL

    model_config = {"populate_by_name": True}


class ReframeMessageRequest(BaseModel):
    session_id: str = Field(alias="sessionId")
    run_id: str = Field(alias="runId")
    candidate_id: str = Field(alias="candidateId")
    message: str
    model: str = DEFAULT_MODEL

    model_config = {"populate_by_name": True}


class ReframeFinalizeRequest(BaseModel):
    session_id: str = Field(alias="sessionId")
    model: str = DEFAULT_MODEL

    model_config = {"populate_by_name": True}


def _load_candidate(run_id: str, candidate_id: str) -> ReframeCandidate:
    path = get_data_dir() / "analysis" / "runs" / run_id / "reframe_candidates.json"
    if not path.exists():
        raise ValueError("Reframe candidates not found")
    items = json.loads(path.read_text(encoding="utf-8"))
    for item in items:
        if item.get("id") == candidate_id:
            return ReframeCandidate(**item)
    raise ValueError(f"Candidate {candidate_id} not found")


@app.get("/health")
def health():
    llm = OllamaClient()
    ollama_ok, err = llm.check_health()
    llm.close()
    return {
        "python": True,
        "ollama": ollama_ok,
        "ollamaModel": DEFAULT_MODEL,
        "error": err if not ollama_ok else None,
    }


@app.post("/analyze")
async def analyze(request: AnalysisRequest):
    import queue
    import threading

    def generate():
        q: queue.Queue = queue.Queue()
        pipeline = AnalysisPipeline(model=request.model)

        def on_progress(p):
            q.put(
                (
                    "progress",
                    json.dumps(
                        {"type": "progress", "data": p.model_dump(by_alias=True)},
                        ensure_ascii=False,
                    ),
                )
            )

        def run_pipeline():
            try:
                report = pipeline.run(request.run_id, request.entries, on_progress=on_progress)
                complete = json.dumps(
                    {"type": "complete", "data": report.model_dump(by_alias=True)},
                    ensure_ascii=False,
                )
                q.put(("complete", complete))
            except Exception as e:
                error = json.dumps(
                    {"type": "error", "data": {"message": str(e)}},
                    ensure_ascii=False,
                )
                q.put(("error", error))

        threading.Thread(target=run_pipeline, daemon=True).start()

        while True:
            kind, payload = q.get()
            yield f"data: {payload}\n\n"
            if kind in ("complete", "error"):
                break

    return StreamingResponse(generate(), media_type="text/event-stream; charset=utf-8")


@app.post("/reframe/start")
def reframe_start(req: ReframeStartRequest):
    data_dir = get_data_dir()
    candidate = _load_candidate(req.run_id, req.candidate_id)
    llm = OllamaClient(model=req.model)
    try:
        session = start_session(data_dir, req.run_id, candidate, llm)
        return session.model_dump(by_alias=True)
    finally:
        llm.close()


@app.post("/reframe/message")
def reframe_message(req: ReframeMessageRequest):
    data_dir = get_data_dir()
    candidate = _load_candidate(req.run_id, req.candidate_id)
    llm = OllamaClient(model=req.model)
    try:
        session = send_message(data_dir, req.session_id, req.message, candidate, llm)
        return session.model_dump(by_alias=True)
    finally:
        llm.close()


@app.post("/reframe/finalize")
def reframe_finalize(req: ReframeFinalizeRequest):
    data_dir = get_data_dir()
    llm = OllamaClient(model=req.model)
    try:
        session = finalize_alternative(data_dir, req.session_id, llm)
        return session.model_dump(by_alias=True)
    finally:
        llm.close()
