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

    # Small sample: below 3 goals, percentages mislead — flag it so callers can
    # show absolute counts instead.
    small_sample = total < 3

    breakdown = [
        {"type": _ASSIST_LABELS.get(t, t), "count": c, "pct": round(c / total * 100)}
        for t, c in counter.most_common()
    ]
    return {
        "total": total,
        "breakdown": breakdown,
        "set_piece_pct": round(set_piece_goals / total * 100),
        "set_piece_goals": set_piece_goals,
        "small_sample": small_sample,
    }


def fmt_circumstance(circ: dict) -> list[str]:
    """Render circumstance breakdown as display strings, honouring small sample
    (counts instead of percentages, with a flag)."""
    total = circ.get("total", 0)
    if not total:
        return []
    small = circ.get("small_sample")
    out = []
    for b in circ["breakdown"]:
        if small:
            out.append(f"{b['type']}: {b['count']}/{total} goals")
        else:
            out.append(f"{b['type']}: {b['pct']}%")
    if small:
        out.append("(small sample — based on few matches)")
    return out


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


def goal_log(goals: list[dict], is_for: bool = True) -> list[str]:
    """Chronological list of 'Scorer MIN'' strings (e.g. 'Gakpo 47'')."""
    rel = [g for g in goals if g.get("is_for") == is_for]
    rel.sort(key=lambda g: g.get("minute_num", 0))
    out = []
    for g in rel:
        scorer = g.get("scorer") or "?"
        # surname only to keep it compact
        scorer = scorer.split()[-1] if scorer != "?" else scorer
        minute = g.get("minute", "")
        if minute and not minute.endswith("'"):
            minute += "'"
        out.append(f"{scorer} {minute}".strip())
    return out


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
# Key alerts — punchy, data-driven flags for coaching staff
# ---------------------------------------------------------------------------

_TIMING_LABELS = {0: "0-15'", 1: "16-30'", 2: "31-45'", 3: "46-60'", 4: "61-75'", 5: "76-90'+"}


def key_alerts(
    shots: list[dict],
    goals: list[dict],
    danger: list[dict],
    circ_for: dict,
    tend_against: dict,
    lang: str = "en",
) -> list[str]:
    """Generate short, high-signal alerts a coach reads first. Each is only
    emitted when the data crosses a meaningful threshold — no filler."""
    pt = lang == "pt"
    alerts: list[str] = []

    # 1. Single player carrying the attack (share of team shots on target)
    team_on_target = sum(1 for s in shots if s.get("is_for") and s["result"] in ("goal", "on_target"))
    if danger and team_on_target >= 4:
        top = danger[0]
        share = round((top["on_target"] / team_on_target) * 100) if team_on_target else 0
        if share >= 35:
            alerts.append(
                f"{top['player']} responsável por {share}% dos remates ao alvo da equipa"
                if pt else
                f"{top['player']} responsible for {share}% of the team's shots on target"
            )

    # 2. Where they concede (central vulnerability)
    if tend_against.get("total", 0) >= 5:
        c = tend_against.get("central_pct", 0)
        l, r = tend_against.get("left_pct", 0), tend_against.get("right_pct", 0)
        if c >= 50:
            alerts.append(
                f"{c}% dos remates sofridos vêm pelo centro" if pt
                else f"{c}% of shots conceded come centrally"
            )
        elif max(l, r) >= 45:
            side = ("esquerda" if l > r else "direita") if pt else ("left" if l > r else "right")
            alerts.append(
                f"{max(l, r)}% dos remates sofridos vêm pela {side}" if pt
                else f"{max(l, r)}% of shots conceded come from the {side}"
            )

    # 3. Set-piece threat — only as a % with a real sample; with few goals,
    # state it in absolute counts so we never show a misleading "100%".
    sp = circ_for.get("set_piece_pct", 0)
    sp_goals = circ_for.get("set_piece_goals", 0)
    total_g = circ_for.get("total", 0)
    if total_g >= 3 and sp >= 33:
        alerts.append(
            f"{sp}% dos golos vêm de bolas paradas — ameaça em lances parados" if pt
            else f"{sp}% of goals come from set pieces — set-piece threat"
        )
    elif sp_goals >= 2:
        alerts.append(
            f"{sp_goals} dos {total_g} golos de bolas paradas — atenção a lances parados" if pt
            else f"{sp_goals} of {total_g} goals from set pieces — watch set pieces"
        )

    # 4. Highest danger period (goal timing for)
    minutes = [g.get("minute_num", 0) for g in goals if g.get("is_for") and g.get("minute_num")]
    if len(minutes) >= 2:
        buckets = [0] * 6
        bands = [(0, 15), (16, 30), (31, 45), (46, 60), (61, 75), (76, 200)]
        for mn in minutes:
            for i, (lo, hi) in enumerate(bands):
                if lo <= mn <= hi:
                    buckets[i] += 1
                    break
        peak = max(range(6), key=lambda i: buckets[i])
        if buckets[peak] >= 2:
            alerts.append(
                f"Período mais perigoso: {_TIMING_LABELS[peak]}" if pt
                else f"Highest danger period: {_TIMING_LABELS[peak]}"
            )

    # 5. Conceding pattern timing (vulnerability window)
    minutes_against = [g.get("minute_num", 0) for g in goals if not g.get("is_for") and g.get("minute_num")]
    if len(minutes_against) >= 2:
        buckets = [0] * 6
        bands = [(0, 15), (16, 30), (31, 45), (46, 60), (61, 75), (76, 200)]
        for mn in minutes_against:
            for i, (lo, hi) in enumerate(bands):
                if lo <= mn <= hi:
                    buckets[i] += 1
                    break
        peak = max(range(6), key=lambda i: buckets[i])
        if buckets[peak] >= 2:
            alerts.append(
                f"Vulneráveis a sofrer golos no período {_TIMING_LABELS[peak]}" if pt
                else f"Vulnerable to conceding in the {_TIMING_LABELS[peak]} window"
            )

    return alerts


