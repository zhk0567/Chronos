from __future__ import annotations

import json
import re
from typing import Any, Optional

import httpx

from schemas.models import Evidence, EvidenceSource


DEFAULT_OLLAMA_URL = "http://127.0.0.1:11434"
DEFAULT_MODEL = "minimax-m3:cloud"


class OllamaClient:
    def __init__(self, base_url: str = DEFAULT_OLLAMA_URL, model: str = DEFAULT_MODEL):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self._client = httpx.Client(timeout=120.0)

    def check_health(self) -> tuple[bool, Optional[str]]:
        try:
            res = self._client.get(f"{self.base_url}/api/tags")
            if res.status_code != 200:
                return False, f"Ollama HTTP {res.status_code}"
            return True, None
        except Exception as e:
            return False, str(e)

    def chat_json(self, system: str, user: str, retries: int = 1) -> dict[str, Any]:
        last_err: Optional[Exception] = None
        for attempt in range(retries + 1):
            try:
                raw = self._chat(system, user)
                return self._parse_json(raw)
            except Exception as e:
                last_err = e
                if attempt < retries:
                    user = user + "\n\n请严格输出合法 JSON，不要包含 markdown 代码块。"
        raise RuntimeError(f"LLM JSON parse failed: {last_err}")

    def chat(self, system: str, user: str) -> str:
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "stream": False,
        }
        res = self._client.post(f"{self.base_url}/api/chat", json=payload)
        res.raise_for_status()
        data = res.json()
        return data.get("message", {}).get("content", "")

    def _chat(self, system: str, user: str) -> str:
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "stream": False,
            "format": "json",
        }
        res = self._client.post(f"{self.base_url}/api/chat", json=payload)
        res.raise_for_status()
        data = res.json()
        return data.get("message", {}).get("content", "")

    def _parse_json(self, text: str) -> dict[str, Any]:
        text = text.strip()
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\s*", "", text)
            text = re.sub(r"\s*```$", "", text)
        return json.loads(text)

    def close(self) -> None:
        self._client.close()


def make_evidence(
    date: str,
    text: str,
    char_offset: Optional[int] = None,
    char_length: Optional[int] = None,
    source: EvidenceSource = EvidenceSource.INFERRED,
) -> Evidence:
    return Evidence(
        date=date,
        text=text[:200],
        charOffset=char_offset,
        charLength=char_length,
        source=source,
    )
