"""
Visualisations for football scout reports — shot heatmaps, goal-timing charts.

IMPORTANT: matplotlib must use the headless 'Agg' backend. On Railway there is
no display server; importing pyplot without this line crashes the worker.
The line MUST run before pyplot is imported anywhere.
"""
from __future__ import annotations

import matplotlib
matplotlib.use("Agg")  # noqa: E402  — must precede pyplot import

import base64  # noqa: E402
from io import BytesIO  # noqa: E402

import matplotlib.pyplot as plt  # noqa: E402

# mplsoccer is optional at import time so the rest of the app still boots if the
# dependency is missing; callers check viz_available().
try:
    from mplsoccer import VerticalPitch
    _MPL_SOCCER = True
except Exception:  # pragma: no cover
    _MPL_SOCCER = False


_BG = "#0f172a"        # slate-950 (matches PDF cover)
_LINE = "#94a3b8"      # slate-400
_GOAL = "#22c55e"      # green-500
_SHOT = "#60a5fa"      # blue-400
_MISS = "#64748b"      # slate-500
_TEXT = "#e2e8f0"      # slate-200


def viz_available() -> bool:
    return _MPL_SOCCER


def _b64(png: bytes | None) -> str | None:
    if not png:
        return None
    return "data:image/png;base64," + base64.b64encode(png).decode("ascii")


def render_scout_images(viz: dict, team: str, labels: dict | None = None) -> dict:
    """Render all scout charts as base64 data URIs for inline web display.
    Returns {} if mplsoccer is unavailable. Never raises."""
    if not _MPL_SOCCER or not viz:
        return {}
    L = labels or {
        "shots_taken": "Shots Taken", "shots_conceded": "Shots Conceded",
        "goal_timing": "Goal Timing", "probable_lineup": "Probable XI",
    }
    out: dict = {}
    try:
        shots = viz.get("shots", [])
        if shots:
            has_xg = bool(viz.get("has_xg"))
            sf = [s for s in shots if s.get("is_for")]
            sa = [s for s in shots if not s.get("is_for")]
            out["shotmap_for"] = _b64(build_shot_map(sf, f"{team} — {L['shots_taken']}", has_xg))
            out["shotmap_against"] = _b64(build_shot_map(sa, f"{team} — {L['shots_conceded']}", has_xg))
            out["timing"] = _b64(build_timing_chart(
                viz.get("goal_minutes_for", []), viz.get("goal_minutes_against", []),
                f"{team} — {L['goal_timing']}"))
        if viz.get("formation", {}).get("players"):
            out["formation"] = _b64(build_formation_pitch(
                viz["formation"], f"{team} — {L['probable_lineup']}"))
    except Exception:
        return {k: v for k, v in out.items() if v}
    return {k: v for k, v in out.items() if v}


# ---------------------------------------------------------------------------
# Coordinate mapping
# ---------------------------------------------------------------------------
# ESPN gives x,y in 0-100. x grows toward the attacking goal, y is width.
# mplsoccer statsbomb pitch is 120 (length) x 80 (width).
# We use a VerticalPitch (attacking upward) showing only the attacking half.

def _to_pitch(x: float, y: float) -> tuple[float, float]:
    px = x / 100.0 * 120.0
    py = y / 100.0 * 80.0
    return px, py


def _shot_size(shot: dict) -> float:
    xg = shot.get("xg")
    if xg:
        return max(60.0, min(float(xg) * 900.0, 600.0))
    # No xG: size by zone proximity as a danger proxy
    zone = shot.get("zone", "box")
    return {"six_yard": 280, "box": 200, "outside_box": 130, "long_range": 90}.get(zone, 150)


# ---------------------------------------------------------------------------
# Shot map (real coordinates)
# ---------------------------------------------------------------------------

