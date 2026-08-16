from __future__ import annotations

import json
import re
from typing import Any, Callable, Protocol

from openai import AzureOpenAI

from ..config import AIConfig, load_ai_config

# gpt-5-mini é modelo de raciocínio: precisa de max_completion_tokens generoso,
# senão gasta tudo a "pensar" e devolve resposta vazia.
DEFAULT_MAX_COMPLETION_TOKENS = 4096
# api-version que funciona nesta conta (2025-01-01 devolve 404 - quirk Azure for Students)
DEFAULT_API_VERSION = "2024-10-21"
# Acima disto o documento é truncado para extração (e assinalado no relatório)
MAX_CHARS_PER_DOC = 40_000

LogCall = Callable[[dict[str, Any]], None]


class AIClient(Protocol):
    def extract_json(self, prompt: str, max_tokens: int = DEFAULT_MAX_COMPLETION_TOKENS) -> dict[str, Any]:
        ...

    def explain_findings(self, findings: list[dict[str, Any]], language: str = "pt") -> str:
        ...


class NoAIClient:
    """Fallback offline: devolve JSON vazio/estrutura mínima (nunca inventa valores)."""

    def extract_json(self, prompt: str, max_tokens: int = DEFAULT_MAX_COMPLETION_TOKENS) -> dict[str, Any]:
        return {"error": "no_ai_provider"}

    def explain_findings(self, findings: list[dict[str, Any]], language: str = "pt") -> str:
        return ""


def _strip_code_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\n?", "", text)
        text = re.sub(r"\n?```$", "", text)
    return text.strip()


class AzureOpenAIClient:
    def __init__(self, config: AIConfig, log_call: LogCall | None = None) -> None:
        self.cfg = config
        self.log_call = log_call
        self._client = AzureOpenAI(
            azure_endpoint=config.azure_openai_endpoint,
            api_key=config.azure_openai_api_key,
            api_version=config.azure_openai_api_version or DEFAULT_API_VERSION,
        )

    def _chat(self, messages: list[dict[str, str]], max_tokens: int) -> str:
        resp = self._client.chat.completions.create(
            model=self.cfg.azure_openai_deployment,
            messages=messages,
            max_completion_tokens=max_tokens,
        )
        if self.log_call is not None:
            usage = resp.usage
            self.log_call(
                {
                    "model": resp.model or self.cfg.azure_openai_deployment,
                    "prompt_tokens": usage.prompt_tokens if usage else None,
                    "completion_tokens": usage.completion_tokens if usage else None,
                    "total_tokens": usage.total_tokens if usage else None,
                    "reasoning_tokens": (
                        getattr(getattr(usage, "completion_tokens_details", None), "reasoning_tokens", None)
                        if usage
                        else None
                    ),
                }
            )
        return resp.choices[0].message.content or ""

    def extract_json(self, prompt: str, max_tokens: int = DEFAULT_MAX_COMPLETION_TOKENS) -> dict[str, Any]:
        """Pede JSON estruturado à IA. Tenta 2x; nunca devolve valores inventados."""
        instruction = (
            "\n\nResponde APENAS com JSON válido, sem markdown, sem texto extra. "
            "Campos que não existam no documento ficam como null (nunca inventes)."
        )
        attempts = 0
        last_error = "sem resposta"
        while attempts < 2:
            attempts += 1
            try:
                content = self._chat(
                    [
                        {
                            "role": "system",
                            "content": "És um extractor de documentos financeiros. Só devolves JSON estruturado, fiel ao documento.",
                        },
                        {"role": "user", "content": prompt + instruction},
                    ],
                    max_tokens=max_tokens,
                )
                cleaned = _strip_code_fences(content)
                parsed = json.loads(cleaned)
                if isinstance(parsed, dict):
                    return parsed
                last_error = "JSON não é objeto"
            except Exception as exc:  # noqa: BLE001 - falha de parse/API -> tentar de novo
                last_error = str(exc)[:200]
        return {"error": "ai_parse_failed", "detail": last_error}

    def explain_findings(self, findings: list[dict[str, Any]], language: str = "pt") -> str:
        if not findings:
            return ""
        prompt = (
            "Tens estes achados de auditoria (calculados por regras, com evidência):\n"
            + json.dumps(findings, ensure_ascii=False, indent=2)
            + "\n\nEscreve um resumo executivo em português, curto e concreto, "
            "sem inventar números. Máx. 150 palavras."
        )
        try:
            content = self._chat(
                [
                    {
                        "role": "system",
                        "content": f"Escreves relatórios de auditoria em {language}. Só usas os dados fornecidos.",
                    },
                    {"role": "user", "content": prompt},
                ],
                max_tokens=1500,
            )
            return content.strip()
        except Exception as exc:  # noqa: BLE001
            return f"(resumo IA indisponível: {str(exc)[:120]})"


def build_ai_client(config: AIConfig | None = None, log_call: LogCall | None = None) -> AIClient:
    cfg = config or load_ai_config()
    if cfg.provider in {"azure_openai", "azure"} and cfg.azure_openai_endpoint and cfg.azure_openai_api_key:
        return AzureOpenAIClient(cfg, log_call=log_call)
    if cfg.provider in {"mistral"}:
        # Mistral fica como pendência — o providers.py já tem o slot; ver NOTES.md
        return NoAIClient()
    return NoAIClient()
