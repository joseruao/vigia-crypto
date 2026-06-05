"""
Private Arkham wallet intelligence cron runner.

This is intentionally backend-only: it writes to Supabase candidate_wallets but
does not expose candidate wallet addresses on the public website.

Recommended Railway command:
    python backend/worker/arkham_wallet_intel_runner.py
"""
from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CLUSTER_SCRIPT = ROOT / "backend" / "worker" / "arkham_wallet_cluster.py"
ACTIVITY_SCRIPT = ROOT / "backend" / "worker" / "arkham_candidate_wallet_activity.py"


def _split_csv(value: str) -> list[str]:
    return [item.strip() for item in value.replace(";", ",").split(",") if item.strip()]


def _run_step(name: str, script: Path, env_updates: dict[str, str]) -> int:
    env = os.environ.copy()
    env.update(env_updates)
    print(f"\n{'=' * 72}\n{name}\n{'=' * 72}", flush=True)
    print(
        "Settings: "
        f"entities={env.get('ARKHAM_CLUSTER_ENTITIES', '-')}, "
        f"flow={env.get('ARKHAM_CLUSTER_FLOW', '-')}, "
        f"depth={env.get('ARKHAM_CLUSTER_DEPTH', '-')}, "
        f"limit={env.get('ARKHAM_CLUSTER_TRANSFER_LIMIT', '-')}, "
        f"max_hop={env.get('ARKHAM_CLUSTER_MAX_SECOND_HOP', '-')}, "
        f"activity_min={env.get('ARKHAM_ACTIVITY_MIN_VALUE_USD', '-')}",
        flush=True,
    )
    completed = subprocess.run([sys.executable, str(script)], cwd=str(ROOT), env=env, check=False)
    print(f"{name} finished with exit code {completed.returncode}", flush=True)
    return int(completed.returncode or 0)


def main() -> int:
    """
    Runs:
      1. Broad scan across default Arkham entities.
      2. Optional deep scans for selected entities.
      3. Activity refresh for saved candidate wallets.
    """
    broad_entities = os.getenv("ARKHAM_INTEL_BROAD_ENTITIES", "all")
    deep_entities = _split_csv(os.getenv("ARKHAM_INTEL_DEEP_ENTITIES", "galaxy-digital,multicoin-capital,a16z"))
    run_deep = os.getenv("ARKHAM_INTEL_RUN_DEEP", "1").strip().lower() in {"1", "true", "yes"}

    exit_code = 0

    exit_code |= _run_step(
        "ARKHAM BROAD CLUSTER SCAN",
        CLUSTER_SCRIPT,
        {
            "ARKHAM_CLUSTER_SAVE": "1",
            "ARKHAM_CLUSTER_ENTITIES": broad_entities,
            "ARKHAM_CLUSTER_FLOW": os.getenv("ARKHAM_INTEL_BROAD_FLOW", "out"),
            "ARKHAM_CLUSTER_TRANSFER_LIMIT": os.getenv("ARKHAM_INTEL_BROAD_TRANSFER_LIMIT", "10"),
            "ARKHAM_CLUSTER_DEPTH": os.getenv("ARKHAM_INTEL_BROAD_DEPTH", "2"),
            "ARKHAM_CLUSTER_MAX_SECOND_HOP": os.getenv("ARKHAM_INTEL_BROAD_MAX_SECOND_HOP", "3"),
        },
    )

    if run_deep:
        for entity in deep_entities:
            time.sleep(1.2)
            exit_code |= _run_step(
                f"ARKHAM DEEP CLUSTER SCAN - {entity}",
                CLUSTER_SCRIPT,
                {
                    "ARKHAM_CLUSTER_SAVE": "1",
                    "ARKHAM_CLUSTER_ENTITIES": entity,
                    "ARKHAM_CLUSTER_FLOW": os.getenv("ARKHAM_INTEL_DEEP_FLOW", "both"),
                    "ARKHAM_CLUSTER_TRANSFER_LIMIT": os.getenv("ARKHAM_INTEL_DEEP_TRANSFER_LIMIT", "20"),
                    "ARKHAM_CLUSTER_DEPTH": os.getenv("ARKHAM_INTEL_DEEP_DEPTH", "3"),
                    "ARKHAM_CLUSTER_MAX_SECOND_HOP": os.getenv("ARKHAM_INTEL_DEEP_MAX_SECOND_HOP", "5"),
                },
            )

    time.sleep(1.2)
    exit_code |= _run_step(
        "ARKHAM CANDIDATE WALLET ACTIVITY REFRESH",
        ACTIVITY_SCRIPT,
        {
            "ARKHAM_ACTIVITY_LIMIT": os.getenv("ARKHAM_INTEL_ACTIVITY_LIMIT", "50"),
            "ARKHAM_ACTIVITY_MIN_VALUE_USD": os.getenv("ARKHAM_INTEL_ACTIVITY_MIN_VALUE_USD", "50000"),
            "ARKHAM_ACTIVITY_TRANSFER_LIMIT": os.getenv("ARKHAM_INTEL_ACTIVITY_TRANSFER_LIMIT", "25"),
        },
    )

    print(f"\nARKHAM WALLET INTEL RUNNER finished with exit code {exit_code}", flush=True)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