def build_shot_map(shots: list[dict], title: str, has_xg: bool = False) -> bytes | None:
    """Render a vertical half-pitch shot map. Returns PNG bytes, or None if
    mplsoccer is unavailable or there are no shots with coordinates."""
    if not _MPL_SOCCER:
        return None
    coord_shots = [s for s in shots if s.get("x") is not None and s.get("y") is not None]
    if not coord_shots:
        return None

    pitch = VerticalPitch(
        pitch_type="statsbomb", half=True,
        pitch_color=_BG, line_color=_LINE, linewidth=1.2, line_zorder=2,
    )
    fig, ax = pitch.draw(figsize=(7, 5.2))
    fig.set_facecolor(_BG)

    # Non-goal shots first (so goals render on top)
    for s in coord_shots:
        if s["result"] == "goal":
            continue
        px, py = _to_pitch(s["x"], s["y"])
        color = _MISS if has_xg else _SHOT
        pitch.scatter(
            px, py, s=_shot_size(s),
            c=color, edgecolors="white", linewidths=0.3, alpha=0.6,
            marker="o", ax=ax, zorder=3,
        )

    # Goals on top with the football marker (no linewidth kwarg — mplsoccer
    # sets its own for this marker)
    for s in coord_shots:
        if s["result"] != "goal":
            continue
        px, py = _to_pitch(s["x"], s["y"])
        pitch.scatter(
            px, py, s=_shot_size(s) * 1.3,
            c=_GOAL, edgecolors="white", alpha=0.95,
            marker="football", ax=ax, zorder=5,
        )

    goals = sum(1 for s in coord_shots if s["result"] == "goal")
    on_t = sum(1 for s in coord_shots if s["result"] in ("goal", "on_target"))
    ax.set_title(
        f"{title}\n{len(coord_shots)} shots  |  {on_t} on target  |  {goals} goals",
        color=_TEXT, fontsize=11, pad=8,
    )

    # Legend
    from matplotlib.lines import Line2D
    handles = [
        Line2D([0], [0], marker="o", color=_BG, markerfacecolor=_GOAL,
               markeredgecolor="white", markersize=10, label="Goal"),
        Line2D([0], [0], marker="o", color=_BG, markerfacecolor=_SHOT,
               markeredgecolor="white", markersize=10, label="Shot"),
    ]
    leg = ax.legend(handles=handles, loc="lower center", ncol=2,
                    frameon=False, fontsize=8, labelcolor=_TEXT,
                    bbox_to_anchor=(0.5, -0.04))

    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=150, facecolor=_BG, bbox_inches="tight")
    plt.close(fig)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Formation pitch (probable XI laid out by position)
# ---------------------------------------------------------------------------

def build_formation_pitch(formation: dict, title: str) -> bytes | None:
    """Render the starting XI on a full vertical pitch at their positions."""
    if not _MPL_SOCCER:
        return None
    players = formation.get("players", [])
    if len(players) < 11:
        return None

    pitch = VerticalPitch(
        pitch_type="statsbomb", half=False,
        pitch_color=_BG, line_color=_LINE, linewidth=1.2, line_zorder=2,
    )
    fig, ax = pitch.draw(figsize=(6.5, 9))
    fig.set_facecolor(_BG)

    # Spread players that share the same vertical band so their name labels
    # don't collide. Group by rounded y (length band) and re-space x evenly.
    from collections import defaultdict
    bands: dict = defaultdict(list)
    for p in players:
        bands[round(p["y"] / 6)].append(p)
    for band_players in bands.values():
        n = len(band_players)
        if n > 1:
            band_players.sort(key=lambda q: q["x"])
            # even spread across the pitch width (8..72)
            lo, hi = 10, 70
            step = (hi - lo) / (n - 1)
            for i, q in enumerate(band_players):
                q["x"] = lo + step * i

    for p in players:
        x, y = p["x"], p["y"]  # x=width(0-80), y=length(0-120)
        pitch.scatter(y, x, s=560, c=_GOAL, edgecolors="white",
                      linewidths=1.0, alpha=0.95, ax=ax, zorder=4)
        # jersey number inside the dot
        pitch.annotate(str(p.get("jersey", "")), (y, x), ax=ax,
                       color=_BG, fontsize=8, fontweight="bold",
                       ha="center", va="center", zorder=5)
        # surname under the dot (truncated to avoid overlap)
        surname = p["name"].split()[-1] if p.get("name") else ""
        if len(surname) > 11:
            surname = surname[:10] + "."
        pitch.annotate(surname, (y - 6.5, x), ax=ax, color=_TEXT,
                       fontsize=7, ha="center", va="center", zorder=5)

    formation_str = formation.get("formation", "")
    ax.set_title(f"{title}" + (f"   ({formation_str})" if formation_str else ""),
                 color=_TEXT, fontsize=12, pad=8)

    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=150, facecolor=_BG, bbox_inches="tight")
    plt.close(fig)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Goal timing distribution (works with or without coordinates)
