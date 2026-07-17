from __future__ import annotations

import json
from typing import Any, Protocol

from ..config import AIConfig, load_ai_config


class AIClient(Protocol):
    def explain_findings(self, findings: list[dict[str, Any]], language: str = "pt") -> str:
        ...


class NoAIClient:
    def explain_findings(self, findings: list[dict[str, Any]], language: str = "pt") -> str:
        return json.dumps({"language": language, "findings": findings}, ensure_ascii=False, indent=2)


def build_ai_client(config: AIConfig | None = None) -> AIClient:
    cfg = config or load_ai_config()
    # Provider adapters are intentionally not implemented yet. The local audit
    # pipeline must work without external AI first; adapters plug in here.
    if cfg.provider in {"none", "", "local"}:
        return NoAIClient()
    return NoAIClient()
