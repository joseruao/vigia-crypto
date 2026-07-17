from __future__ import annotations

from pathlib import Path


WORKSPACE_DIRS = (
    "input/faturas",
    "input/contratos",
    "input/extratos",
    "input/catalogos",
    "input/outros",
    "extracted",
    "db",
    "reports",
)


def ensure_workspace(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    for folder in WORKSPACE_DIRS:
        (path / folder).mkdir(parents=True, exist_ok=True)
    readme = path / "README.md"
    if not readme.exists():
        readme.write_text(
            "# Local Audit Workspace\n\n"
            "Coloque documentos nas pastas dentro de `input/` e corra:\n\n"
            "```powershell\n"
            "python -m auditor run .\n"
            "```\n",
            encoding="utf-8",
        )

