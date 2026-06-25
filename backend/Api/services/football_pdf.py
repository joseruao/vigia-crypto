from __future__ import annotations

import datetime
import os
from io import BytesIO

from fpdf import FPDF
from fpdf.enums import XPos, YPos

# ---------------------------------------------------------------------------
# Colours
# ---------------------------------------------------------------------------
_DARK     = (15,  23,  42)
_GREEN    = (4,  120,  87)
_GREEN_LT = (236, 253, 245)
_GRAY     = (100, 116, 139)
_GRAY_LT  = (241, 245, 249)
_WHITE    = (255, 255, 255)
_RED      = (185,  28,  28)
_AMBER    = (161, 100,   0)
_BLUE     = (30,   64, 175)
_PURPLE   = (109,  40, 217)

_PAGE_W = 210   # A4 mm
_MARGIN = 18
_INNER  = _PAGE_W - _MARGIN * 2
_COL    = _INNER / 2 - 2

# ---------------------------------------------------------------------------
# Font discovery
# ---------------------------------------------------------------------------
# matplotlib bundles the DejaVu TTF family (it is a hard dependency now for the
# shot maps), so we use those — guaranteed present on any platform, no system
# packages and no network download required. System paths are kept as a cheap
# first check in case a faster local copy exists.
_DEJAVU_NAMES = {
    "regular": "DejaVuSans.ttf",
    "bold":    "DejaVuSans-Bold.ttf",
    "italic":  "DejaVuSans-Oblique.ttf",
}

_FONT_PATHS = {
    "regular": [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "C:/Windows/Fonts/arial.ttf",
    ],
    "bold": [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "C:/Windows/Fonts/arialbd.ttf",
    ],
    "italic": [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Oblique.ttf",
        "C:/Windows/Fonts/ariali.ttf",
    ],
}


def _matplotlib_font(key: str) -> str | None:
    try:
        import matplotlib
        path = os.path.join(matplotlib.get_data_path(), "fonts", "ttf", _DEJAVU_NAMES[key])
        return path if os.path.exists(path) else None
    except Exception:
        return None


def _find_font(key: str) -> str:
    # Prefer matplotlib's bundled DejaVu — it has the full glyph set we use
    # (✓, em dash, accents) and is identical on every platform, so PDFs render
    # the same locally and on Railway. System fonts (e.g. Windows Arial) are a
    # fallback only and may miss glyphs like U+2713.
    mpl = _matplotlib_font(key)
    if mpl:
        return mpl
    for path in _FONT_PATHS[key]:
        if os.path.exists(path):
            return path
    raise FileNotFoundError(f"No DejaVu/Arial font found for '{key}'")


# ---------------------------------------------------------------------------
# Base PDF
# ---------------------------------------------------------------------------

