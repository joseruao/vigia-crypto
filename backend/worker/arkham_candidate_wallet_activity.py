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
ARKHAM_SIGNALS_TABLE = os.getenv("ARKHAM_SIGNALS_TABLE", "arkham_signals")
LIMIT = int(os.getenv("ARKHAM_ACTIVITY_LIMIT", "100"))
MIN_ACTIVITY_VALUE_USD = float(os.getenv("ARKHAM_ACTIVITY_MIN_VALUE_USD", "50000"))
INSIDER_MIN_VALUE_USD = float(os.getenv("ARKHAM_INSIDER_MIN_VALUE_USD", "25000"))
TRANSFER_LOOKBACK_LIMIT = int(os.getenv("ARKHAM_ACTIVITY_TRANSFER_LIMIT", "25"))
REQUEST_TIMEOUT = int(os.getenv("ARKHAM_ACTIVITY_TIMEOUT", "45"))

TELEGRAM_BOT_TOKEN = (
    os.getenv("TELEGRAM_BOT_TOKEN_SOL")
    or os.getenv("TELEGRAM_BOT_TOKEN_1")
    or os.getenv("TELEGRAM_BOT_TOKEN")
    or ""
)
TELEGRAM_CHAT_ID = (
    os.getenv("TELEGRAM_CHAT_ID_SOL")
    or os.getenv("TELEGRAM_CHAT_ID_1")
    or os.getenv("TELEGRAM_CHAT_ID")
    or ""
)


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


def _fmt_usd(v: float) -> str:
    if v >= 1_000_000:
        return f"${v/1_000_000:.1f}M"
    if v >= 1_000:
        return f"${v/1_000:.0f}K"
    return f"${v:.0f}"


def _is_insider(row: dict[str, Any]) -> bool:
    return str(row.get("source") or "").startswith("prelisting")


def send_insider_telegram(row: dict[str, Any], activity: dict[str, Any]) -> None:
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return
    flow = activity.get("flow", "?")
    token = activity.get("token") or "token"
    value = _fmt_usd(float(activity.get("value_usd") or 0))
    counterparty = activity.get("to_label") if flow == "out" else activity.get("from_label")
    entity = str(row.get("entity") or "").replace("insider:", "")
    chain = activity.get("chain") or row.get("chain") or ""
    emoji = "📤" if flow == "out" else "📥"
    direction_text = "Saída" if flow == "out" else "Entrada"
    lines = [
        f"*🕵️ Insider Alert — {entity}*",
        f"{emoji} *{direction_text}* {token} · {value}",
    ]
    if counterparty:
        lines.append(f"↔️ {counterparty}")
    if chain:
        lines.append(f"⛓ {chain.upper()}")
    ts = (activity.get("timestamp") or "")[:10]
    if ts:
        lines.append(f"📅 {ts}")
    tx = activity.get("tx")
    if tx:
        addr = str(row.get("address") or "")
        if chain in ("ethereum", "bsc", "base"):
            explorer = f"https://etherscan.io/tx/{tx}" if chain == "ethereum" else f"https://bscscan.com/tx/{tx}"
            lines.append(f"[Ver tx]({explorer})")
        elif chain == "solana":
            lines.append(f"[Ver tx](https://solscan.io/tx/{tx})")
    try:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
            json={"chat_id": TELEGRAM_CHAT_ID, "text": "\n".join(lines), "parse_mode": "Markdown", "disable_web_page_preview": True},
            timeout=10,
        )
        print(f"  Telegram insider alert enviado: {entity}", flush=True)
    except Exception as exc:
        print(f"  Telegram falhou: {exc}", flush=True)


def save_insider_signal(row: dict[str, Any], activity: dict[str, Any]) -> None:
    """Write insider activity to arkham_signals so it appears in the Whales tab."""
    flow = activity.get("flow", "?")
    value_usd = float(activity.get("value_usd") or 0)
    entity = str(row.get("entity") or "")
    token = activity.get("token") or ""
    chain = activity.get("chain") or row.get("chain") or ""
    counterparty = activity.get("to_label") if flow == "out" else activity.get("from_label")
    signal_key = f"insider:{row.get('address','')[:12]}:{token}:{(activity.get('timestamp') or '')[:10]}"
    payload = {
        "signal_key": signal_key,
        "entity": entity,
        "entity_type": "insider",
        "token": token,
        "chain": chain,
        "value_usd": value_usd,
        "signal_direction": flow,
        "exchange": counterparty or "",
        "score": int(row.get("score") or 60),
        "ts": activity.get("timestamp"),
        "analysis_text": f"Insider wallet {str(row.get('address',''))[:12]}... · {_fmt_usd(value_usd)} {token} {flow}",
    }
    try:
        response = requests.post(
            f"{SUPABASE_URL}/rest/v1/{ARKHAM_SIGNALS_TABLE}",
            headers={**_supabase_headers(), "Prefer": "resolution=ignore-duplicates,return=minimal"},
            data=json.dumps(payload),
            timeout=15,
        )
        if response.status_code not in (200, 201, 204):
            print(f"  arkham_signals insert failed HTTP {response.status_code}: {response.text[:200]}", flush=True)
    except Exception as exc:
        print(f"  arkham_signals insert failed: {exc}", flush=True)


