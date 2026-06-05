"""
Refresh last activity for Arkham candidate wallets.

Standalone local run:
    python backend/worker/arkham_candidate_wallet_activity.py

Reads Supabase candidate_wallets, checks latest relevant Arkham in/out transfer
for each address, prints the result, and stores it in dedicated activity
columns plus raw.last_activity.
"""
from __future__ import annotations

import base64
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv


for _env in (
    Path(__file__).resolve().parents[1] / ".env",
    Path(__file__).resolve().parents[2] / ".env",
):
    if _env.exists():
        load_dotenv(_env, override=False)
        break


ARKHAM_BASE_URL = "https://api.arkm.com"
ARKHAM_API_KEY = os.getenv("ARKHAM_API_KEY", "").strip()
SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE", "").strip() or os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()
CANDIDATE_WALLETS_TABLE = os.getenv("CANDIDATE_WALLETS_TABLE", "candidate_wallets")
LIMIT = int(os.getenv("ARKHAM_ACTIVITY_LIMIT", "50"))
MIN_ACTIVITY_VALUE_USD = float(os.getenv("ARKHAM_ACTIVITY_MIN_VALUE_USD", "50000"))
TRANSFER_LOOKBACK_LIMIT = int(os.getenv("ARKHAM_ACTIVITY_TRANSFER_LIMIT", "25"))
REQUEST_TIMEOUT = int(os.getenv("ARKHAM_ACTIVITY_TIMEOUT", "45"))


def _jwt_role(token: str) -> str:
    try:
        payload = token.split(".")[1]
        payload += "=" * (-len(payload) % 4)
        data = json.loads(base64.urlsafe_b64decode(payload.encode("utf-8")).decode("utf-8"))
        return str(data.get("role") or "").strip()
    except Exception:
        return ""


def _require_env() -> None:
    if not ARKHAM_API_KEY:
        raise RuntimeError("Missing ARKHAM_API_KEY")
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise RuntimeError("Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE")
    if _jwt_role(SUPABASE_KEY) != "service_role":
        raise RuntimeError(f"Need Supabase service_role key; detected jwt_role={_jwt_role(SUPABASE_KEY) or 'unknown'}")


def _arkham_headers() -> dict[str, str]:
    return {
        "API-Key": ARKHAM_API_KEY,
        "Accept": "application/json",
        "User-Agent": "vigia-crypto-arkham-wallet-activity/0.1",
    }


def _supabase_headers(prefer: str = "return=representation") -> dict[str, str]:
    return {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": prefer,
    }


def _float(value: Any) -> float:
    try:
        if value is None:
            return 0.0
        if isinstance(value, str):
            value = value.replace(",", "").replace("$", "").strip()
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _entity_name(value: Any) -> str:
    if not isinstance(value, dict):
        return ""
    entity = value.get("arkhamEntity") if isinstance(value.get("arkhamEntity"), dict) else {}
    predicted = value.get("predictedEntity") if isinstance(value.get("predictedEntity"), dict) else {}
    label = value.get("arkhamLabel") if isinstance(value.get("arkhamLabel"), dict) else {}
    return str(entity.get("name") or predicted.get("name") or label.get("name") or "").strip()


def _address(value: Any) -> str:
    if isinstance(value, dict):
        return str(value.get("address") or "").strip()
    return str(value or "").strip()


def _parse_ts(value: Any) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None


def _extract_rows(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)]
    if isinstance(payload, dict):
        for key in ("transfers", "items", "data", "results"):
            if isinstance(payload.get(key), list):
                return [row for row in payload[key] if isinstance(row, dict)]
    return []


def fetch_candidate_wallets() -> list[dict[str, Any]]:
    params = {
        "select": "id,entity,address,chain,score,balance_usd,classification,raw",
        "order": "score.desc,balance_usd.desc",
        "limit": str(LIMIT),
    }
    response = requests.get(
        f"{SUPABASE_URL}/rest/v1/{CANDIDATE_WALLETS_TABLE}",
        headers=_supabase_headers(),
        params=params,
        timeout=30,
    )
    if response.status_code >= 400:
        raise RuntimeError(f"Supabase fetch failed: HTTP {response.status_code} {response.text[:300]}")
    return response.json()


