"""
Data provider abstraction for football analysis.

The ScoutReport consumes ONLY the DataProvider interface — never a concrete
source. Today the only working free source with shot-level coordinates is ESPN
(its match `commentary` carries fieldPositionX/Y for every shot). FotMob and
Sofascore have both locked their public APIs behind anti-bot tokens / Cloudflare.

When a premium key arrives (StatsBomb / Wyscout / Opta), implement a new
provider with the same contract and inject it — the report and PDF code stay
untouched. That is the whole point of this layer.

Contracts:
    resolve_team(name, competition)        -> canonical team name (str) or None
    get_team_matches(team, competition, n) -> list[match dict] (most recent finished)
    get_shot_events(matches, team)         -> list[ShotEvent]
    get_goal_events(matches, team)         -> list[GoalEvent]
    get_lineups(matches, team)             -> list[(player, starts)] most frequent XI

Each ShotEvent is a plain dict so it survives JSON round-trips:
    {
        "x": float (0-100, distance toward attacking goal),
        "y": float (0-100, width),
        "result": "goal" | "on_target" | "off_target" | "blocked" | "woodwork",
        "xg": float | None,          # None until a premium provider supplies it
        "body_part": "right_foot" | "left_foot" | "head" | "other",
        "zone": "six_yard" | "box" | "outside_box" | "long_range",
        "team": str,
        "player": str,
        "minute": str,
        "is_for": bool,              # True = taken by scouted team, False = conceded
    }
"""
from __future__ import annotations

import re
from abc import ABC, abstractmethod
from collections import Counter


# ---------------------------------------------------------------------------
# Text parsing helpers (ESPN commentary is natural language)
# ---------------------------------------------------------------------------

def _body_part(text: str) -> str:
    t = text.lower()
    if "header" in t or "head" in t:
        return "head"
    if "left foot" in t or "left-foot" in t:
        return "left_foot"
    if "right foot" in t or "right-foot" in t:
        return "right_foot"
    return "other"


def _zone_from_text(text: str, x: float | None) -> str:
    t = text.lower()
    if "very close range" in t or "six yard" in t or "close range" in t:
        return "six_yard"
    if "outside the box" in t or "outside the area" in t or "long range" in t:
        # distinguish long range by x if available
        if x is not None and x < 65:
            return "long_range"
        return "outside_box"
    if "the box" in t or "the area" in t or "penalty" in t:
        return "box"
    # Fall back to coordinate if no words
    if x is not None:
        if x >= 94:
            return "six_yard"
        if x >= 83:
            return "box"
        if x >= 70:
            return "outside_box"
        return "long_range"
    return "box"


def _assist_type(text: str) -> str:
    """Classify how a goal was created from the commentary text."""
    t = text.lower()
    if "penalty" in t:
        return "penalty"
    if "free kick" in t and "assisted" not in t:
        return "free_kick"
    if "following a corner" in t or "from a corner" in t or "corner" in t:
        return "corner"
    if "with a cross" in t or "following a cross" in t or "cross" in t:
        return "cross"
    if "through ball" in t or "through-ball" in t:
        return "through_ball"
    if "set piece" in t or "set-piece" in t:
        return "set_piece"
    if "assisted by" in t:
        return "open_play_pass"
    return "unassisted"


_SHOT_TYPE_MAP = {
    "shot-on-target": "on_target",
    "shot-off-target": "off_target",
    "shot-blocked": "blocked",
    "shot-hit-woodwork": "woodwork",
}


# ---------------------------------------------------------------------------
# Abstract interface
# ---------------------------------------------------------------------------

class DataProvider(ABC):
    name: str = "abstract"
    has_xg: bool = False
    has_coordinates: bool = False

    @abstractmethod
    def resolve_team(self, name: str, competition: str) -> str | None: ...

    @abstractmethod
    def get_team_matches(self, team: str, competition: str, last_n: int = 5) -> list[dict]: ...

    @abstractmethod
    def get_shot_events(self, matches: list[dict], team: str) -> list[dict]: ...

    @abstractmethod
    def get_goal_events(self, matches: list[dict], team: str) -> list[dict]: ...

    @abstractmethod
    def get_lineups(self, matches: list[dict], team: str) -> list[tuple[str, int]]: ...


# ---------------------------------------------------------------------------
# ESPN provider — the only working free source with shot coordinates
# ---------------------------------------------------------------------------

