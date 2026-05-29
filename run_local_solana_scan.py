"""Run the Solana listing scan locally.

Usage:
    python run_local_solana_scan.py

This loads .env files before importing the Render worker, then runs the same
Supabase-updating scan used by the cron job.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
BACKEND = ROOT / "backend"
WORKER = BACKEND / "worker"


def load_env() -> None:
    try:
        from dotenv import load_dotenv
    except ImportError as exc:
        raise RuntimeError("python-dotenv is required. Run: pip install -r backend/requirements.txt") from exc

    for env_path in (ROOT / ".env", BACKEND / ".env"):
        if env_path.exists():
            load_dotenv(env_path, override=False)
            print(f"Loaded env: {env_path}")


def require_env() -> None:
    missing = [
        name for name in ("SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY")
        if not os.getenv(name)
    ]
    if not (os.getenv("HELIUS_API_KEY") or os.getenv("HELIUS_KEYS")):
        missing.append("HELIUS_API_KEY or HELIUS_KEYS")

    if missing:
        raise RuntimeError("Missing required env vars: " + ", ".join(missing))


def main() -> int:
    load_env()
    require_env()

    sys.path.insert(0, str(WORKER))
    sys.path.insert(0, str(BACKEND))

    from vigia_solana_pro_supabase import main as worker_main

    total = worker_main()
    print(f"Local Solana scan finished. Alerts saved: {total}")
    return int(total or 0)


if __name__ == "__main__":
    main()