class _ScoutPDF(FPDF):
    _competition: str = ""

    def _setup_fonts(self) -> None:
        self.add_font("U", "", _find_font("regular"))
        self.add_font("U", "B", _find_font("bold"))
        self.add_font("U", "I", _find_font("italic"))

    def header(self) -> None:
        self.set_fill_color(*_DARK)
        self.rect(0, 0, _PAGE_W, 11, "F")
        self.set_font("U", "B", 7.5)
        self.set_text_color(*_WHITE)
        self.set_xy(_MARGIN, 3)
        self.cell(0, 5, f"FOOTBALL AI LAB  |  {self._competition}",
                  new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_text_color(0, 0, 0)
        self.set_xy(_MARGIN, 13)

    def footer(self) -> None:
        self.set_y(-13)
        self.set_font("U", "I", 7)
        self.set_text_color(*_GRAY)
        date_str = datetime.date.today().isoformat()
        self.cell(0, 5, f"Football AI Lab  |  {date_str}  |  Page {self.page_no()}", align="C")

    # --- Helpers ---

    def _section_bar(self, title: str, color: tuple = _GREEN) -> None:
        self.set_fill_color(*color)
        self.set_text_color(*_WHITE)
        self.set_font("U", "B", 8.5)
        self.set_x(_MARGIN)
        self.cell(_INNER, 7, f"  {title.upper()}", fill=True,
                  new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_text_color(0, 0, 0)
        self.ln(2)

    def _body(self, text: str, indent: float = 0) -> None:
        self.set_font("U", "", 9)
        self.set_text_color(*_DARK)
        self.set_x(_MARGIN + indent)
        self.multi_cell(_INNER - indent, 5.5, text,
                        new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.ln(1)

    def _bullets(self, items: list[str], indent: float = 3) -> None:
        if not items:
            self._body("—", indent)
            return
        self.set_font("U", "", 8.5)
        self.set_text_color(*_DARK)
        for item in items:
            x = _MARGIN + indent
            y = self.get_y()
            self.set_fill_color(*_GREEN)
            # small filled circle approximated with a short dash
            self.set_x(x)
            self.set_font("U", "B", 10)
            self.set_text_color(*_GREEN)
            self.cell(5, 5.5, "-", new_x=XPos.RIGHT, new_y=YPos.TOP)
            self.set_font("U", "", 8.5)
            self.set_text_color(*_DARK)
            self.multi_cell(_INNER - indent - 5, 5.5, item,
                            new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.ln(1)

    def _two_col(
        self,
        lt: str, li: list[str],
        rt: str, ri: list[str],
        lc: tuple = _GREEN, rc: tuple = _RED,
    ) -> None:
        y0 = self.get_y()

        # Left header
        self.set_xy(_MARGIN, y0)
        self.set_fill_color(*lc)
        self.set_text_color(*_WHITE)
        self.set_font("U", "B", 8)
        self.cell(_COL, 6, f"  {lt.upper()}", fill=True,
                  new_x=XPos.RIGHT, new_y=YPos.TOP)

        # Right header
        self.set_xy(_MARGIN + _COL + 4, y0)
        self.set_fill_color(*rc)
        self.cell(_COL, 6, f"  {rt.upper()}", fill=True,
                  new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.ln(2)

        y1 = self.get_y()

        # Left items
        self.set_xy(_MARGIN, y1)
        self._col_items(li, _MARGIN, _COL)
        y_left = self.get_y()

        # Right items
        self.set_xy(_MARGIN + _COL + 4, y1)
        self._col_items(ri, _MARGIN + _COL + 4, _COL)
        y_right = self.get_y()

        self.set_y(max(y_left, y_right) + 2)

    def _col_items(self, items: list[str], x: float, w: float) -> None:
        if not items:
            self.set_x(x + 2)
            self.set_font("U", "I", 8)
            self.cell(w, 5, "—", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            return
        self.set_font("U", "", 8.3)
        self.set_text_color(*_DARK)
        for item in items:
            self.set_x(x + 2)
            self.set_font("U", "B", 9)
            self.set_text_color(*_GREEN)
            self.cell(5, 5.2, "-", new_x=XPos.RIGHT, new_y=YPos.TOP)
            self.set_font("U", "", 8.3)
            self.set_text_color(*_DARK)
            self.multi_cell(w - 5, 5.2, item, new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    def _stat_row(self, label: str, value: str) -> None:
        self.set_x(_MARGIN)
        self.set_font("U", "B", 8)
        self.set_text_color(*_GRAY)
        self.cell(40, 5, label, new_x=XPos.RIGHT, new_y=YPos.TOP)
        self.set_font("U", "", 8.5)
        self.set_text_color(*_DARK)
        self.multi_cell(_INNER - 40, 5, value, new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    def _cover_box(self, badge: str, title: str, source: str) -> None:
        y = self.get_y()
        self.set_fill_color(*_DARK)
        self.rect(_MARGIN, y, _INNER, 30, "F")
        self.set_xy(_MARGIN + 4, y + 3)
        self.set_font("U", "B", 7)
        self.set_text_color(100, 220, 170)
        self.cell(0, 5, badge.upper(), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_x(_MARGIN + 4)
        self.set_font("U", "B", 16)
        self.set_text_color(*_WHITE)
        self.multi_cell(_INNER - 8, 9, title, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_x(_MARGIN + 4)
        self.set_font("U", "", 7.5)
        self.set_text_color(160, 190, 220)
        self.cell(0, 5, source, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_text_color(0, 0, 0)
        self.ln(4)

    def _data_footer(self, source: str) -> None:
        self.ln(3)
        self.set_fill_color(*_GRAY_LT)
        self.set_x(_MARGIN)
        self.set_font("U", "I", 7.5)
        self.set_text_color(*_GRAY)
        self.multi_cell(_INNER, 5,
                        f"Data source: {source}  |  Football AI Lab - joseruao.com",
                        fill=True, new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    def _image(self, png: bytes, w: float, x: float | None = None) -> None:
        """Embed a PNG (bytes) at width w mm, centred unless x given."""
        if not png:
            return
        if x is None:
            x = (_PAGE_W - w) / 2
        self.image(BytesIO(png), x=x, w=w)

    def _danger_table(self, players: list[dict], labels: dict) -> None:
        if not players:
            return
        self.set_x(_MARGIN)
        self.set_font("U", "B", 8); self.set_text_color(*_GRAY)
        cols = [(70, labels["player"]), (22, "G"), (22, "A"),
                (38, labels["on_target"]), (28, labels["danger"])]
        for w, h in cols:
            self.cell(w, 6, h, new_x=XPos.RIGHT, new_y=YPos.TOP)
        self.ln(6)
        for i, p in enumerate(players):
            self.set_x(_MARGIN)
            self.set_fill_color(*( _GREEN_LT if i == 0 else _WHITE))
            self.set_font("U", "B" if i == 0 else "", 9)
            self.set_text_color(*_DARK)
            self.cell(70, 6, f"{i+1}. {p.get('player','')}", fill=True, new_x=XPos.RIGHT, new_y=YPos.TOP)
            self.cell(22, 6, str(p.get("goals", 0)), fill=True, new_x=XPos.RIGHT, new_y=YPos.TOP)
            self.cell(22, 6, str(p.get("assists", 0)), fill=True, new_x=XPos.RIGHT, new_y=YPos.TOP)
            self.cell(38, 6, f"{p.get('on_target',0)}/{p.get('shots',0)}", fill=True, new_x=XPos.RIGHT, new_y=YPos.TOP)
            self.set_text_color(*_GREEN); self.set_font("U", "B", 9)
            self.cell(28, 6, str(p.get("score", 0)), fill=True, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            self.set_text_color(*_DARK)
        self.ln(2)

    def _data_confidence_box(self, dq: dict, L: dict) -> None:
        """Provenance + confidence strip at the top of page 1 (Codex #1 / #5)."""
        if not dq:
            return
        conf = dq.get("confidence", "low")
        bar = {"high": _GREEN, "medium": _AMBER, "low": _RED}.get(conf, _GRAY)
        y0 = self.get_y()
        self.set_fill_color(*bar)
        self.rect(_MARGIN, y0, 2, 9, "F")
        self.set_fill_color(*_GRAY_LT)
        self.set_xy(_MARGIN + 2, y0)
        self.set_font("U", "B", 8); self.set_text_color(*_DARK)
        head = (f"   {L['data_confidence'].upper()}: {dq.get('confidence_label', conf)}   |   "
                f"{dq.get('matches_analysed', 0)} {L['dq_matches']}   |   "
                f"{dq.get('shots_with_coordinates', 0)} {L['dq_shots']}   |   "
                f"xG: {'-' if dq.get('xg_source') == 'none' else dq.get('xg_source')}")
        self.cell(_INNER - 2, 9, head, fill=True, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        warns = dq.get("warnings", [])
        if warns:
            self.set_x(_MARGIN)
            self.set_font("U", "I", 7); self.set_text_color(*_GRAY)
            self.multi_cell(_INNER, 4.5, "   • " + "   • ".join(warns),
                            new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_text_color(0, 0, 0)
        self.ln(2)

    def _rank_cards(self, ranks: list[dict]) -> None:
        """Three competition-rank cards in a row (green=strength, red=weakness)."""
        if not ranks:
            return
        n = min(len(ranks), 3)
        gap = 4.0
        w = (_INNER - gap * (n - 1)) / n
        h = 24.0
        y0 = self.get_y()
        for i, r in enumerate(ranks[:n]):
            x = _MARGIN + i * (w + gap)
            if r.get("good"):
                fill, txt, border = _GREEN_LT, _GREEN, _GREEN
            elif r.get("bad"):
                fill, txt, border = (254, 242, 242), _RED, _RED
            else:
                fill, txt, border = _GRAY_LT, _DARK, _GRAY
            self.set_fill_color(*fill)
            self.set_draw_color(*border)
            self.set_line_width(0.3)
            self.rect(x, y0, w, h, "DF")
            self.set_xy(x, y0 + 2.5)
            self.set_font("U", "B", 16); self.set_text_color(*txt)
            self.cell(w, 7, f"#{r.get('rank','')}", align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            self.set_x(x)
            self.set_font("U", "", 6.5); self.set_text_color(*_GRAY)
            self.cell(w, 3.5, f"/ {r.get('total','')}", align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            self.set_x(x)
            self.set_font("U", "B", 8); self.set_text_color(*_DARK)
            self.cell(w, 4.5, str(r.get("label", "")), align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            self.set_x(x)
            self.set_font("U", "", 7); self.set_text_color(*_GRAY)
            self.cell(w, 4, f"{r.get('value','')}/game", align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_y(y0 + h + 3)
        self.set_text_color(0, 0, 0)

    def _priority_box(self, title: str, alerts: list[str]) -> None:
        """Compact red-flag box for the top of page 1 — a 10-second read."""
        if not alerts:
            return
        self.set_x(_MARGIN)
        self.set_fill_color(*_RED)
        self.set_text_color(*_WHITE)
        self.set_font("U", "B", 8.5)
        self.cell(_INNER, 6.5, f"  {title.upper()}", fill=True,
                  new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_fill_color(254, 242, 242)
        for a in alerts[:4]:
            self.set_x(_MARGIN)
            self.set_font("U", "B", 9); self.set_text_color(185, 28, 28)
            self.multi_cell(_INNER, 6.5, f"   •  {a}", fill=True,
                            new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_text_color(0, 0, 0)
        self.ln(3)


# ---------------------------------------------------------------------------
# Match Prep PDF (3 pages)
# ---------------------------------------------------------------------------

def build_match_prep_pdf(report: dict, lang: str = "en") -> bytes:
    L = _labels(lang)
    pdf = _ScoutPDF(orientation="P", unit="mm", format="A4")
    pdf._competition = ("FIFA World Cup 2026"
                        if "world cup" in report.get("data_source", "").lower()
                        else "Campeonato Brasileiro Serie A")
    pdf._setup_fonts()
    pdf.set_margins(_MARGIN, 14, _MARGIN)
    pdf.set_auto_page_break(auto=True, margin=18)

    my_team  = report.get("my_team", "")
    opp_team = report.get("opponent_team", "")
    source   = report.get("data_source", "")

    # ----- PAGE 1: Cover + Priority Alerts + Context -----
    pdf.add_page()
    pdf._cover_box(L["match_prep"], f"{my_team}  vs  {opp_team}", source)

    pdf._data_confidence_box(report.get("data_quality", {}), L)

    # Priority alerts: matchup edges first, then opponent danger + alerts
    prio = list(report.get("matchup_insights", []))
    danger0 = (report.get("opponent_danger_players") or [{}])[0]
    if danger0.get("player"):
        prio.append(f"{L['main_danger']}: {danger0['player']} ({opp_team})")
    prio.extend(report.get("opponent_alerts", []))
    pdf._priority_box(L["priority_alerts"], prio)

    pdf._section_bar(L["exec_summary"])
    pdf._body(report.get("executive_summary", "-"))
    pdf.ln(3)

    # Parse raw stats
    raw_lines = [l.strip() for l in report.get("raw_stats_used", "").split("\n") if l.strip()]
    my_line  = next((l for l in raw_lines if l.startswith("MY TEAM")), "")
    opp_line = next((l for l in raw_lines if l.startswith("OPPONENT")), "")

    if my_line or opp_line:
        pdf._section_bar(L["season_stats"], color=_DARK)
        if my_line:
            pdf._stat_row(L["my_team"] + ":", my_line)
        if opp_line:
            pdf._stat_row(L["opponent"] + ":", opp_line)
        pdf.ln(3)

    # Parse recent matches from raw block
    my_matches: list[str] = []
    opp_matches: list[str] = []
    h2h_matches: list[str] = []
    section = ""
    for line in raw_lines:
        if "MY TEAM" in line and "MATCHES" in line:
            section = "my"
        elif "OPPONENT" in line and "MATCHES" in line:
            section = "opp"
        elif "HEAD-TO-HEAD" in line:
            section = "h2h"
        elif line.startswith("202") or line == "no data":
            {"my": my_matches, "opp": opp_matches, "h2h": h2h_matches}.get(section, []).append(line)

    pdf._section_bar(L["recent_form"], color=_BLUE)
    pdf.set_font("U", "B", 8); pdf.set_text_color(*_GRAY)
    pdf.set_x(_MARGIN); pdf.cell(0, 5, L["my_team"].upper(), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_text_color(0, 0, 0)
    pdf._bullets(my_matches[:6] or ["-"])

    pdf.set_font("U", "B", 8); pdf.set_text_color(*_GRAY)
    pdf.set_x(_MARGIN); pdf.cell(0, 5, L["opponent"].upper(), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_text_color(0, 0, 0)
    pdf._bullets(opp_matches[:6] or ["-"])

    if h2h_matches:
        pdf.set_font("U", "B", 8); pdf.set_text_color(*_GRAY)
        pdf.set_x(_MARGIN); pdf.cell(0, 5, "HEAD TO HEAD", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_text_color(0, 0, 0)
        pdf._bullets(h2h_matches)

    # ----- PAGE 2: Opponent Analysis -----
    pdf.add_page()
    pdf.set_font("U", "B", 13); pdf.set_text_color(*_DARK)
    pdf.set_x(_MARGIN)
    pdf.cell(0, 8, f"{L['opp_analysis']}: {opp_team}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_draw_color(*_GREEN); pdf.set_line_width(0.5)
    pdf.line(_MARGIN, pdf.get_y(), _PAGE_W - _MARGIN, pdf.get_y())
    pdf.ln(4)

    # Opponent competition rankings
    opp_ranks = report.get("opponent_ranks", [])
    if opp_ranks:
        pdf._section_bar(L["competition_context"], color=_DARK)
        pdf._rank_cards(opp_ranks)
        pdf.ln(1)

    # Head-to-head comparison chart (per-game, both teams)
    comp_uri = report.get("images", {}).get("comparison")
    if comp_uri and "," in comp_uri:
        import base64 as _b64c
        try:
            comp_png = _b64c.b64decode(comp_uri.split(",", 1)[1])
            pdf._section_bar(L["head_to_head"], color=_DARK)
            pdf._image(comp_png, w=150)
            pdf.ln(3)
        except Exception:
            pass

    pdf._two_col(L["strengths"], report.get("opponent_strengths", []),
                 L["weaknesses"], report.get("opponent_weaknesses", []))
    pdf.ln(3)

    pdf._section_bar(L["key_threats"])
    pdf._bullets(report.get("key_threats", []))
    pdf.ln(2)

    pdf._section_bar(L["tactical_approach"], color=_BLUE)
    pdf._body(report.get("tactical_approach", "-"))

    # Opponent danger players
    opp_danger = report.get("opponent_danger_players", [])
    if opp_danger:
        pdf.ln(2)
        pdf._section_bar(L["danger_players"], color=_RED)
        pdf._danger_table(opp_danger, L)

    # Opponent goal log (scorers + minutes)
    opp_glog = report.get("opponent_goals_log", [])
    if opp_glog:
        pdf.ln(1)
        pdf._section_bar(L["goal_log"], color=_DARK)
        pdf.set_font("U", "", 8.5); pdf.set_text_color(*_DARK)
        pdf.set_x(_MARGIN)
        pdf.multi_cell(_INNER, 5.5, "  ·  ".join(opp_glog), new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    # ----- PAGE: Opponent shot maps -----
    imgs = report.get("images", {})
    if imgs.get("shotmap_for") or imgs.get("shotmap_against"):
        pdf.add_page()
        pdf.set_font("U", "B", 13); pdf.set_text_color(*_DARK)
        pdf.set_x(_MARGIN)
        pdf.cell(0, 8, f"{L['shot_analysis']}: {opp_team}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_draw_color(*_GREEN); pdf.set_line_width(0.5)
        pdf.line(_MARGIN, pdf.get_y(), _PAGE_W - _MARGIN, pdf.get_y())
        pdf.ln(3)
        import base64 as _b64mod
        def _decode(uri):
            if not uri: return None
            return _b64mod.b64decode(uri.split(",", 1)[1]) if "," in uri else None
        sf = _decode(imgs.get("shotmap_for"))
        sa = _decode(imgs.get("shotmap_against"))
        if sf:
            pdf._image(sf, w=110); pdf.ln(1)
        if sa:
            pdf._image(sa, w=110)

    # ----- PAGE 3: Game Plan -----
    pdf.add_page()
    pdf.set_font("U", "B", 13); pdf.set_text_color(*_DARK)
    pdf.set_x(_MARGIN)
    pdf.cell(0, 8, L["game_plan"], new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_draw_color(*_GREEN); pdf.set_line_width(0.5)
    pdf.line(_MARGIN, pdf.get_y(), _PAGE_W - _MARGIN, pdf.get_y())
    pdf.ln(4)

    pdf._two_col(L["pressing_triggers"], report.get("pressing_triggers", []),
                 L["attacking_approach"], report.get("attacking_approach", []),
                 lc=_GREEN, rc=_BLUE)
    pdf.ln(3)

    pdf._section_bar(L["set_pieces"], color=_AMBER)
    pdf._bullets(report.get("set_piece_plan", []))
    pdf.ln(2)

    pdf._section_bar(L["risk"], color=_RED)
    pdf._body(report.get("risk_assessment", "-"))

    subs = report.get("substitution_notes", [])
    if subs:
        pdf.ln(2)
        pdf._section_bar(L["sub_notes"], color=_PURPLE)
        pdf._bullets(subs)

    # ----- FINAL PAGE: Matchup edges + Key Alerts -----
    matchups = report.get("matchup_insights", [])
    opp_alerts = report.get("opponent_alerts", [])
    my_alerts = report.get("my_team_alerts", [])
    if matchups or opp_alerts or my_alerts:
        pdf.add_page()
        pdf.set_font("U", "B", 13); pdf.set_text_color(*_DARK)
        pdf.set_x(_MARGIN)
        pdf.cell(0, 8, L["key_alerts"], new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_draw_color(*_RED); pdf.set_line_width(0.5)
        pdf.line(_MARGIN, pdf.get_y(), _PAGE_W - _MARGIN, pdf.get_y())
        pdf.ln(3)

        def _alert_rows(items, color):
            for a in items:
                y = pdf.get_y()
                pdf.set_fill_color(*color)
                pdf.rect(_MARGIN, y, 2, 11, "F")
                pdf.set_fill_color(254, 242, 242)
                pdf.set_xy(_MARGIN + 2, y)
                pdf.set_font("U", "B", 9.5); pdf.set_text_color(150, 30, 30)
                pdf.multi_cell(_INNER - 2, 11, f"   {a}", fill=True,
                               new_x=XPos.LMARGIN, new_y=YPos.NEXT)
                pdf.ln(1.5)

        if matchups:
            pdf._section_bar(L["matchup_edges"], color=_RED)
            _alert_rows(matchups, _RED)
            pdf.ln(1)
        if opp_alerts:
            pdf._section_bar(f"{opp_team} — {L['key_alerts']}", color=_AMBER)
            _alert_rows(opp_alerts, _AMBER)
            pdf.ln(1)
        if my_alerts:
            pdf._section_bar(f"{my_team} — {L['key_alerts']}", color=_BLUE)
            _alert_rows(my_alerts, _BLUE)

    pdf._data_footer(source)

    buf = BytesIO()
    pdf.output(buf)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Opponent Scout PDF (3 pages)
# ---------------------------------------------------------------------------

def build_scout_pdf(report: dict, lang: str = "en") -> bytes:
    L = _labels(lang)
    pdf = _ScoutPDF(orientation="P", unit="mm", format="A4")
    pdf._competition = ("FIFA World Cup 2026"
                        if "world cup" in report.get("data_source", "").lower()
                        else "Campeonato Brasileiro Serie A")
    pdf._setup_fonts()
    pdf.set_margins(_MARGIN, 14, _MARGIN)
    pdf.set_auto_page_break(auto=True, margin=18)

    team   = report.get("team", "")
    source = report.get("data_source", "")
    viz    = report.get("viz_payload", {}) or {}

    # Pre-render charts (graceful: returns None if mplsoccer missing / no data)
    shotmap_for = shotmap_against = timing_png = formation_png = None
    try:
        from Api.services import football_viz as fv
        if fv.viz_available():
            if viz.get("shots"):
                shots = viz["shots"]
                has_xg = bool(viz.get("has_xg"))
                shots_for = [s for s in shots if s.get("is_for")]
                shots_against = [s for s in shots if not s.get("is_for")]
                shotmap_for = fv.build_shot_map(shots_for, f"{team} — {L['shots_taken']}", has_xg)
                shotmap_against = fv.build_shot_map(shots_against, f"{team} — {L['shots_conceded']}", has_xg)
                timing_png = fv.build_timing_chart(
                    viz.get("goal_minutes_for", []), viz.get("goal_minutes_against", []),
                    f"{team} — {L['goal_timing']}",
                )
            if viz.get("formation", {}).get("players"):
                formation_png = fv.build_formation_pitch(
                    viz["formation"], f"{team} — {L['probable_lineup']}")
    except Exception:
        pass  # charts are optional — text report still renders

    # ----- PAGE 1: Cover + Priority Alerts + Overview -----
    pdf.add_page()
    pdf._cover_box(L["scout_report"], team, source)

    pdf._data_confidence_box(report.get("data_quality", {}), L)

    # Priority alerts: main danger player + top key alerts (10-second read)
    prio = []
    danger0 = (report.get("top_danger_players") or [{}])[0]
    if danger0.get("player"):
        prio.append(f"{L['main_danger']}: {danger0['player']}")
    prio.extend(report.get("key_alerts", []))
    pdf._priority_box(L["priority_alerts"], prio)

    pdf._section_bar(L["exec_summary"])
    pdf._body(report.get("executive_summary", "-"))
    pdf.ln(1)

    pdf._section_bar(L["form_analysis"], color=_BLUE)
    pdf._body(report.get("form_analysis", "-"))
    pdf.ln(1)

    pdf._section_bar(L["playing_style"], color=_PURPLE)
    pdf._body(report.get("playing_style", "-"))
    pdf.ln(1)

    ranks = report.get("competition_ranks", [])
    if ranks:
        pdf._section_bar(L["competition_context"], color=_DARK)
        pdf._rank_cards(ranks)
        pdf.ln(1)

    lineup = report.get("probable_lineup", [])
    if lineup and not formation_png:
        # Text fallback only when we couldn't draw the formation pitch
        pdf._section_bar(L["probable_lineup"], color=_DARK)
        pdf.set_font("U", "", 8.5); pdf.set_text_color(*_DARK)
        pdf.set_x(_MARGIN)
        pdf.multi_cell(_INNER, 5.5, "  •  ".join(lineup),
                       new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.ln(1)

    # ----- PAGE: Formation pitch -----
    if formation_png:
        pdf.add_page()
        pdf.set_font("U", "B", 13); pdf.set_text_color(*_DARK)
        pdf.set_x(_MARGIN)
        pdf.cell(0, 8, f"{L['probable_lineup']}: {team}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_draw_color(*_GREEN); pdf.set_line_width(0.5)
        pdf.line(_MARGIN, pdf.get_y(), _PAGE_W - _MARGIN, pdf.get_y())
        pdf.ln(3)
        pdf._image(formation_png, w=120)

    # ----- PAGE: Tactical Evolution -----
    tact_evo = report.get("tactical_evolution", {}) or {}
    evo_matches = tact_evo.get("matches", [])
    if evo_matches:
        pdf.add_page()
        pdf.set_font("U", "B", 13); pdf.set_text_color(*_DARK)
        pdf.set_x(_MARGIN)
        tact_evo_title = "Evolucao Tactica" if lang == "pt" else "Tactical Evolution"
        pdf.cell(0, 8, f"{tact_evo_title}: {team}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_draw_color(*_BLUE); pdf.set_line_width(0.5)
        pdf.line(_MARGIN, pdf.get_y(), _PAGE_W - _MARGIN, pdf.get_y())
        pdf.ln(3)

        # Summary chips
        for line in tact_evo.get("summary", []):
            pdf.set_x(_MARGIN)
            pdf.set_fill_color(*_GRAY_LT)
            pdf.set_font("U", "", 8.5); pdf.set_text_color(*_DARK)
            pdf.cell(_INNER, 5.5, f"  {line}", fill=True, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.ln(0.5)
        pdf.ln(3)

        # Per-match rows: Date | vs Opponent | W/D/L Score | Formation | Changes
        _R_COLORS = {"W": _GREEN, "D": _AMBER, "L": _RED}
        col_date = 22; col_opp = 52; col_res = 22; col_form = 24; col_changes = _INNER - col_date - col_opp - col_res - col_form

        # Header
        pdf.set_x(_MARGIN)
        pdf.set_font("U", "B", 7.5); pdf.set_text_color(*_GRAY)
        for w, h in [(col_date, "DATE"), (col_opp, "OPPONENT"), (col_res, "RESULT"),
                     (col_form, L["formation"]), (col_changes, "CHANGES")]:
            pdf.cell(w, 6, h, new_x=XPos.RIGHT, new_y=YPos.TOP)
        pdf.ln(6)
        pdf.set_draw_color(*_GRAY_LT); pdf.set_line_width(0.3)
        pdf.line(_MARGIN, pdf.get_y(), _PAGE_W - _MARGIN, pdf.get_y())
        pdf.ln(1)

        for m in evo_matches:
            rc = _R_COLORS.get(m.get("result", ""), _GRAY)
            changes = m.get("changes_from_prev", [])
            change_txt = " / ".join(changes[:3]) if changes else "—"
            has_form_change = any(c.startswith("Formation:") for c in changes)

            if has_form_change:
                pdf.set_fill_color(255, 251, 235)  # amber-50
            else:
                pdf.set_fill_color(*_WHITE)

            y0 = pdf.get_y()
            pdf.set_x(_MARGIN)
            pdf.set_font("U", "", 7.5); pdf.set_text_color(*_GRAY)
            pdf.cell(col_date, 6, m.get("date", ""), fill=True, new_x=XPos.RIGHT, new_y=YPos.TOP)
            pdf.set_text_color(*_DARK)
            pdf.cell(col_opp, 6, m.get("opponent", ""), fill=True, new_x=XPos.RIGHT, new_y=YPos.TOP)
            pdf.set_font("U", "B", 7.5); pdf.set_text_color(*rc)
            pdf.cell(col_res, 6, f"{m.get('result','')} {m.get('score','')}", fill=True, new_x=XPos.RIGHT, new_y=YPos.TOP)
            pdf.set_text_color(*_WHITE); pdf.set_fill_color(*_DARK)
            pdf.cell(col_form, 6, m.get("formation_name", ""), fill=True, align="C", new_x=XPos.RIGHT, new_y=YPos.TOP)
            pdf.set_fill_color(255, 251, 235) if has_form_change else pdf.set_fill_color(*_GRAY_LT)
            pdf.set_font("U", "", 7); pdf.set_text_color(*_DARK)
            pdf.multi_cell(col_changes, 6, change_txt, fill=True, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.ln(0.5)

    # ----- PAGE 2: Shot Maps (attack + defence) -----
    if shotmap_for or shotmap_against:
        pdf.add_page()
        pdf.set_font("U", "B", 13); pdf.set_text_color(*_DARK)
        pdf.set_x(_MARGIN)
        pdf.cell(0, 8, f"{L['shot_analysis']}: {team}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_draw_color(*_GREEN); pdf.set_line_width(0.5)
        pdf.line(_MARGIN, pdf.get_y(), _PAGE_W - _MARGIN, pdf.get_y())
        pdf.ln(3)
        if shotmap_for:
            pdf._image(shotmap_for, w=110)
            pdf.ln(1)
        if shotmap_against:
            pdf._image(shotmap_against, w=110)

    # ----- PAGE 3: Tactical Profile -----
    pdf.add_page()
    pdf.set_font("U", "B", 13); pdf.set_text_color(*_DARK)
    pdf.set_x(_MARGIN)
    pdf.cell(0, 8, f"{L['tactical_profile']}: {team}",
             new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_draw_color(*_GREEN); pdf.set_line_width(0.5)
    pdf.line(_MARGIN, pdf.get_y(), _PAGE_W - _MARGIN, pdf.get_y())
    pdf.ln(4)

    pdf._two_col(L["strengths"], report.get("strengths", []),
                 L["weaknesses"], report.get("weaknesses", []))
    pdf.ln(3)

    pdf._section_bar(L["key_patterns"])
    pdf._bullets(report.get("key_patterns", []))
    pdf.ln(2)

    pdf._section_bar(L["pressing_vuln"], color=_AMBER)
    pdf._bullets(report.get("pressing_vulnerabilities", []))
    pdf.ln(2)

    pdf._section_bar(L["set_piece_tend"], color=_PURPLE)
    pdf._bullets(report.get("set_piece_tendencies", []))

    # ----- PAGE 4: Danger Players + Timing + Circumstances -----
    danger = report.get("top_danger_players", [])
    how_score = report.get("how_they_score", [])
    how_concede = report.get("how_they_concede", [])
    if danger or timing_png or how_score:
        pdf.add_page()
        pdf.set_font("U", "B", 13); pdf.set_text_color(*_DARK)
        pdf.set_x(_MARGIN)
        pdf.cell(0, 8, f"{L['danger_analysis']}: {team}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_draw_color(*_RED); pdf.set_line_width(0.5)
        pdf.line(_MARGIN, pdf.get_y(), _PAGE_W - _MARGIN, pdf.get_y())
        pdf.ln(4)

        if danger:
            pdf._section_bar(L["danger_players"], color=_RED)
            pdf._danger_table(danger, L)
            pdf.ln(2)

        if how_score:
            pdf._section_bar(L["how_they_score"], color=_GREEN)
            pdf._bullets(how_score)
            pdf.ln(1)
        if how_concede:
            pdf._section_bar(L["how_they_concede"], color=_AMBER)
            pdf._bullets(how_concede)
            pdf.ln(1)

        # Goal log — scorers with minutes
        glog_for = report.get("goals_log_for", [])
        glog_against = report.get("goals_log_against", [])
        if glog_for or glog_against:
            pdf._section_bar(L["goal_log"], color=_DARK)
            pdf.set_font("U", "", 8.5); pdf.set_text_color(*_DARK)
            if glog_for:
                pdf.set_x(_MARGIN)
                pdf.set_font("U", "B", 8); pdf.set_text_color(*_GRAY)
                pdf.cell(0, 5, L["goals_scored"].upper(), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
                pdf.set_font("U", "", 8.5); pdf.set_text_color(*_DARK)
                pdf.set_x(_MARGIN)
                pdf.multi_cell(_INNER, 5.5, "  ·  ".join(glog_for), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            if glog_against:
                pdf.ln(1)
                pdf.set_x(_MARGIN)
                pdf.set_font("U", "B", 8); pdf.set_text_color(*_GRAY)
                pdf.cell(0, 5, L["goals_conceded"].upper(), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
                pdf.set_font("U", "", 8.5); pdf.set_text_color(*_DARK)
                pdf.set_x(_MARGIN)
                pdf.multi_cell(_INNER, 5.5, "  ·  ".join(glog_against), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.ln(2)

        if timing_png:
            pdf._image(timing_png, w=150)

    # ----- PAGE 5: How to Beat Them -----
    pdf.add_page()
    pdf.set_font("U", "B", 13); pdf.set_text_color(*_DARK)
    pdf.set_x(_MARGIN)
    pdf.cell(0, 8, f"{L['how_to_beat']}: {team}",
             new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_draw_color(*_RED); pdf.set_line_width(0.5)
    pdf.line(_MARGIN, pdf.get_y(), _PAGE_W - _MARGIN, pdf.get_y())
    pdf.ln(3)

    pdf.set_font("U", "I", 8.5); pdf.set_text_color(*_GRAY)
    pdf.set_x(_MARGIN)
    pdf.cell(0, 5, L["how_to_beat_desc"], new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(2)

    for i, item in enumerate(report.get("how_to_beat_them", []), 1):
        pdf.set_x(_MARGIN)
        pdf.set_fill_color(*_GREEN_LT)
        pdf.set_font("U", "B", 10); pdf.set_text_color(*_GREEN)
        pdf.cell(8, 8, str(i), fill=True, align="C",
                 new_x=XPos.RIGHT, new_y=YPos.TOP)
        pdf.set_font("U", "", 9); pdf.set_text_color(*_DARK)
        pdf.multi_cell(_INNER - 10, 8, f"  {item}",
                       new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.ln(1)

    # ----- FINAL PAGE: Key Alerts for coaching staff -----
    alerts = report.get("key_alerts", [])
    if alerts:
        pdf.add_page()
        pdf.set_font("U", "B", 13); pdf.set_text_color(*_DARK)
        pdf.set_x(_MARGIN)
        pdf.cell(0, 8, L["key_alerts"], new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_draw_color(*_RED); pdf.set_line_width(0.5)
        pdf.line(_MARGIN, pdf.get_y(), _PAGE_W - _MARGIN, pdf.get_y())
        pdf.ln(2)
        pdf.set_font("U", "I", 8.5); pdf.set_text_color(*_GRAY)
        pdf.set_x(_MARGIN)
        pdf.cell(0, 5, L["key_alerts_desc"], new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.ln(3)

        for alert in alerts:
            y = pdf.get_y()
            pdf.set_fill_color(254, 242, 242)  # red-50
            pdf.set_draw_color(*_RED)
            pdf.set_x(_MARGIN)
            # red left bar
            pdf.set_fill_color(*_RED)
            pdf.rect(_MARGIN, y, 2, 11, "F")
            pdf.set_fill_color(254, 242, 242)
            pdf.set_xy(_MARGIN + 2, y)
            pdf.set_font("U", "B", 10); pdf.set_text_color(185, 28, 28)
            pdf.multi_cell(_INNER - 2, 11, f"   {alert}", fill=True,
                           new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.ln(2)

    pdf._data_footer(source)

    buf = BytesIO()
    pdf.output(buf)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Labels
# ---------------------------------------------------------------------------

def _labels(lang: str) -> dict[str, str]:
    if lang == "pt":
        return {
            "match_prep": "Preparacao de Jogo",
            "scout_report": "Relatorio de Scout",
            "exec_summary": "Sumario Executivo",
            "season_stats": "Estatisticas da Epoca",
            "recent_form": "Forma Recente",
            "opp_analysis": "Analise do Adversario",
            "tactical_profile": "Perfil Tactico",
            "strengths": "Pontos Fortes",
            "weaknesses": "Pontos Fracos",
            "key_threats": "Ameacas a Neutralizar",
            "key_patterns": "Padroes Identificados",
            "tactical_approach": "Abordagem Tactica",
            "game_plan": "Plano de Jogo",
            "pressing_triggers": "Gatilhos de Pressao",
            "attacking_approach": "Abordagem Ofensiva",
            "set_pieces": "Bolas Paradas",
            "risk": "Riscos Principais",
            "my_team": "A minha equipa",
            "opponent": "Adversario",
            "form_analysis": "Analise de Forma",
            "playing_style": "Estilo de Jogo",
            "pressing_vuln": "Vulnerabilidades a Pressao",
            "set_piece_tend": "Tendencias em Bolas Paradas",
            "how_to_beat": "Como Bater Esta Equipa",
            "how_to_beat_desc": "Instrucoes tacticas especificas com base nos dados analisados:",
            "probable_lineup": "Onze Provavel (inferido)",
            "shot_analysis": "Analise de Remates",
            "shots_taken": "Remates Efectuados",
            "shots_conceded": "Remates Sofridos",
            "goal_timing": "Distribuicao de Golos por Minuto",
            "danger_analysis": "Jogadores Perigosos e Padroes",
            "danger_players": "Top 3 Jogadores Mais Perigosos",
            "how_they_score": "Como Marcam",
            "how_they_concede": "Como Sofrem",
            "player": "Jogador",
            "on_target": "Ao alvo",
            "danger": "Perigo",
            "key_alerts": "Alertas Chave",
            "key_alerts_desc": "Pontos criticos para a equipa tecnica:",
            "sub_notes": "Gestao de Jogo",
            "matchup_edges": "Confronto Directo (ataque deles vs defesa nossa)",
            "priority_alerts": "Alertas Prioritarios",
            "main_danger": "Jogador mais perigoso",
            "goal_log": "Golos (marcadores e minutos)",
            "goals_scored": "Marcados",
            "goals_conceded": "Sofridos",
            "formation": "FORMACAO",
            "head_to_head": "Comparacao Directa (por jogo)",
            "competition_context": "Contexto na Competicao",
            "data_confidence": "Confianca dos Dados",
            "dq_matches": "jogos",
            "dq_shots": "remates c/ coords",
        }
    return {
        "match_prep": "Match Preparation Report",
        "scout_report": "Opponent Scout Report",
        "exec_summary": "Executive Summary",
        "season_stats": "Season Statistics",
        "recent_form": "Recent Form",
        "opp_analysis": "Opponent Analysis",
        "tactical_profile": "Tactical Profile",
        "strengths": "Strengths",
        "weaknesses": "Weaknesses",
        "key_threats": "Key Threats to Neutralise",
        "key_patterns": "Key Patterns",
        "tactical_approach": "Tactical Approach",
        "game_plan": "Game Plan",
        "pressing_triggers": "Pressing Triggers",
        "attacking_approach": "Attacking Approach",
        "set_pieces": "Set Pieces",
        "risk": "Main Risks",
        "my_team": "My team",
        "opponent": "Opponent",
        "form_analysis": "Form Analysis",
        "playing_style": "Playing Style",
        "pressing_vuln": "Pressing Vulnerabilities",
        "set_piece_tend": "Set Piece Tendencies",
        "how_to_beat": "How to Beat Them",
        "how_to_beat_desc": "Specific tactical instructions based on analysed data:",
        "probable_lineup": "Probable XI (inferred)",
        "shot_analysis": "Shot Analysis",
        "shots_taken": "Shots Taken",
        "shots_conceded": "Shots Conceded",
        "goal_timing": "Goal Timing Distribution",
        "danger_analysis": "Danger Players & Patterns",
        "danger_players": "Top 3 Most Dangerous Players",
        "how_they_score": "How They Score",
        "how_they_concede": "How They Concede",
        "player": "Player",
        "on_target": "On target",
        "danger": "Danger",
        "key_alerts": "Key Alerts",
        "key_alerts_desc": "Critical points for the coaching staff:",
        "sub_notes": "Match Management",
        "matchup_edges": "Matchup Edges (their attack vs our defence)",
        "priority_alerts": "Priority Alerts",
        "main_danger": "Main danger player",
        "goal_log": "Goals (scorers & minutes)",
        "goals_scored": "Scored",
        "goals_conceded": "Conceded",
        "formation": "FORMATION",
        "head_to_head": "Head-to-Head (per game)",
        "competition_context": "Competition Context",
        "data_confidence": "Data Confidence",
        "dq_matches": "matches",
        "dq_shots": "shots w/ coords",
    }
