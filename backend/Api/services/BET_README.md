# Football Bet — value engine

Informational **value-betting** tool: for each upcoming match it crosses real
bookmaker odds (The Odds API) with our own probability estimate (Poisson over
ESPN per-game history) and surfaces where the two disagree.

> **Honest framing (non-negotiable).** This is a *divergence finder*, not a
> profit promise. Bookmakers price well and add margin (vig); genuine +EV is
> hard and rare. Corners/cards on the free tier come almost only from
> **Pinnacle** — the sharpest book — so its de-vigged price is close to the true
> probability; treat those as "model-vs-sharp" signals. The tool's value is
> filtering + discipline (staking, record-keeping), not guaranteed wins.

## Pieces
- `bet_odds.py` — The Odds API client (free tier: 500 credits/month; reads
  `ODDS_API_KEY` from `.env`). Tracks remaining credits via response headers.
- `bet_model.py` — Poisson with shrinkage (`estimate_rate` / `match_total_lambda`
  pull small samples toward the league prior), `prob_over`, de-vig, edge calc.
- `bet_engine.py` — joins odds + ESPN history per fixture → value rows.

## Empirical findings (24 Jun 2026, real calls)
- Free tier returns **goals O/U (totals)** from many books (Pinnacle + soft
  books), **BTTS**, **h2h** — broad coverage, even weeks ahead.
- **Corners & cards O/U DO exist** but: only from **~Pinnacle**, and only on the
  **per-event** endpoint **close to kickoff** (hours, not weeks). Far-out and
  lower-league fixtures return nothing. So the tool must run **on matchday**.
- The big-five leagues are **off-season until ~21 Aug 2026**; live testing now is
  only possible on the World Cup (tiny samples → warnings fire on every row).

## Run
```bash
# 1. put your key in repo-root .env:   ODDS_API_KEY=...
# 2. confirm which markets the tier returns (spends a few credits):
cd backend && python -m worker._probe_odds_api
cd backend && python -m worker._probe_odds_inseason     # nearest in-season match
# 3. unit-test the model (no API/credits):
cd backend && python -m worker._test_bet_model
# 4. live end-to-end scan (defaults to World Cup in June):
cd backend && python -m worker._run_bet_scan soccer_fifa_world_cup 36
#    in August, point it at a real league:
cd backend && python -m worker._run_bet_scan soccer_italy_serie_a 72
```

## Next (when the big leagues are in season)
1. Run the scan on Serie A / EPL matchdays — with 8+ game histories the
   shrinkage settles and edges become sober (no more 2-game λ=14 noise).
2. Wire a FastAPI endpoint + a frontend page (reuse the Lab's stack) showing the
   value rows with the sample warning front-and-centre.
3. Calibrate the league priors in `bet_model.LEAGUE_PRIOR` from real ESPN season
   averages per competition.
