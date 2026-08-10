from __future__ import annotations

import asyncio
import hmac
import json
import logging
import os
import queue
import time
import uuid
from collections import deque
from typing import Literal

from fastapi import APIRouter, File, Form, Header, HTTPException, Request, UploadFile
from fastapi.responses import StreamingResponse
from starlette.concurrency import run_in_threadpool

from Api.services.devils_advocate import (
    AcordaoSummaryResult,
    DevilsAdvocateAnalyzeResult,
    analyze_document,
    extract_uploads_text,
    fetch_acordao_from_url,
    summarize_acordao,
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
    # Local builds (desktop/Ollama) have no wallet to protect — the gate can be
    # disabled so the single, private user isn't asked for a code.
    if os.getenv("DEVILS_ADVOCATE_REQUIRE_ACCESS_CODE", "true").strip().lower() in ("0", "false", "no"):
        return
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
    files: list[UploadFile] = File(...),
    jurisdiction: str = Form(default="Portugal", description="Jurisdição (ex: Portugal)"),
    legal_area: str = Form(
        default="Fiscal",
        description="Área jurídica — 'Fiscal' (IVA/IRC/IRS) ou 'Laboral' (relações laborais, despedimento, acidentes de trabalho, assédio)",
    ),
    document_type: str = Form(
        default="Documento fiscal",
        description="Tipo de documento (ex: 'Documento fiscal', 'Nota de culpa', 'Decisão de despedimento', 'Relatório médico')",
    ),
    represented_side: str = Form(
        default="Contribuinte",
        description="Parte representada (ex: 'Contribuinte', 'Autoridade Tributária', 'Trabalhador', 'Empregador')",
    ),
    objective: str = Form(default="Encontrar argumentos, riscos e pontos a verificar"),
    language: Literal["pt", "en"] = Form(default="pt"),
    provider: str = Form(default="openai"),
    model: str = Form(default=""),
    mode: Literal["adversarial", "pre_filing"] = Form(default="adversarial"),
    x_access_code: str | None = Header(default=None),
):
    _check_access_code(x_access_code)
    _check_rate_limit(request.client.host if request.client else "unknown")
    try:
        extracted_text, content_truncated, per_file = await extract_uploads_text(files)
        upload_notes = [
            f"{p['name']}: {p['error']}" for p in per_file if not p.get("ok")
        ]
        return await run_in_threadpool(
            analyze_document,
            document_name="; ".join(p["name"] for p in per_file) or "documento",
            extracted_text=extracted_text,
            jurisdiction=jurisdiction.strip() or "Portugal",
            legal_area=legal_area.strip() or "Fiscal",
            document_type=document_type.strip() or "Documento fiscal",
            represented_side=represented_side.strip() or "Contribuinte",
            objective=objective.strip() or "Encontrar argumentos, riscos e pontos a verificar",
            language=language,
            content_truncated=content_truncated,
            upload_notes=upload_notes,
            provider=provider,
            model_choice=model.strip() or None,
            mode=mode,
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


@router.post("/summarize", response_model=AcordaoSummaryResult)
async def summarize_acordao_endpoint(
    request: Request,
    file: UploadFile | None = File(default=None),
    url: str = Form(default=""),
    language: Literal["pt", "en"] = Form(default="pt"),
    provider: str = Form(default="openai"),
    x_access_code: str | None = Header(default=None),
):
    _check_access_code(x_access_code)
    _check_rate_limit(request.client.host if request.client else "unknown")
    url = (url or "").strip()
    # Rulings can be much longer than fiscal documents and end with the conclusion
    # that matters most — give the acórdão path a higher character ceiling than
    # the default (unchanged for /analyze) so it doesn't cut before the decision.
    acordao_max_chars = int(os.getenv("DEVILS_ADVOCATE_ACORDAO_MAX_CHARS", "200000"))
    try:
        if url:
            source_text, content_truncated = await run_in_threadpool(
                fetch_acordao_from_url, url, acordao_max_chars
            )
            source_label = url
        elif file is not None and file.filename:
            source_text, content_truncated = await extract_upload_text(file, acordao_max_chars)
            source_label = file.filename
        else:
            raise ValueError("Forneça um PDF/DOCX ou um link do acórdão (dgsi.pt).")
        return await run_in_threadpool(
            summarize_acordao,
            source_text=source_text,
            source_label=source_label,
            language=language,
            provider=provider,
            content_truncated=content_truncated,
        )
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        log.error("devils-advocate summarize failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Resumo de acórdão falhou") from exc


@router.post("/analyze-stream")
async def analyze_devils_advocate_stream(
    request: Request,
    files: list[UploadFile] = File(...),
    jurisdiction: str = Form(default="Portugal"),
    legal_area: str = Form(
        default="Fiscal",
        description="Área jurídica — 'Fiscal' (IVA/IRC/IRS) ou 'Laboral'",
    ),
    document_type: str = Form(default="Documento fiscal"),
    represented_side: str = Form(default="Contribuinte"),
    objective: str = Form(default="Encontrar argumentos, riscos e pontos a verificar"),
    language: Literal["pt", "en"] = Form(default="pt"),
    provider: str = Form(default="openai"),
    model: str = Form(default=""),
    mode: Literal["adversarial", "pre_filing"] = Form(default="adversarial"),
    x_access_code: str | None = Header(default=None),
):
    _check_access_code(x_access_code)
    _check_rate_limit(request.client.host if request.client else "unknown")

    try:
        extracted_text, content_truncated, per_file = await extract_uploads_text(files)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    upload_notes = [f"{p['name']}: {p['error']}" for p in per_file if not p.get("ok")]

    _HEARTBEAT_MSGS = (
        "A analisar o documento...",
        "A montar a defesa e o ataque...",
        "A cruzar factos com a legislação...",
        "A procurar pontos fracos e riscos...",
        "A verificar o que não está documentado...",
        "A compor o relatório final...",
    )

    progress_queue: queue.Queue[dict] = queue.Queue()

    def _progress_callback(stage: str, message: str) -> None:
        progress_queue.put({"stage": stage, "message": message, "ts": time.time()})

    async def _event_stream():
        loop = asyncio.get_running_loop()

        task = loop.run_in_executor(
            None,
            lambda: analyze_document(
                document_name="; ".join(p["name"] for p in per_file) or "documento",
                extracted_text=extracted_text,
                jurisdiction=jurisdiction.strip() or "Portugal",
                legal_area=legal_area.strip() or "Fiscal",
                document_type=document_type.strip() or "Documento fiscal",
                represented_side=represented_side.strip() or "Contribuinte",
                objective=objective.strip() or "Encontrar argumentos, riscos e pontos a verificar",
                language=language,
                content_truncated=content_truncated,
                upload_notes=upload_notes,
                provider=provider,
                model_choice=model.strip() or None,
                progress_callback=_progress_callback,
                mode=mode,
            ),
        )

        # ── SSE event loop ──────────────────────────────────────────
        # Drain the queue every ~200 ms while the analysis runs.  When
        # the analysis finishes, drain one last time, then send the
        # result (or error) and close the stream.
        yield _sse_event("extracting",
                         f"Texto extraído de '{file.filename}' "
                         f"({len(extracted_text):,} caracteres). A iniciar análise...")

        stream_start = time.time()
        last_drain = time.time()
        while True:
            try:
                evt = progress_queue.get(timeout=0.2)
                yield _sse_event(evt["stage"], evt["message"])
                last_drain = time.time()
            except queue.Empty:
                if task.done():
                    # Drain any late events, then break
                    while True:
                        try:
                            evt = progress_queue.get_nowait()
                            yield _sse_event(evt["stage"], evt["message"])
                        except queue.Empty:
                            break
                    break
                # Heartbeat every 5 s so proxies don't close the connection —
                # vary the message so the user sees real progress, not a loop.
                if time.time() - last_drain > 5:
                    elapsed = int(time.time() - stream_start)
                    msg = _HEARTBEAT_MSGS[(elapsed // 15) % len(_HEARTBEAT_MSGS)]
                    yield _sse_event("heartbeat", f"{msg} (há {elapsed} s)")
                    last_drain = time.time()

        # ── Final result ────────────────────────────────────────────
        try:
            result = task.result()
        except Exception as exc:
            log.error("devils-advocate analyze-stream failed: %s", exc, exc_info=True)
            detail = str(exc)
            if not detail:
                detail = "Devil's Advocate analysis failed"
            yield _sse_event("error", detail)
            return

        yield _sse_event("result", json.dumps(result.model_dump(), ensure_ascii=False))

    return StreamingResponse(
        _event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # disable nginx buffering
        },
    )


def _sse_event(event: str, data: str) -> str:
    """Format a single SSE message.  Multi-line data is sent as multiple
    `data:` lines — the empty trailing line terminates the message."""
    return f"event: {event}\n" + "".join(f"data: {line}\n" for line in data.split("\n")) + "\n"


# ── Job + polling (robust against proxies that kill long-lived streams) ──
# Cloud proxies (Railway free tier included) cut connections that stay open
# too long, so SSE dies mid-analysis. A job endpoint answers immediately with
# an id; the frontend polls a tiny GET until the analysis is done. Each
# response is short, so no proxy limit is ever hit.
_JOBS: dict[str, dict] = {}
_JOB_TTL_SECONDS = 3600


@router.post("/analyze-job")
async def analyze_devils_advocate_job(
    request: Request,
    files: list[UploadFile] = File(...),
    jurisdiction: str = Form(default="Portugal"),
    legal_area: str = Form(default="Fiscal"),
    document_type: str = Form(default="Documento fiscal"),
    represented_side: str = Form(default="Contribuinte"),
    objective: str = Form(default="Encontrar argumentos, riscos e pontos a verificar"),
    language: Literal["pt", "en"] = Form(default="pt"),
    provider: str = Form(default="openai"),
    model: str = Form(default=""),
    mode: Literal["adversarial", "pre_filing"] = Form(default="adversarial"),
    x_access_code: str | None = Header(default=None),
):
    _check_access_code(x_access_code)
    _check_rate_limit(request.client.host if request.client else "unknown")

    try:
        extracted_text, content_truncated, per_file = await extract_uploads_text(files)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    upload_notes = [f"{p['name']}: {p['error']}" for p in per_file if not p.get("ok")]

    # Drop stale jobs so the dict doesn't grow forever.
    now = time.time()
    for job_id in [k for k, v in _JOBS.items() if now - v["created"] > _JOB_TTL_SECONDS]:
        _JOBS.pop(job_id, None)

    job_id = uuid.uuid4().hex
    progress: list[dict] = []

    def _progress_callback(stage: str, message: str) -> None:
        progress.append({"stage": stage, "message": message, "ts": time.time()})

    loop = asyncio.get_running_loop()
    task = loop.run_in_executor(
        None,
        lambda: analyze_document(
            document_name="; ".join(p["name"] for p in per_file) or "documento",
            extracted_text=extracted_text,
            jurisdiction=jurisdiction.strip() or "Portugal",
            legal_area=legal_area.strip() or "Fiscal",
            document_type=document_type.strip() or "Documento fiscal",
            represented_side=represented_side.strip() or "Contribuinte",
            objective=objective.strip() or "Encontrar argumentos, riscos e pontos a verificar",
            language=language,
            content_truncated=content_truncated,
            upload_notes=upload_notes,
            provider=provider,
            model_choice=model.strip() or None,
            progress_callback=_progress_callback,
            mode=mode,
        ),
    )
    _JOBS[job_id] = {"task": task, "progress": progress, "created": now}
    return {"job_id": job_id}


@router.get("/job/{job_id}")
async def get_devils_advocate_job(job_id: str):
    job = _JOBS.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Trabalho não encontrado ou já expirou.")
    elapsed = int(time.time() - job["created"])
    task = job["task"]
    if not task.done():
        return {"status": "running", "progress": job["progress"], "elapsed": elapsed}
    try:
        result = task.result()
    except Exception as exc:
        log.error("devils-advocate job %s failed: %s", job_id, exc, exc_info=True)
        return {
            "status": "error",
            "detail": str(exc) or "A análise falhou. Tente novamente.",
            "progress": job["progress"],
            "elapsed": elapsed,
        }
    return {
        "status": "done",
        "result": result.model_dump(),
        "progress": job["progress"],
        "elapsed": elapsed,
    }
