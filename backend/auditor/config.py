from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class AIConfig:
    provider: str = "none"
    azure_openai_endpoint: str = ""
    azure_openai_api_key: str = ""
    azure_openai_deployment: str = ""
    azure_openai_api_version: str = "2024-10-21"
    mistral_api_key: str = ""
    mistral_model: str = "mistral-large-latest"


def load_ai_config() -> AIConfig:
    return AIConfig(
        provider=os.getenv("AUDITOR_AI_PROVIDER", "none").strip().lower(),
        azure_openai_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT", ""),
        azure_openai_api_key=os.getenv("AZURE_OPENAI_API_KEY", ""),
        azure_openai_deployment=os.getenv("AZURE_OPENAI_DEPLOYMENT", ""),
        azure_openai_api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-10-21"),
        mistral_api_key=os.getenv("MISTRAL_API_KEY", ""),
        mistral_model=os.getenv("MISTRAL_MODEL", "mistral-large-latest"),
    )

