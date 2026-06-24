"""Follow-up probe: remove the off-season confound.

The first probe tested August fixtures (~2 months out) — corner/card prop
markets may simply not be posted yet that far ahead. This one scans ALL active
soccer competitions, finds the SOONEST kicking-off event across them, and tests
corners/cards there. If even an imminent match has no corners/cards from any
bookmaker, the absence is real (not a timing artifact).
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "Api"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))
except Exception:
    pass

from Api.services.bet_odds import OddsClient, OddsAPIError, ADDITIONAL_MARKETS

c = OddsClient()
sports = c.list_sports()
soccer = [s for s in sports if s.get("key", "").startswith("soccer_") and s.get("active")]
print(f"Active soccer competitions: {len(soccer)}")
for s in soccer:
    print(f"  {s['key']:38} {s['title']}")

# Gather the nearest upcoming event per competition (0-credit /events calls).
nearest = []
for s in soccer:
    try:
        evs = c.list_events(s["key"])
    except OddsAPIError as e:
        print(f"  ! {s['key']}: {e}"); continue
    for e in evs:
        ct = e.get("commence_time", "")
        nearest.append((ct, s["key"], e))
nearest.sort(key=lambda t: t[0])

print(f"\nSoonest 8 events across all soccer comps (today is ~2026-06-24):")
for ct, key, e in nearest[:8]:
    print(f"  {ct}  {key:34} {e.get('home_team')} vs {e.get('away_team')}")

# Test corners/cards on the 3 soonest events from IN-SEASON comps.
print("\n=== corners/cards test on the 3 soonest events ===")
for ct, key, e in nearest[:3]:
    print(f"\n{ct}  {key}  {e.get('home_team')} vs {e.get('away_team')}")
    for mkt in ADDITIONAL_MARKETS:
        try:
            data = c.event_odds(key, e["id"], [mkt])
            bks = data.get("bookmakers", [])
            got = sum(1 for b in bks for m in b.get("markets", []) if m.get("key") == mkt)
            sample = ""
            for b in bks:
                for m in b.get("markets", []):
                    if m.get("key") == mkt and m.get("outcomes"):
                        o = m["outcomes"][0]
                        sample = f"  e.g. {b['title']}: {o.get('name')} {o.get('point','')}@{o.get('price')}"
                        break
                if sample: break
            print(f"  {mkt:28} books={got}{sample}  [rem={c.quota.remaining} cost={c.quota.last_cost}]")
        except OddsAPIError as ex:
            print(f"  {mkt:28} ERROR: {ex}")

print(f"\nFinal quota: remaining={c.quota.remaining}")
