"""
Live end-to-end value scan — Football Bet.

Runs the full pipeline (Odds API + ESPN history + Poisson model) on a real
competition and prints the value bets it surfaces. In June the only in-season
competition is the World Cup, so it defaults there — useful to prove the
pipeline works end-to-end, with the honest caveat that World Cup samples are
tiny (group stage = ~3 games), so the sample warning will fire on most rows.
The SAME engine runs on Serie A / EPL in August with rich history.

Usage:
    cd backend && python -m worker._run_bet_scan [sport_key] [hours_ahead]
    e.g. python -m worker._run_bet_scan soccer_fifa_world_cup 36
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "Api"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))
except Exception:
    pass

from Api.services.bet_odds import OddsClient
from Api.services.bet_engine import scan

SPORT = sys.argv[1] if len(sys.argv) > 1 else "soccer_fifa_world_cup"
HOURS = int(sys.argv[2]) if len(sys.argv) > 2 else 36

c = OddsClient()
print(f"Scanning {SPORT} for fixtures in the next {HOURS}h ...\n")
results = scan(c, SPORT, hours_ahead=HOURS, last_n=8, min_edge=0.02, max_events=8)

total_edges = 0
for mv in results:
    hh, ah = mv.home_hist, mv.away_hist
    hist_note = (f"hist: {mv.home}[g{len(hh.goals_for)}/c{len(hh.corners_for)}/k{len(hh.cards_for)}] "
                 f"{mv.away}[g{len(ah.goals_for)}/c{len(ah.corners_for)}/k{len(ah.cards_for)}]")
    print(f"== {mv.home} vs {mv.away}  ({mv.commence})")
    print(f"   {hist_note}")
    if not (hh.resolved and ah.resolved):
        print("   (one or both teams unresolved in ESPN — no model rate)")
    if not mv.edges:
        print("   no positive-edge bets")
    for r in mv.edges:
        total_edges += 1
        warn = f"  WARN: {r['warning']}" if r["warning"] else ""
        print(f"   VALUE {r['market']:7} {r['side']:5} {r['line']:>5} @ {r['odd']:.2f} "
              f"({r['book']}) | model {r['model_prob']:.0%} vs fair {r['fair_prob']:.0%} "
              f"| edge {r['edge']:+.1%} EV {r['ev_per_unit']:+.2f} | lam={r['lambda']}{warn}")
    print()

print(f"Surfaced {total_edges} value rows across {len(results)} matches.  "
      f"Quota remaining={c.quota.remaining}")