def fetch_candidate_wallets() -> list[dict[str, Any]]:
    params = {
        "select": "id,entity,address,chain,score,balance_usd,classification,source,last_activity_ts,raw",
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


def latest_activity(address: str, min_value_usd: float | None = None) -> dict[str, Any] | None:
    _orig = MIN_ACTIVITY_VALUE_USD
    if min_value_usd is not None:
        import builtins
        # Temporarily patch module-level constant via closure
        pass
    candidates = []
    for flow in ("out", "in"):
        response = requests.get(
            f"{ARKHAM_BASE_URL}/transfers",
            headers=_arkham_headers(),
            params={"base": address, "flow": flow, "limit": TRANSFER_LOOKBACK_LIMIT},
            timeout=REQUEST_TIMEOUT,
        )
        if response.status_code >= 400:
            time.sleep(1.05)
            continue
        rows = _extract_rows(response.json() if response.content else {})
        threshold = min_value_usd if min_value_usd is not None else MIN_ACTIVITY_VALUE_USD
        for row in rows:
            value_usd = _float(row.get("historicalUSD") or row.get("usdValue") or row.get("valueUsd") or 0)
            if value_usd >= threshold:
                ts = _parse_ts(row.get("blockTimestamp"))
                from_obj = row.get("fromAddress")
                to_obj = row.get("toAddress")
                candidates.append({
                    "flow": flow,
                    "timestamp": ts.isoformat() if ts else str(row.get("blockTimestamp") or ""),
                    "timestamp_dt": ts,
                    "token": str(row.get("tokenSymbol") or row.get("tokenName") or "").strip(),
                    "value_usd": value_usd,
                    "tx": row.get("transactionHash"),
                    "chain": row.get("chain"),
                    "from": _address(from_obj),
                    "to": _address(to_obj),
                    "from_label": _entity_name(from_obj),
                    "to_label": _entity_name(to_obj),
                })
                break  # take only the most recent per flow direction
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


def _is_new_activity(row: dict[str, Any], activity: dict[str, Any]) -> bool:
    """Returns True if activity is newer than the last recorded activity_ts."""
    prev_ts = _parse_ts(row.get("last_activity_ts"))
    new_ts = _parse_ts(activity.get("timestamp"))
    if not new_ts:
        return False
    if not prev_ts:
        return True
    return new_ts > prev_ts


def main() -> None:
    _require_env()
    rows = fetch_candidate_wallets()
    insider_rows = [r for r in rows if _is_insider(r)]
    regular_rows = [r for r in rows if not _is_insider(r)]
    print(
        f"ARKHAM CANDIDATE WALLET ACTIVITY - {len(rows)} wallet(s) "
        f"({len(insider_rows)} insiders, {len(regular_rows)} regular), "
        f"min=${MIN_ACTIVITY_VALUE_USD:,.0f}, insider_min=${INSIDER_MIN_VALUE_USD:,.0f}",
        flush=True,
    )
    saved = 0
    alerted = 0

    # Process insiders first with lower threshold
    all_rows = insider_rows + regular_rows
    for index, row in enumerate(all_rows, 1):
        address = str(row.get("address") or "").strip()
        if not address:
            continue
        is_insider = _is_insider(row)
        threshold = INSIDER_MIN_VALUE_USD if is_insider else MIN_ACTIVITY_VALUE_USD
        activity = latest_activity(address, min_value_usd=threshold)
        if not activity:
            print(
                f"[{index}/{len(all_rows)}] {address[:12]}... no transfer >= ${threshold:,.0f}",
                flush=True,
            )
            continue
        label = activity.get("to_label") if activity.get("flow") == "out" else activity.get("from_label")
        is_new = _is_new_activity(row, activity)
        tag = "🕵️ INSIDER" if is_insider else "🐋"
        new_tag = " [NEW]" if is_new else ""
        print(
            f"[{index}/{len(all_rows)}] {tag} {row.get('entity')} {address[:12]}...{new_tag} "
            f"{activity['flow']} {activity.get('token') or 'token'} ${activity.get('value_usd', 0):,.0f} "
            f"at {(activity.get('timestamp') or '')[:10]} {('via ' + label) if label else ''}",
            flush=True,
        )
        if is_insider and is_new:
            send_insider_telegram(row, activity)
            save_insider_signal(row, activity)
            alerted += 1
        if save_activity(row, activity):
            saved += 1

    print(f"Saved activity: {saved}/{len(all_rows)}, insider alerts: {alerted}", flush=True)


if __name__ == "__main__":
    main()