def fetch_latest_transfer(address: str, flow: str) -> dict[str, Any] | None:
    response = requests.get(
        f"{ARKHAM_BASE_URL}/transfers",
        headers=_arkham_headers(),
        params={"base": address, "flow": flow, "limit": TRANSFER_LOOKBACK_LIMIT},
        timeout=REQUEST_TIMEOUT,
    )
    if response.status_code >= 400:
        print(f"  Arkham {flow} failed for {address[:10]}... HTTP {response.status_code}: {response.text[:160]}", flush=True)
        return None
    rows = _extract_rows(response.json() if response.content else {})
    if not rows:
        return None
    relevant_rows = []
    for row in rows:
        value_usd = _float(row.get("historicalUSD") or row.get("usdValue") or row.get("valueUsd") or 0)
        if value_usd >= MIN_ACTIVITY_VALUE_USD:
            relevant_rows.append(row)
    if not relevant_rows:
        return None

    row = relevant_rows[0]
    ts = _parse_ts(row.get("blockTimestamp"))
    from_obj = row.get("fromAddress")
    to_obj = row.get("toAddress")
    return {
        "flow": flow,
        "timestamp": ts.isoformat() if ts else str(row.get("blockTimestamp") or ""),
        "timestamp_dt": ts,
        "token": str(row.get("tokenSymbol") or row.get("tokenName") or "").strip(),
        "value_usd": _float(row.get("historicalUSD") or row.get("usdValue") or row.get("valueUsd") or 0),
        "tx": row.get("transactionHash"),
        "chain": row.get("chain"),
        "from": _address(from_obj),
        "to": _address(to_obj),
        "from_label": _entity_name(from_obj),
        "to_label": _entity_name(to_obj),
    }


def latest_activity(address: str) -> dict[str, Any] | None:
    candidates = []
    for flow in ("out", "in"):
        item = fetch_latest_transfer(address, flow)
        if item:
            candidates.append(item)
        time.sleep(1.05)
    if not candidates:
        return None
    candidates.sort(key=lambda row: row.get("timestamp_dt") or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
    latest = candidates[0].copy()
    latest.pop("timestamp_dt", None)
    return latest


def save_activity(row: dict[str, Any], activity: dict[str, Any]) -> bool:
    raw = row.get("raw") if isinstance(row.get("raw"), dict) else {}
    raw = {**raw, "last_activity": activity, "last_activity_checked_at": datetime.now(timezone.utc).isoformat()}
    counterparty = activity.get("to") if activity.get("flow") == "out" else activity.get("from")
    counterparty_label = activity.get("to_label") if activity.get("flow") == "out" else activity.get("from_label")
    payload = {
        "last_activity_ts": activity.get("timestamp") or None,
        "last_activity_value_usd": activity.get("value_usd") or 0,
        "last_activity_flow": activity.get("flow") or None,
        "last_activity_token": activity.get("token") or None,
        "last_activity_chain": activity.get("chain") or None,
        "last_activity_counterparty": counterparty or None,
        "last_activity_counterparty_label": counterparty_label or None,
        "last_activity_tx": activity.get("tx") or None,
        "activity_checked_at": datetime.now(timezone.utc).isoformat(),
        "raw": raw,
    }
    response = requests.patch(
        f"{SUPABASE_URL}/rest/v1/{CANDIDATE_WALLETS_TABLE}",
        headers=_supabase_headers("return=minimal"),
        params={"id": f"eq.{row['id']}"},
        data=json.dumps(payload),
        timeout=30,
    )
    if response.status_code not in (200, 204):
        print(f"  Supabase update failed for {row.get('address', '')[:10]}... HTTP {response.status_code}: {response.text[:200]}", flush=True)
        return False
    return True


def main() -> None:
    _require_env()
    rows = fetch_candidate_wallets()
    print(
        f"ARKHAM CANDIDATE WALLET ACTIVITY - {len(rows)} wallet(s), "
        f"min=${MIN_ACTIVITY_VALUE_USD:,.0f}, transfer_limit={TRANSFER_LOOKBACK_LIMIT}",
        flush=True,
    )
    saved = 0
    for index, row in enumerate(rows, 1):
        address = str(row.get("address") or "").strip()
        if not address:
            continue
        activity = latest_activity(address)
        if not activity:
            print(
                f"[{index}/{len(rows)}] {address[:12]}... no transfer >= ${MIN_ACTIVITY_VALUE_USD:,.0f} "
                f"in latest {TRANSFER_LOOKBACK_LIMIT} in/out rows",
                flush=True,
            )
            continue
        label = activity.get("to_label") if activity.get("flow") == "out" else activity.get("from_label")
        print(
            f"[{index}/{len(rows)}] {row.get('entity')} {address[:12]}... "
            f"{activity['flow']} {activity.get('token') or 'token'} ${activity.get('value_usd', 0):,.0f} "
            f"at {activity.get('timestamp')} {('via ' + label) if label else ''}",
            flush=True,
        )
        if save_activity(row, activity):
            saved += 1
    print(f"Saved activity: {saved}/{len(rows)}", flush=True)


if __name__ == "__main__":
    main()