# ---------------------------------------------------------------------------
# Tactical evolution — match-by-match formation/XI changes
# ---------------------------------------------------------------------------

def tactical_evolution(per_match: list[dict]) -> dict:
    """Analyse how a team's formation and XI changed across recent matches.

    per_match: output of ESPNProvider.get_formation_per_match() — list of
    {date, opponent, score, result, formation_name, starters} sorted oldest→newest.

    Returns:
        matches:               same list with 'changes_from_prev' added
        most_common_formation: most-used formation string
        formation_changes:     how many times formation changed
        avg_xi_changes:        average starters swapped match-to-match
        summary:               2-4 coaching-friendly summary lines
    """
    if not per_match:
        return {}

    from collections import Counter as _Counter
    enriched = []
    xi_change_counts: list[int] = []
    formation_seq: list[str] = []

    for i, m in enumerate(per_match):
        starters_now = set(m.get("starters", []))
        formation_now = m.get("formation_name", "")
        changes: list[str] = []

        if i == 0:
            changes = []
        else:
            prev = per_match[i - 1]
            starters_prev = set(prev.get("starters", []))
            formation_prev = prev.get("formation_name", "")
            # Formation change
            if formation_now and formation_prev and formation_now != formation_prev:
                changes.append(f"Formation: {formation_prev} → {formation_now}")
            # XI changes
            out = starters_prev - starters_now
            into = starters_now - starters_prev
            n_changes = max(len(out), len(into))
            xi_change_counts.append(n_changes)
            if n_changes == 0:
                changes.append("Unchanged XI")
            else:
                for o, inn in zip(sorted(out)[:4], sorted(into)[:4]):
                    changes.append(f"{inn.split()[-1]} in for {o.split()[-1]}")
                remaining = n_changes - 4
                if remaining > 0:
                    changes.append(f"+{remaining} more change{'s' if remaining > 1 else ''}")

        enriched.append({**m, "changes_from_prev": changes})
        if formation_now:
            formation_seq.append(formation_now)

    formation_counter = _Counter(formation_seq)
    most_common = formation_counter.most_common(1)[0][0] if formation_counter else ""

    # Count formation changes
    f_changes = sum(
        1 for i in range(1, len(formation_seq))
        if formation_seq[i] and formation_seq[i - 1] and formation_seq[i] != formation_seq[i - 1]
    )

    avg_changes = round(sum(xi_change_counts) / len(xi_change_counts), 1) if xi_change_counts else 0.0

    # Summary lines for coaching staff
    summary: list[str] = []
    n = len(per_match)
    mc_count = formation_counter.get(most_common, 0) if most_common else 0
    if most_common:
        summary.append(
            f"{'Consistent' if mc_count >= n - 1 else 'Primarily'} {most_common} "
            f"({mc_count} of {n} matches)"
        )
    if f_changes == 0 and most_common:
        summary.append("No formation changes — tactically predictable")
    elif f_changes == 1:
        # Find where it changed
        for i in range(1, len(enriched)):
            c = enriched[i].get("changes_from_prev", [])
            if any("Formation:" in x for x in c):
                summary.append(
                    f"Formation changed once (vs {enriched[i]['opponent']}, {enriched[i]['date']})"
                )
                break
    elif f_changes >= 2:
        summary.append(f"Rotated formations {f_changes} times — tactically flexible")

    if avg_changes > 0:
        summary.append(f"Avg {avg_changes} lineup changes per game")

    # Results per formation
    form_results: dict[str, list[str]] = {}
    for m in per_match:
        fn = m.get("formation_name", "")
        if fn:
            form_results.setdefault(fn, []).append(m.get("result", "?"))
    for fn, results in form_results.items():
        w = results.count("W")
        d = results.count("D")
        l = results.count("L")
        if len(results) >= 2:
            summary.append(f"In {fn}: {w}W {d}D {l}L")

    return {
        "matches": enriched,
        "most_common_formation": most_common,
        "formation_changes": f_changes,
        "avg_xi_changes": avg_changes,
        "summary": summary[:4],  # cap at 4 lines
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
