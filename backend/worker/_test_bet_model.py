"""Sanity test for bet_model — pure math, runs without any API key."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "Api"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from Api.services.bet_model import (
    estimate_rate, poisson_cdf, prob_over, devig_two_way, value_edge, LEAGUE_PRIOR,
)

def approx(a, b, t=1e-6): return abs(a - b) < t

print("== poisson_cdf sanity (lam=3) ==")
# Known: Poisson(3) P(X<=2)=0.4232, P(X<=3)=0.6472
print(f"  P(X<=2)={poisson_cdf(2,3):.4f}  expected 0.4232  {'OK' if approx(poisson_cdf(2,3),0.42319,1e-4) else 'FAIL'}")
print(f"  P(X<=3)={poisson_cdf(3,3):.4f}  expected 0.6472  {'OK' if approx(poisson_cdf(3,3),0.64723,1e-4) else 'FAIL'}")

print("\n== shrinkage (corners prior=10.2, k=4) ==")
hot = [13,14,12,15,13]   # 5 games, mean 13.4
lam = estimate_rate(hot, "corners")
w = 5/(5+4)
exp = w*13.4 + (1-w)*10.2
print(f"  5-game mean 13.4 -> shrunk lambda {lam:.3f} (expected {exp:.3f}) "
      f"{'OK' if approx(lam,exp,1e-3) else 'FAIL'}")
print(f"  empty history -> prior {estimate_rate([], 'corners'):.2f} "
      f"{'OK' if approx(estimate_rate([],'corners'),10.2) else 'FAIL'}")

print("\n== prob_over: corners line 9.5, lambda 11.2 ==")
lam2 = 11.2
p = prob_over(9.5, lam2)   # P(X>=10) = 1 - P(X<=9)
print(f"  P(corners > 9.5) = {p:.4f}  (1 - cdf(9,11.2)={1-poisson_cdf(9,11.2):.4f})")

print("\n== de-vig ==")
fo, fu = devig_two_way(1.83, 1.91)
print(f"  over@1.83 under@1.91 -> fair over {fo:.4f} under {fu:.4f} (sum={fo+fu:.4f}) "
      f"{'OK' if approx(fo+fu,1.0) else 'FAIL'}")

print("\n== END-TO-END value scenario ==")
print("  Scenario: team averaging ~13 corners/g (hot), book offers Over 9.5 @ 1.83 / Under 9.5 @ 1.91")
edges = value_edge("corners", 9.5, 1.83, 1.91, hot)
for e in edges:
    flag = "  <-- VALUE" if e.is_value else ""
    print(f"  {e.side:5} line {e.line} @ {e.odd:.2f} | model {e.model_prob:.1%} "
          f"vs fair {e.fair_prob:.1%} | edge {e.edge:+.1%} | EV/unit {e.ev_per_unit:+.3f}{flag}")
    if e.sample_warning:
        print(f"        warn: {e.sample_warning}")

print("\n  Counter-scenario: average team (~10 corners/g), same line/odds")
avg = [11,9,10,12,8,10,11,9]  # 8 games, mean 10
edges2 = value_edge("corners", 9.5, 1.83, 1.91, avg)
for e in edges2:
    flag = "  <-- VALUE" if e.is_value else ""
    print(f"  {e.side:5} line {e.line} @ {e.odd:.2f} | model {e.model_prob:.1%} "
          f"vs fair {e.fair_prob:.1%} | edge {e.edge:+.1%} | EV/unit {e.ev_per_unit:+.3f}{flag}")

print("\nDone.")