class ESPNProvider(DataProvider):
    name = "ESPN"
    has_xg = False            # ESPN does not expose xG
    has_coordinates = True    # commentary carries fieldPositionX/Y per shot

    def resolve_team(self, name: str, competition: str) -> str | None:
        from Api.services.football_analysis import fetch_standings, _teams_match
        for row in fetch_standings(competition):
            if _teams_match(name, row["team"]):
                return row["team"]
        return None

    def get_team_matches(self, team: str, competition: str, last_n: int = 5) -> list[dict]:
        from Api.services.football_analysis import fetch_rich_schedule, _team_recent
        schedule = fetch_rich_schedule(competition)
        return _team_recent(team, schedule, n=last_n)

    def _summary(self, match: dict, competition: str) -> dict:
        from Api.services.football_analysis import _fetch_event_summary, _cached
        eid = match.get("event_id")
        if not eid:
            return {}
        return _cached(f"summary_raw_{eid}",
                       lambda: _fetch_event_summary(eid, competition))

    def get_shot_events(self, matches: list[dict], team: str) -> list[dict]:
        from Api.services.football_analysis import _teams_match
        competition = matches[0].get("_competition", "serie_a") if matches else "serie_a"

        shots: list[dict] = []
        for m in matches:
            summary = self._summary(m, m.get("_competition", competition))
            for c in summary.get("commentary", []):
                play = c.get("play", {})
                ptype = play.get("type", {}).get("type", "")
                if ptype not in _SHOT_TYPE_MAP:
                    continue
                x = play.get("fieldPositionX")
                y = play.get("fieldPositionY")
                shot_team = play.get("team", {}).get("displayName", "")
                player = (play.get("participants") or [{}])[0].get("athlete", {}).get("displayName", "")
                text = play.get("text", "")
                shots.append({
                    "x": float(x) if x is not None else None,
                    "y": float(y) if y is not None else None,
                    "result": _SHOT_TYPE_MAP.get(ptype, "off_target"),
                    "xg": None,
                    "body_part": _body_part(text),
                    "zone": _zone_from_text(text, x),
                    "team": shot_team,
                    "player": player,
                    "minute": play.get("clock", {}).get("displayValue", ""),
                    "is_for": _teams_match(team, shot_team),
                })

        # ESPN commentary does NOT include the goal-scoring shot — goals live
        # only in keyEvents (which carry their own coordinates). Append them so
        # the shot map and counts include goals.
        for g in self.get_goal_events(matches, team):
            shots.append({
                "x": float(g["x"]) if g.get("x") is not None else None,
                "y": float(g["y"]) if g.get("y") is not None else None,
                "result": "goal",
                "xg": None,
                "body_part": g.get("body_part", "other"),
                "zone": g.get("zone", "box"),
                "team": g.get("team", ""),
                "player": g.get("scorer", ""),
                "minute": g.get("minute", ""),
                "is_for": g.get("is_for", False),
            })
        return shots

    def get_goal_events(self, matches: list[dict], team: str) -> list[dict]:
        from Api.services.football_analysis import _teams_match
        goals: list[dict] = []
        for m in matches:
            summary = self._summary(m, m.get("_competition", "serie_a"))
            for ev in summary.get("keyEvents", []):
                if not ev.get("scoringPlay"):
                    continue
                text = ev.get("text", "")
                gteam = ev.get("team", {}).get("displayName", "")
                participants = ev.get("participants", [])
                scorer = participants[0].get("athlete", {}).get("displayName", "") if participants else ""
                assister = ""
                if len(participants) > 1:
                    assister = participants[1].get("athlete", {}).get("displayName", "")
                if not assister:
                    mt = re.search(r"assisted by ([^.]+?)(?: with| following|\.|$)", text, re.I)
                    if mt:
                        assister = mt.group(1).strip()
                clock = ev.get("clock", {}).get("displayValue", "")
                goals.append({
                    "scorer": scorer,
                    "assister": assister,
                    "assist_type": _assist_type(text),
                    "minute": clock,
                    "minute_num": _minute_to_int(clock),
                    "body_part": _body_part(text),
                    "team": gteam,
                    "is_for": _teams_match(team, gteam),
                    "x": ev.get("fieldPositionX"),
                    "y": ev.get("fieldPositionY"),
                    "zone": _zone_from_text(text, ev.get("fieldPositionX")),
                    "text": text,
                })
        return goals

    def get_lineups(self, matches: list[dict], team: str) -> list[tuple[str, int]]:
        from Api.services.football_analysis import _teams_match
        counter: Counter = Counter()
        for m in matches:
            summary = self._summary(m, m.get("_competition", "serie_a"))
            for roster in summary.get("rosters", []):
                rteam = roster.get("team", {}).get("displayName", "")
                if not _teams_match(team, rteam):
                    continue
                for entry in roster.get("roster", []):
                    if not entry.get("starter"):
                        continue
                    nm = entry.get("athlete", {}).get("displayName", "")
                    if nm:
                        counter[nm] += 1
        return counter.most_common(11)

    def get_formation(self, matches: list[dict], team: str) -> dict:
        """Most-recent-match starting XI with positions, for a formation pitch.
        Returns {formation, players:[{name, jersey, position, x, y}]} or {}."""
        from Api.services.football_analysis import _teams_match
        for m in reversed(matches):  # most recent first
            summary = self._summary(m, m.get("_competition", "serie_a"))
            for roster in summary.get("rosters", []):
                if not _teams_match(team, roster.get("team", {}).get("displayName", "")):
                    continue
                starters = [e for e in roster.get("roster", []) if e.get("starter")]
                if len(starters) < 11:
                    continue
                players = []
                for e in starters:
                    pos = (e.get("position") or {}).get("abbreviation", "")
                    x, y = _position_to_xy(pos)
                    players.append({
                        "name": e.get("athlete", {}).get("displayName", ""),
                        "jersey": e.get("jersey", ""),
                        "position": pos,
                        "x": x, "y": y,
                    })
                return {"formation": roster.get("formation", ""), "players": players}
        return {}