# ---------------------------------------------------------------------------

_INTERVALS = [(0, 15), (16, 30), (31, 45), (46, 60), (61, 75), (76, 120)]
_LABELS = ["0-15", "16-30", "31-45", "46-60", "61-75", "76+"]


def build_timing_chart(goals_for: list[int], goals_against: list[int], title: str) -> bytes | None:
    """Bar chart of goal minute distribution. Always available (no pitch)."""
    def bucket(minutes: list[int]) -> list[int]:
        out = [0] * len(_INTERVALS)
        for mn in minutes:
            for i, (lo, hi) in enumerate(_INTERVALS):
                if lo <= mn <= hi:
                    out[i] += 1
                    break
        return out

    gf = bucket(goals_for)
    ga = bucket(goals_against)
    if sum(gf) + sum(ga) == 0:
        return None

    fig, ax = plt.subplots(figsize=(7, 3.4))
    fig.set_facecolor(_BG)
    ax.set_facecolor(_BG)

    x = range(len(_LABELS))
    w = 0.4
    ax.bar([i - w / 2 for i in x], gf, w, label="Scored", color=_GOAL, alpha=0.9)
    ax.bar([i + w / 2 for i in x], ga, w, label="Conceded", color="#ef4444", alpha=0.9)

    ax.set_xticks(list(x))
    ax.set_xticklabels(_LABELS, color=_TEXT, fontsize=9)
    ax.set_ylabel("Goals", color=_TEXT, fontsize=9)
    ax.set_title(title, color=_TEXT, fontsize=11, pad=6)
    ax.tick_params(colors=_TEXT)
    for spine in ax.spines.values():
        spine.set_color(_LINE)
    ax.legend(facecolor=_BG, edgecolor=_LINE, labelcolor=_TEXT, fontsize=8)
    ax.yaxis.set_major_locator(plt.MaxNLocator(integer=True))

    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=150, facecolor=_BG, bbox_inches="tight")
    plt.close(fig)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Zone fallback chart (when there are no coordinates at all)
# ---------------------------------------------------------------------------

def build_zone_chart(shots: list[dict], title: str) -> bytes | None:
    """Horizontal bar chart of shots by zone — graceful fallback when a future
    provider lacks coordinates. Not used by ESPN (which has coordinates)."""
    zones = ["six_yard", "box", "outside_box", "long_range"]
    labels = ["Six-yard", "Penalty box", "Outside box", "Long range"]
    counts = [sum(1 for s in shots if s.get("zone") == z) for z in zones]
    if sum(counts) == 0:
        return None

    fig, ax = plt.subplots(figsize=(7, 3))
    fig.set_facecolor(_BG)
    ax.set_facecolor(_BG)
    ax.barh(labels, counts, color=_SHOT, alpha=0.85)
    ax.set_title(title, color=_TEXT, fontsize=11)
    ax.tick_params(colors=_TEXT)
    for spine in ax.spines.values():
        spine.set_color(_LINE)
    ax.xaxis.set_major_locator(plt.MaxNLocator(integer=True))

    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=150, facecolor=_BG, bbox_inches="tight")
    plt.close(fig)
    return buf.getvalue()
