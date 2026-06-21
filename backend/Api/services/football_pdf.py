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
# Font paths — fallback chain so it works on Linux (Railway) & Windows
# ---------------------------------------------------------------------------
_FONT_PATHS = {
    "regular": [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "C:/Windows/Fonts/arial.ttf",
    ],
    "bold": [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "C:/Windows/Fonts/arialbd.ttf",
    ],
    "italic": [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Oblique.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Italic.ttf",
        "C:/Windows/Fonts/ariali.ttf",
    ],
}


def _find_font(key: str) -> str:
    for path in _FONT_PATHS[key]:
        if os.path.exists(path):
            return path
    raise FileNotFoundError(f"No suitable font found for '{key}'. Checked: {_FONT_PATHS[key]}")


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
        self.cell(0, 5, f"FOOTBALL AI LAB  |  {self._competition}  |  CONFIDENTIAL",
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


# ---------------------------------------------------------------------------
# Match Prep PDF (3 pages)
# ---------------------------------------------------------------------------

def build_match_prep_pdf(report: dict, lang: str = "en") -> bytes:
    L = _labels(lang)
    pdf = _ScoutPDF(orientation="P", unit="mm", format="A4")
    pdf._competition = ("FIFA World Cup 2026"
                        if "world_cup" in report.get("data_source", "").lower()
                        else "Campeonato Brasileiro Serie A")
    pdf._setup_fonts()
    pdf.set_margins(_MARGIN, 14, _MARGIN)
    pdf.set_auto_page_break(auto=True, margin=18)

    my_team  = report.get("my_team", "")
    opp_team = report.get("opponent_team", "")
    source   = report.get("data_source", "")

    # ----- PAGE 1: Cover + Context -----
    pdf.add_page()
    pdf._cover_box(L["match_prep"], f"{my_team}  vs  {opp_team}", source)

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

    pdf._two_col(L["strengths"], report.get("opponent_strengths", []),
                 L["weaknesses"], report.get("opponent_weaknesses", []))
    pdf.ln(3)

    pdf._section_bar(L["key_threats"])
    pdf._bullets(report.get("key_threats", []))
    pdf.ln(2)

    pdf._section_bar(L["tactical_approach"], color=_BLUE)
    pdf._body(report.get("tactical_approach", "-"))

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
                        if "world_cup" in report.get("data_source", "").lower()
                        else "Campeonato Brasileiro Serie A")
    pdf._setup_fonts()
    pdf.set_margins(_MARGIN, 14, _MARGIN)
    pdf.set_auto_page_break(auto=True, margin=18)

    team   = report.get("team", "")
    source = report.get("data_source", "")

    # ----- PAGE 1: Cover + Overview -----
    pdf.add_page()
    pdf._cover_box(L["scout_report"], team, source)

    pdf._section_bar(L["exec_summary"])
    pdf._body(report.get("executive_summary", "-"))
    pdf.ln(2)

    pdf._section_bar(L["form_analysis"], color=_BLUE)
    pdf._body(report.get("form_analysis", "-"))
    pdf.ln(2)

    pdf._section_bar(L["playing_style"], color=_PURPLE)
    pdf._body(report.get("playing_style", "-"))
    pdf.ln(2)

    # Raw data snippet
    raw_lines = [l.strip() for l in report.get("raw_stats_used", "").split("\n") if l.strip()]
    if raw_lines:
        pdf.set_fill_color(*_GRAY_LT)
        pdf.set_font("U", "", 7.5)
        pdf.set_text_color(*_GRAY)
        for line in raw_lines[:8]:
            pdf.set_x(_MARGIN)
            pdf.cell(_INNER, 4.5, line[:105], fill=True,
                     new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    # ----- PAGE 2: Tactical Profile -----
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

    # ----- PAGE 3: How to Beat Them -----
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
            "risk": "Avaliacao de Risco",
            "my_team": "A minha equipa",
            "opponent": "Adversario",
            "form_analysis": "Analise de Forma",
            "playing_style": "Estilo de Jogo",
            "pressing_vuln": "Vulnerabilidades a Pressao",
            "set_piece_tend": "Tendencias em Bolas Paradas",
            "how_to_beat": "Como Bater Esta Equipa",
            "how_to_beat_desc": "Instrucoes tacticas especificas com base nos dados analisados:",
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
        "risk": "Risk Assessment",
        "my_team": "My team",
        "opponent": "Opponent",
        "form_analysis": "Form Analysis",
        "playing_style": "Playing Style",
        "pressing_vuln": "Pressing Vulnerabilities",
        "set_piece_tend": "Set Piece Tendencies",
        "how_to_beat": "How to Beat Them",
        "how_to_beat_desc": "Specific tactical instructions based on analysed data:",
    }
