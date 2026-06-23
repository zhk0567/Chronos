from __future__ import annotations

import json
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.responses import StreamingResponse

from llm.ollama_client import OllamaClient, DEFAULT_MODEL
from pipeline.runner import AnalysisPipeline
from schemas.models import AnalysisRequest

app = FastAPI(title="Chronos Engine")


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
