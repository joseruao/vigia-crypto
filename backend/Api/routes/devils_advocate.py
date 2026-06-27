from __future__ import annotations

import hmac
import logging
import os
import time
from collections import deque
from typing import Literal

from fastapi import APIRouter, File, Form, Header, HTTPException, Request, UploadFile
from starlette.concurrency import run_in_threadpool

from Api.services.devils_advocate import (
    DevilsAdvocateAnalyzeResult,
    analyze_document,
    extract_upload_text,
)

log = logging.getLogger("vigia.devils_advocate")
router = APIRouter(prefix="/api/devils-advocate", tags=["devils-advocate"])

# Per-IP rate limit (in-memory, per-process). Defence in depth on top of the
# access code — caps how fast a single client can spend OpenAI credits.
RATE_LIMIT_MAX = int(os.getenv("DEVILS_ADVOCATE_RATE_LIMIT_MAX", "40"))
RATE_LIMIT_WINDOW_SECONDS = int(os.getenv("DEVILS_ADVOCATE_RATE_LIMIT_WINDOW", "3600"))
_REQUEST_LOG: dict[str, deque[float]] = {}


def _check_access_code(provided: str | None) -> None:
    """Fail closed: if no access code is configured, the endpoint is disabled.

    This prevents the OpenAI-spending endpoint from ever being publicly open
    just because an env var was forgotten in a deploy.
    """
    expected = os.getenv("DEVILS_ADVOCATE_ACCESS_CODE", "")
    if not expected:
        log.error("DEVILS_ADVOCATE_ACCESS_CODE not set; refusing analysis requests")
        raise HTTPException(
            status_code=503,
            detail="Devil's Advocate is not configured for access. Set DEVILS_ADVOCATE_ACCESS_CODE.",
        )
    if not provided or not hmac.compare_digest(provided.strip(), expected):
        raise HTTPException(status_code=401, detail="Invalid or missing access code.")


def _check_rate_limit(client_ip: str) -> None:
    now = time.time()
    window_start = now - RATE_LIMIT_WINDOW_SECONDS
    hits = _REQUEST_LOG.setdefault(client_ip, deque())
    while hits and hits[0] < window_start:
        hits.popleft()
    if len(hits) >= RATE_LIMIT_MAX:
        raise HTTPException(
            status_code=429,
            detail="Too many requests. Please wait before analysing more documents.",
        )
    hits.append(now)


@router.post("/analyze", response_model=DevilsAdvocateAnalyzeResult)
async def analyze_devils_advocate(
    request: Request,
    file: UploadFile = File(...),
    jurisdiction: str = Form(default="Portugal"),
    legal_area: str = Form(default="Fiscal"),
    document_type: str = Form(default="Documento fiscal"),
    represented_side: str = Form(default="Contribuinte"),
    objective: str = Form(default="Encontrar argumentos, riscos e pontos a verificar"),
    language: Literal["pt", "en"] = Form(default="pt"),
    x_access_code: str | None = Header(default=None),
):
    _check_access_code(x_access_code)
    _check_rate_limit(request.client.host if request.client else "unknown")
    try:
        extracted_text, content_truncated = await extract_upload_text(file)
        return await run_in_threadpool(
            analyze_document,
            document_name=file.filename or "documento",
            extracted_text=extracted_text,
            jurisdiction=jurisdiction.strip() or "Portugal",
            legal_area=legal_area.strip() or "Fiscal",
            document_type=document_type.strip() or "Documento fiscal",
            represented_side=represented_side.strip() or "Contribuinte",
            objective=objective.strip() or "Encontrar argumentos, riscos e pontos a verificar",
            language=language,
            content_truncated=content_truncated,
        )
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        log.error("devils-advocate analyze failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Devil's Advocate analysis failed") from exc
