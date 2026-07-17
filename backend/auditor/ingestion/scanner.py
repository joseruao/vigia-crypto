from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


SUPPORTED_SUFFIXES = {".pdf", ".docx", ".xlsx", ".csv", ".txt", ".png", ".jpg", ".jpeg"}


@dataclass(frozen=True)
class DocumentCandidate:
    path: Path
    category: str
    suffix: str


def scan_input(workspace: Path) -> list[DocumentCandidate]:
    input_dir = workspace / "input"
    documents: list[DocumentCandidate] = []
    if not input_dir.exists():
        return documents
    for path in input_dir.rglob("*"):
        if not path.is_file():
            continue
        suffix = path.suffix.lower()
        if suffix not in SUPPORTED_SUFFIXES:
            continue
        try:
            category = path.relative_to(input_dir).parts[0]
        except IndexError:
            category = "outros"
        documents.append(DocumentCandidate(path=path, category=category, suffix=suffix))
    return documents

