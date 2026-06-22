"""
Derived tactical analytics computed from provider data.

These functions take the normalised ShotEvent / GoalEvent lists from any
DataProvider and produce structured insights the LLM and PDF consume:
player danger score, goal circumstances, set-piece breakdown, timing, zones.

All pure functions — no I/O, no provider knowledge. They work identically on
ESPN data today and StatsBomb data tomorrow (the latter just adds real xG).
"""
from __future__ import annotations

from collections import Counter, defaultdict


# ---------------------------------------------------------------------------
# Player danger score
# ---------------------------------------------------------------------------

def player_danger_scores(shots: list[dict], goals: list[dict], top: int = 3) -> list[dict]:
    """Combine goals, assists, shots on target and xG (when present) into a
    single danger score per player. Returns the top N most dangerous."""
    stats: dict[str, dict] = defaultdict(lambda: {
        "goals": 0, "assists": 0, "shots": 0, "on_target": 0, "xg": 0.0,
    })

    for s in shots:
        if not s.get("is_for"):
            continue
        p = s.get("player") or "Unknown"
        stats[p]["shots"] += 1
        if s["result"] in ("goal", "on_target"):
            stats[p]["on_target"] += 1
        if s.get("xg"):
            stats[p]["xg"] += float(s["xg"])

    # Goals and assists come from keyEvents (authoritative) — the commentary
    # shot for a goal is often tagged "shot-on-target", not scoringPlay.
    for g in goals:
        if not g.get("is_for"):
            continue
        scorer = g.get("scorer")
        if scorer:
            stats[scorer]["goals"] += 1
        a = g.get("assister")
        if a:
            stats[a]["assists"] += 1

    scored = []
    for player, s in stats.items():
        if player == "Unknown":
            continue
        # Weighted danger score. xG dominates when available, else falls back
        # to goals/on-target volume.
        score = (
            s["goals"] * 4.0
            + s["assists"] * 2.5
            + s["on_target"] * 1.0
            + s["shots"] * 0.3
            + s["xg"] * 3.0
        )
        scored.append({
            "player": player,
            "score": round(score, 1),
            "goals": s["goals"],
            "assists": s["assists"],
            "shots": s["shots"],
            "on_target": s["on_target"],
            "xg": round(s["xg"], 2) if s["xg"] else None,
        })

    scored.sort(key=lambda d: d["score"], reverse=True)
    return scored[:top]


# ---------------------------------------------------------------------------
# Goal circumstances (how they score / concede)
# ---------------------------------------------------------------------------

_ASSIST_LABELS = {
    "cross": "Crosses",
    "corner": "Corners",
    "free_kick": "Free kicks",
    "penalty": "Penalties",
    "through_ball": "Through balls",
    "set_piece": "Set pieces",
    "open_play_pass": "Open-play passes",
    "unassisted": "Individual / unassisted",
}


def goal_circumstances(goals: list[dict], is_for: bool = True) -> dict:
    """Frequency of how goals were created (for or against the team)."""
    relevant = [g for g in goals if g.get("is_for") == is_for]
    total = len(relevant)
    if total == 0:
        return {"total": 0, "breakdown": [], "set_piece_pct": 0}

    counter = Counter(g.get("assist_type", "unassisted") for g in relevant)
    set_piece_types = {"corner", "free_kick", "penalty", "set_piece"}
    set_piece_goals = sum(c for t, c in counter.items() if t in set_piece_types)

    breakdown = [
        {"type": _ASSIST_LABELS.get(t, t), "count": c, "pct": round(c / total * 100)}
        for t, c in counter.most_common()
    ]
    return {
        "total": total,
        "breakdown": breakdown,
        "set_piece_pct": round(set_piece_goals / total * 100),
    }


# ---------------------------------------------------------------------------
# Set-piece breakdown
# ---------------------------------------------------------------------------

