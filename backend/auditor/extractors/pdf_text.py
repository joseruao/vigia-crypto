from __future__ import annotations

from pathlib import Path

from pypdf import PdfReader


def extract_pdf_text(path: Path, max_chars: int) -> tuple[str, bool]:
    """Extrai texto de um PDF textual. Devolve (texto, truncado).

    PDFs escaneados (sem camada de texto) devolvem texto vazio — o OCR
    (Azure Document Intelligence) fica como passo futuro.
    """
    reader = PdfReader(str(path))
    parts: list[str] = []
    total = 0
    for page in reader.pages:
        page_text = page.extract_text() or ""
        if not page_text.strip():
            continue
        parts.append(page_text)
        total += len(page_text)
        if total >= max_chars:
            break
    text = "\n\n".join(parts)
    truncated = len(text) > max_chars
    return text[:max_chars], truncated
