from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path

from llm.ollama_client import OllamaClient
from llm.prompts.story import (
    REFRAME_ALTERNATIVE_SYSTEM,
    REFRAME_ALTERNATIVE_USER,
    REFRAME_DIALOGUE_SYSTEM,
    REFRAME_DIALOGUE_USER,
)
from schemas.models import ReframeCandidate, ReframeMessage, ReframeSession

FORBIDDEN_PATTERNS = re.compile(r"你应该|建议你|必须|正确的做法|更好的是")


def sessions_dir(data_dir: Path) -> Path:
    d = data_dir / "reframe" / "sessions"
    d.mkdir(parents=True, exist_ok=True)
    return d


def start_session(
    data_dir: Path,
    run_id: str,
    candidate: ReframeCandidate,
    llm: OllamaClient,
) -> ReframeSession:
    session_id = str(uuid.uuid4())[:8]
    opening = (
        f"我注意到日记中反复出现这样的叙述：「{candidate.problem_statement}」。"
        f"{'也有另一些时刻似乎不同' if candidate.exception_moments else ''}"
        "——如果从另一个角度看，这段经历还可能有哪些不同的理解？"
    )
    if FORBIDDEN_PATTERNS.search(opening):
        opening = f"关于「{candidate.problem_statement[:40]}」，你当时是怎么理解自己的？"

    session = ReframeSession(
        id=session_id,
        runId=run_id,
        candidateId=candidate.id,
        messages=[
            ReframeMessage(
                role="guide",
                text=opening,
                timestamp=datetime.now(timezone.utc).isoformat(),
            )
        ],
        originalNarrative=candidate.problem_statement,
    )
    _save_session(data_dir, session)
    return session


def send_message(
    data_dir: Path,
    session_id: str,
    user_message: str,
    candidate: ReframeCandidate,
    llm: OllamaClient,
) -> ReframeSession:
    session = load_session(data_dir, session_id)
    if not session:
        raise ValueError(f"Session {session_id} not found")

    session.messages.append(
        ReframeMessage(
            role="user",
            text=user_message,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
    )

    history = [{"role": m.role, "text": m.text} for m in session.messages]
    exceptions = [
        {"date": e.date, "text": e.text} for e in candidate.exception_moments[:3]
    ]
    user = REFRAME_DIALOGUE_USER.format(
        problem_statement=candidate.problem_statement,
        exceptions_json=json.dumps(exceptions, ensure_ascii=False),
        history_json=json.dumps(history[-6:], ensure_ascii=False),
        user_message=user_message,
    )

    reply = llm.chat(REFRAME_DIALOGUE_SYSTEM, user)
    if FORBIDDEN_PATTERNS.search(reply):
        reply = "如果朋友遇到类似情况，你会怎么描述他们的处境？"

    session.messages.append(
        ReframeMessage(
            role="guide",
            text=reply.strip(),
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
    )
    _save_session(data_dir, session)
    return session


def finalize_alternative(
    data_dir: Path,
    session_id: str,
    llm: OllamaClient,
) -> ReframeSession:
    session = load_session(data_dir, session_id)
    if not session:
        raise ValueError(f"Session {session_id} not found")

    history = "\n".join(f"{m.role}: {m.text}" for m in session.messages)
    user = REFRAME_ALTERNATIVE_USER.format(
        original=session.original_narrative,
        history=history[-2000:],
    )
    try:
        data = llm.chat_json(REFRAME_ALTERNATIVE_SYSTEM, user)
        session.alternative_story = data.get("alternativeStory")
    except Exception:
        session.alternative_story = "（系统推断）可能存在另一种解读角度，详见对话中的提问与回应。"

    _save_session(data_dir, session)
    return session


def load_session(data_dir: Path, session_id: str) -> ReframeSession | None:
    path = sessions_dir(data_dir) / f"{session_id}.json"
    if not path.exists():
        return None
    return ReframeSession(**json.loads(path.read_text(encoding="utf-8")))


def _save_session(data_dir: Path, session: ReframeSession) -> None:
    path = sessions_dir(data_dir) / f"{session.id}.json"
    path.write_text(
        json.dumps(session.model_dump(by_alias=True), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