def set_piece_breakdown(goals: list[dict]) -> dict:
    """Classify set-piece goals scored and conceded."""
    def classify(subset):
        c = Counter()
        for g in subset:
            at = g.get("assist_type")
            if at in ("corner", "free_kick", "penalty", "set_piece"):
                c[at] += 1
        return dict(c)

    return {
        "scored": classify([g for g in goals if g.get("is_for")]),
        "conceded": classify([g for g in goals if not g.get("is_for")]),
    }


# ---------------------------------------------------------------------------
# Goal timing
# ---------------------------------------------------------------------------

def goal_minutes(goals: list[dict], is_for: bool = True) -> list[int]:
    return [g.get("minute_num", 0) for g in goals
            if g.get("is_for") == is_for and g.get("minute_num")]


# ---------------------------------------------------------------------------
# Shot side / zone tendencies
# ---------------------------------------------------------------------------

def shot_tendencies(shots: list[dict], is_for: bool = True) -> dict:
    """Left/right/central split and zone distribution for shots taken (for) or
    conceded (against)."""
    relevant = [s for s in shots if s.get("is_for") == is_for and s.get("y") is not None]
    total = len(relevant)
    if total == 0:
        return {"total": 0}

    left = sum(1 for s in relevant if s["y"] < 36)
    central = sum(1 for s in relevant if 36 <= s["y"] <= 64)
    right = sum(1 for s in relevant if s["y"] > 64)

    zones = Counter(s.get("zone", "box") for s in relevant)
    body = Counter(s.get("body_part", "other") for s in relevant)

    return {
        "total": total,
        "left_pct": round(left / total * 100),
        "central_pct": round(central / total * 100),
        "right_pct": round(right / total * 100),
        "zones": dict(zones),
        "body_parts": dict(body),
    }


# ---------------------------------------------------------------------------
# Build a compact text block for the LLM prompt
# ---------------------------------------------------------------------------

def insights_to_text(
    danger: list[dict],
    circ_for: dict,
    circ_against: dict,
    set_pieces: dict,
    tend_for: dict,
    tend_against: dict,
    has_xg: bool,
) -> str:
    lines: list[str] = []

    if danger:
        lines.append("TOP DANGER PLAYERS (combined goals/assists/shots" +
                     ("/xG" if has_xg else "") + "):")
        for d in danger:
            extra = f", xG {d['xg']}" if d.get("xg") else ""
            lines.append(
                f"  - {d['player']}: {d['goals']}G {d['assists']}A, "
                f"{d['on_target']}/{d['shots']} on target{extra} (danger {d['score']})"
            )

    if circ_for.get("total"):
        lines.append(f"\nHOW THEY SCORE ({circ_for['total']} goals):")
        for b in circ_for["breakdown"]:
            lines.append(f"  - {b['type']}: {b['count']} ({b['pct']}%)")
        lines.append(f"  - Set-piece goals: {circ_for['set_piece_pct']}% of total")

    if circ_against.get("total"):
        lines.append(f"\nHOW THEY CONCEDE ({circ_against['total']} goals):")
        for b in circ_against["breakdown"]:
            lines.append(f"  - {b['type']}: {b['count']} ({b['pct']}%)")
        lines.append(f"  - Conceded from set pieces: {circ_against['set_piece_pct']}%")

    if tend_for.get("total"):
        lines.append(
            f"\nATTACKING SHOT SIDES: left {tend_for['left_pct']}% | "
            f"central {tend_for['central_pct']}% | right {tend_for['right_pct']}% "
            f"({tend_for['total']} shots)"
        )
    if tend_against.get("total"):
        lines.append(
            f"SHOTS CONCEDED BY SIDE: left {tend_against['left_pct']}% | "
            f"central {tend_against['central_pct']}% | right {tend_against['right_pct']}% "
            f"({tend_against['total']} shots) — this reveals where they are vulnerable"
        )

    if not has_xg:
        lines.append("\nNOTE: xG not available from current data source — danger "
                     "scores use shot volume and outcomes. Will upgrade automatically "
                     "when a premium provider (StatsBomb/Wyscout) is connected.")

    return "\n".join(lines) if lines else "No shot-level data available for these matches."
