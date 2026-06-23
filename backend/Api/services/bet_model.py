"""
Value model — Football Bet project.

Two pure pieces, no I/O, fully unit-testable:

  1. estimate_rate(history)  -> expected count per game (the Poisson lambda) for a
     count market (corners, cards, goals, shots). Uses a shrinkage estimate so a
     5-game sample doesn't overreact (pulls toward the league prior).

  2. value_edge(...)         -> given our lambda and a bookmaker's over/under odd
     at a line, compute our model probability via Poisson, the odd's implied
     probability (de-vigged), and the edge. Positive edge = the bet the tool
     surfaces.

HONEST FRAMING (non-negotiable, per project_football_bet): this is an
*informational* divergence finder, not a profit promise. Bookmakers price well
and add margin (vig); +EV is hard. The model's job is to surface where our
data-derived estimate disagrees with the priced probability — and to be loud
about small samples. Nothing here guarantees anything.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

# League priors (avg combined-per-game) — coarse, refined empirically once we
# have ESPN-derived season averages. Used only for shrinkage of tiny samples.
LEAGUE_PRIOR = {
    "corners": 10.2,
    "cards": 4.4,        # yellow+red, combined both teams
    "goals": 2.7,
    "shots_on_target": 8.5,
}

# Shrinkage strength: equivalent number of "prior games". With k=4, a 5-game
# sample is weighted 5/(5+4)=0.56 toward observed, 0.44 toward the league prior.
SHRINK_K = 4.0


def estimate_rate(history: list[float], market: str) -> float:
    """Shrunken mean of a per-game count series toward the league prior.

    history: list of per-game counts (e.g. corners won per game, last N games).
    Returns the Poisson lambda to use for that market.
    """
    prior = LEAGUE_PRIOR.get(market, 0.0)
    n = len(history)
    if n == 0:
        return prior
    obs_mean = sum(history) / n
    if prior <= 0:
        return obs_mean
    w = n / (n + SHRINK_K)
    return w * obs_mean + (1 - w) * prior


def poisson_cdf(k: int, lam: float) -> float:
    """P(X <= k) for X ~ Poisson(lam)."""
    if lam <= 0:
        return 1.0
    total = 0.0
    term = math.exp(-lam)   # P(X=0)
    for i in range(0, k + 1):
        if i > 0:
            term *= lam / i
        total += term
    return min(1.0, total)


def prob_over(line: float, lam: float) -> float:
    """P(count > line) for a Poisson(lam) count.
    For a half-line like 9.5, over means X >= 10, i.e. 1 - CDF(9)."""
    k = math.floor(line)            # 9.5 -> 9 ; integer line 9 -> push handling below
    p_le = poisson_cdf(k, lam)
    # For a whole-number line the exact-equal outcome is a push (void). We treat
    # over as strictly greater: P(X > line) = 1 - P(X <= floor(line)) works for
    # half-lines; for whole lines the bookmaker voids ties so over = X > line.
    return max(0.0, 1.0 - p_le)


def implied_prob(odd: float) -> float:
    return 1.0 / odd if odd and odd > 0 else 0.0


def devig_two_way(over_odd: float, under_odd: float) -> tuple[float, float]:
    """Remove the bookmaker margin from a 2-way market, returning fair
    (over, under) probabilities that sum to 1."""
    po, pu = implied_prob(over_odd), implied_prob(under_odd)
    s = po + pu
    if s <= 0:
        return 0.0, 0.0
    return po / s, pu / s


@dataclass
class Edge:
    market: str
    line: float
    side: str            # "over" | "under"
    odd: float
    model_prob: float
    fair_prob: float     # de-vigged implied prob from the book
    implied_prob: float  # raw implied (with vig)
    edge: float          # model_prob - fair_prob
    ev_per_unit: float   # model_prob*odd - 1
    n_games: int
    lam: float

    @property
    def is_value(self) -> bool:
        return self.edge > 0 and self.ev_per_unit > 0

    @property
    def sample_warning(self) -> str | None:
        if self.n_games < 6:
            return f"thin sample ({self.n_games} games) - treat as indicative only"
        return None


def value_edge(market: str, line: float, over_odd: float, under_odd: float,
               history: list[float]) -> list[Edge]:
    """Compute edges for both sides of a count over/under market.

    Returns one Edge per side (over, under). Caller filters .is_value and sorts.
    """
    lam = estimate_rate(history, market)
    n = len(history)
    p_over_model = prob_over(line, lam)
    p_under_model = 1.0 - p_over_model
    fair_over, fair_under = devig_two_way(over_odd, under_odd)

    edges = []
    for side, p_model, odd, fair in (
        ("over", p_over_model, over_odd, fair_over),
        ("under", p_under_model, under_odd, fair_under),
    ):
        if not odd or odd <= 1:
            continue
        edges.append(Edge(
            market=market, line=line, side=side, odd=odd,
            model_prob=p_model, fair_prob=fair, implied_prob=implied_prob(odd),
            edge=p_model - fair, ev_per_unit=p_model * odd - 1.0,
            n_games=n, lam=lam,
        ))
    return edges
