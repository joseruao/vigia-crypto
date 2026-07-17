from __future__ import annotations

import argparse
from pathlib import Path

from .workspace import ensure_workspace


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m auditor",
        description="Run local AI Business Auditor workflows on this PC.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    init_cmd = sub.add_parser("init", help="Create a local audit workspace.")
    init_cmd.add_argument("path", help="Workspace folder, e.g. audits/empresa_x")

    run_cmd = sub.add_parser("run", help="Run an audit workspace.")
    run_cmd.add_argument("path", help="Workspace folder created with init.")

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    workspace = Path(args.path).resolve()

    if args.command == "init":
        ensure_workspace(workspace)
        print(f"Audit workspace ready: {workspace}")
        return

    if args.command == "run":
        ensure_workspace(workspace)
        print("Audit runner scaffold is ready.")
        print(f"Workspace: {workspace}")
        print("Next step: implement extract -> normalize -> audit -> report pipeline.")
        return

    parser.error("Unknown command")

