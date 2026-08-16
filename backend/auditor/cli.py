from __future__ import annotations

import argparse
import subprocess
import sys
import webbrowser
from pathlib import Path

from .pipeline import run_audit
from .workspace import ensure_workspace

# Caminho do Azure CLI (instalado a 2026-08-16; o terminal novo já tem no PATH)
_AZ = r"C:\Program Files\Microsoft SDKs\Azure\CLI2\wbin\az.cmd"
_STORAGE_ACCOUNT = "vigiaauditbackups"
_CONTAINER = "audit-backups"


def _az(args: list[str]) -> subprocess.CompletedProcess[str]:
    """Corre o az.cmd de forma fiável no Windows (.cmd precisa do cmd.exe)."""
    cmd = ["cmd", "/c", _AZ, *args]
    return subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m auditor",
        description="Run local AI Business Auditor workflows on this PC.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    init_cmd = sub.add_parser("init", help="Create a local audit workspace.")
    init_cmd.add_argument("path", help="Workspace folder, e.g. audits/empresa_x")

    run_cmd = sub.add_parser("run", help="Run the full audit pipeline (extract -> rules -> report).")
    run_cmd.add_argument("path", help="Workspace folder created with init.")
    run_cmd.add_argument("--limit", type=int, default=None, help="Só processa os primeiros N PDFs.")
    run_cmd.add_argument("--skip-ai", action="store_true", help="Só regras locais, sem chamadas à IA.")
    run_cmd.add_argument("--open", action="store_true", help="Abre o relatório no browser no fim.")

    report_cmd = sub.add_parser("report", help="Regenera o relatório HTML a partir da base local.")
    report_cmd.add_argument("path", help="Workspace folder.")
    report_cmd.add_argument("--open", action="store_true", help="Abre o relatório no browser no fim.")

    upload_cmd = sub.add_parser("upload", help="Envia input/ para o blob do Azure (modo lote/500).")
    upload_cmd.add_argument("path", help="Workspace folder.")
    upload_cmd.add_argument("--container-path", default=None, help="Pasta no container (default: nome do workspace).")

    pull_cmd = sub.add_parser("pull", help="Descarrega ficheiros do blob para input/.")
    pull_cmd.add_argument("path", help="Workspace folder.")
    pull_cmd.add_argument("--container-path", default=None, help="Pasta no container (default: nome do workspace).")

    return parser


def _cmd_upload(workspace: Path, container_path: str | None) -> int:
    source = workspace / "input"
    if not source.exists():
        print(f"Sem pasta input em {workspace}")
        return 1
    dest = f"{_CONTAINER}/{container_path or workspace.name}"
    print(f"⬆️  A enviar {source} → {_STORAGE_ACCOUNT}/{dest}")
    result = _az(
        [
            "storage", "blob", "upload-batch",
            "--account-name", _STORAGE_ACCOUNT,
            "--auth-mode", "login",
            "--source", str(source),
            "--destination", dest,
            "--overwrite",
        ]
    )
    print(result.stdout[-2000:] or result.stderr[-2000:])
    if result.returncode != 0:
        print("❌ Upload falhou. Confirma que fizeste `az login`.")
        return 1
    print("✅ Upload completo.")
    return 0


def _cmd_pull(workspace: Path, container_path: str | None) -> int:
    target = workspace / "input"
    target.mkdir(parents=True, exist_ok=True)
    prefix = f"{container_path or workspace.name}/"
    print(f"⬇️  A descarregar {_STORAGE_ACCOUNT}/{_CONTAINER}/{prefix} → {target}")

    listed = _az(
        [
            "storage", "blob", "list",
            "--account-name", _STORAGE_ACCOUNT,
            "--auth-mode", "login",
            "--container-name", _CONTAINER,
            "--prefix", prefix,
            "--query", "[].name",
            "--output", "tsv",
        ]
    )
    if listed.returncode != 0 or not listed.stdout.strip():
        print(listed.stderr[-1200:])
        print("❌ Nada para descarregar ou sem permissões (fizeste `az login`?).")
        return 1
    blobs = [line.strip() for line in listed.stdout.splitlines() if line.strip()]
    for blob in blobs:
        rel = blob[len(prefix):]
        dest_file = target / rel
        dest_file.parent.mkdir(parents=True, exist_ok=True)
        result = _az(
            [
                "storage", "blob", "download",
                "--account-name", _STORAGE_ACCOUNT,
                "--auth-mode", "login",
                "--container-name", _CONTAINER,
                "--name", blob,
                "--file", str(dest_file),
            ]
        )
        if result.returncode == 0:
            print(f"   ✓ {rel}")
        else:
            print(f"   ✗ {rel}: {result.stderr[-200:]}")
    print(f"✅ {len(blobs)} ficheiro(s) descarregados. Corre agora `python -m auditor run <path>`.")
    return 0


def main() -> None:
    # Windows cp1252 não sabe imprimir emojis — força UTF-8 na consola
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    parser = build_parser()
    args = parser.parse_args()
    workspace = Path(args.path).resolve()

    if args.command == "init":
        ensure_workspace(workspace)
        print(f"Audit workspace ready: {workspace}")
        print("Coloca os documentos em input/ (faturas, extratos, contratos...) e corre:")
        print(f"  python -m auditor run {args.path}")
        return

    if args.command == "run":
        ensure_workspace(workspace)
        report = run_audit(workspace, limit=args.limit, skip_ai=args.skip_ai)
        if args.open:
            webbrowser.open(report.as_uri())
        return

    if args.command == "report":
        from .reports.html_report import write_report
        from .storage.db import AuditDB

        db = AuditDB(workspace / "db" / "audit.db")
        try:
            report = write_report(db, workspace)
        finally:
            db.close()
        print(f"📊 Relatório: {report}")
        if args.open:
            webbrowser.open(report.as_uri())
        return

    if args.command == "upload":
        sys.exit(_cmd_upload(workspace, args.container_path))

    if args.command == "pull":
        sys.exit(_cmd_pull(workspace, args.container_path))

    parser.error("Unknown command")