def _position_to_xy(abbr: str) -> tuple[float, float]:
    """Map an ESPN position abbreviation (e.g. 'CD-L', 'DM', 'RW', 'F') to a
    point on a vertical statsbomb pitch (x: 0-80 width, y: 0-120 length, own
    goal at y=0 / attack upward). Side suffix -L/-R shifts width."""
    a = abbr.upper().strip()
    base = a.split("-")[0]
    side = a.split("-")[1] if "-" in a else ""

    # length (y) by role band
    length_map = {
        "G": 8, "GK": 8,
        "CD": 26, "CB": 26, "LB": 28, "RB": 28, "WB": 32, "LWB": 32, "RWB": 32, "D": 26,
        "DM": 44, "CDM": 44,
        "CM": 60, "M": 60, "LM": 62, "RM": 62, "MF": 60,
        "AM": 78, "CAM": 78, "LAM": 80, "RAM": 80,
        "LW": 96, "RW": 96, "W": 96,
        "F": 104, "CF": 104, "ST": 104, "FW": 104, "SS": 92,
        "LF": 100, "RF": 100, "LS": 100, "RS": 100, "LCF": 100, "RCF": 100,
    }
    y = length_map.get(base, 60)

    # width (x): wide positions hug the touchline; a centre role with an -L/-R
    # suffix (or LCF/RCF-style prefix) sits just inside of centre.
    wide_left = base in ("LB", "LM", "LW", "LWB", "LF", "LAM")
    wide_right = base in ("RB", "RM", "RW", "RWB", "RF", "RAM")
    inner_left = side == "L" or base in ("LS", "LCF")
    inner_right = side == "R" or base in ("RS", "RCF")
    if wide_left:
        x = 14
    elif wide_right:
        x = 66
    elif inner_left:
        x = 32
    elif inner_right:
        x = 48
    else:
        x = 40
    return x, y


def _minute_to_int(clock: str) -> int:
    """'45'+2'' -> 47, '67'' -> 67."""
    if not clock:
        return 0
    base = re.search(r"(\d+)", clock)
    added = re.search(r"\+\s*(\d+)", clock)
    total = int(base.group(1)) if base else 0
    if added:
        total += int(added.group(1))
    return total


# ---------------------------------------------------------------------------
# Premium provider stubs — ready for when a key arrives
# ---------------------------------------------------------------------------

class StatsBombProvider(DataProvider):
    """Stub. Implement against StatsBomb API/open-data once a key is available.

    StatsBomb supplies true xG and exact shot coordinates, so set:
        has_xg = True
        has_coordinates = True
    and the heatmap/danger-score code will automatically use the richer data
    with zero changes elsewhere.
    """
    name = "StatsBomb"
    has_xg = True
    has_coordinates = True

    def __init__(self, *args, **kwargs):
        raise NotImplementedError("StatsBombProvider not yet implemented — awaiting API key")

    def resolve_team(self, name, competition): raise NotImplementedError
    def get_team_matches(self, team, competition, last_n=5): raise NotImplementedError
    def get_shot_events(self, matches, team): raise NotImplementedError
    def get_goal_events(self, matches, team): raise NotImplementedError
    def get_lineups(self, matches, team): raise NotImplementedError


# Active provider — swap this single line when a premium key arrives
def get_provider() -> DataProvider:
    return ESPNProvider()
