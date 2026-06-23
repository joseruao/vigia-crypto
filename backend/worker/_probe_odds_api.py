"""
Empirical probe of The Odds API free tier — Football Bet project.

PRINCIPLE OF THE PROJECT: test before promising. This script answers, with real
calls (not docs), the only question that decides whether the project is viable:

    Does the free tier actually return CORNERS and CARDS over/under odds for the
    big European leagues, and from which bookmakers?

Run (once ODDS_API_KEY is in .env):
    cd backend && python -m worker._probe_odds_api

It spends a tightly-budgeted handful of credits (well under the 500/month free
quota) and prints a verdict table: per market, whether data came back, how many
bookmakers offered it, and a sample line. Stops early if quota runs low.
"""
from __future__ import annotations

import os
import sys

# allow `python backend/worker/_probe_odds_api.py` as well as -m
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "Api"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

from Api.services.bet_odds import (  # noqa: E402
    OddsClient, OddsAPIError, LEAGUE_KEYS, FEATURED_MARKETS, ADDITIONAL_MARKETS,
)

PROBE_LEAGUES = ["serie_a", "epl", "brazil"]   # the high-sample leagues we care about


def _q(c: OddsClient) -> str:
    return f"[used={c.quota.used} remaining={c.quota.remaining} lastcost={c.quota.last_cost}]"


def main() -> int:
    try:
        c = OddsClient()
    except OddsAPIError as e:
        print(f"\n  BLOCKED: {e}\n")
        return 1

    print("=" * 72)
    print("THE ODDS API — FREE TIER EMPIRICAL PROBE")
    print("=" * 72)

    # 1) sports list (free) — confirm leagues are live
    sports = c.list_sports()
    active = {s["key"]: s for s in sports if s.get("active")}
    print(f"\n[1] /sports (0 credits): {len(active)} active sports.")
    for name in PROBE_LEAGUES:
        key = LEAGUE_KEYS[name]
        mark = "OK" if key in active else "MISSING"
        title = active.get(key, {}).get("title", "—")
        print(f"    {mark:8} {name:10} {key:28} {title}")

    verdict: dict[str, dict] = {}

    for name in PROBE_LEAGUES:
        key = LEAGUE_KEYS[name]
        if key not in active:
            continue
        print(f"\n[2] {name} ({key})")

        # events (free)
        events = c.list_events(key)
        print(f"    /events (0 credits): {len(events)} upcoming  {_q(c)}")
        if not events:
            print("    (no upcoming fixtures — off-season? try another league)")
            continue
        ev = events[0]
        print(f"    probe event: {ev.get('home_team')} vs {ev.get('away_team')}  ({ev.get('commence_time')})")

        # featured markets (billed) — goals totals, h2h, btts
        if c.quota.remaining is not None and c.quota.remaining < 20:
            print("    quota low — skipping billed calls"); break
        try:
            feat = c.event_odds(key, ev["id"], FEATURED_MARKETS)
            _record(verdict, name, feat, FEATURED_MARKETS)
            print(f"    featured {FEATURED_MARKETS}: bookmakers={len(feat.get('bookmakers', []))}  {_q(c)}")
        except OddsAPIError as e:
            print(f"    featured FAILED: {e}")

        # additional markets (billed) — THE decisive test: corners + cards
        if c.quota.remaining is not None and c.quota.remaining < 20:
            print("    quota low — skipping additional calls"); break
        for mkt in ADDITIONAL_MARKETS:
            try:
                data = c.event_odds(key, ev["id"], [mkt])
                _record(verdict, name, data, [mkt])
                bks = data.get("bookmakers", [])
                got = sum(1 for b in bks for m in b.get("markets", []) if m.get("key") == mkt)
                sample = _sample(bks, mkt)
                print(f"    +{mkt:28} bookmakers_with_it={got:2}  {sample}  {_q(c)}")
            except OddsAPIError as e:
                print(f"    +{mkt:28} FAILED: {e}")

    _verdict_table(verdict)
    print(f"\nFinal quota {_q(c)}")
    return 0


def _record(verdict, league, data, markets):
    for b in data.get("bookmakers", []):
        for m in b.get("markets", []):
            k = m.get("key")
            if k in markets:
                d = verdict.setdefault(k, {"books": set(), "leagues": set()})
                d["books"].add(b.get("title", b.get("key")))
                d["leagues"].add(league)


def _sample(bookmakers, market_key) -> str:
    for b in bookmakers:
        for m in b.get("markets", []):
            if m.get("key") != market_key:
                continue
            outs = m.get("outcomes", [])[:2]
            bits = [f"{o.get('name')} {o.get('point','')}@{o.get('price')}" for o in outs]
            return f"{b.get('title')}: " + " | ".join(bits)
    return "(none)"


def _verdict_table(verdict):
    print("\n" + "=" * 72)
    print("VERDICT — which markets the free tier actually returns")
    print("=" * 72)
    all_markets = FEATURED_MARKETS + ADDITIONAL_MARKETS
    for mkt in all_markets:
        d = verdict.get(mkt)
        if d:
            print(f"  YES  {mkt:28} books={len(d['books']):2}  "
                  f"leagues={sorted(d['leagues'])}  e.g. {sorted(d['books'])[:3]}")
        else:
            print(f"  no   {mkt:28} (no bookmaker returned this market)")
    corners = any(k.endswith("corners") or "corners" in k for k in verdict if "corner" in k)
    cards = any("cards" in k for k in verdict)
    print("\n  >>> CORNERS available:", "YES" if corners else "NO")
    print("  >>> CARDS   available:", "YES" if cards else "NO")
    print("  (If both NO for EU leagues, the free tier can't feed the core product — "
          "report to José before building the value engine.)")


if __name__ == "__main__":
    raise SystemExit(main())
