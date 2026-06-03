from __future__ import annotations

import json
import os

from pydantic import BaseModel, Field


class FootballAnalyzeRequest(BaseModel):
    team_name: str = Field(..., min_length=1, max_length=120)
    stats: str = Field(default="", max_length=12000)
    observations: str = Field(default="", max_length=20000)


class FootballAnalysisReport(BaseModel):
    executive_summary: str
    tactical_strengths: list[str]
    tactical_weaknesses: list[str]
    key_players_to_watch: list[str]
    recommended_match_strategy: str
    pressing_recommendations: list[str]
    set_piece_considerations: list[str]
    risk_assessment: str


class FootballAnalyzeResponse(BaseModel):
    team_name: str
    report: FootballAnalysisReport


def _system_prompt() -> str:
    return (
        "You are a senior football opposition analyst helping coaches prepare match plans. "
        "Use only the team name, stats, and raw observations supplied by the user. "
        "If information is missing, state the uncertainty inside the relevant section instead of inventing facts. "
        "Return concise, practical coaching language. "
        "Output valid JSON only."
    )


def _user_prompt(payload: FootballAnalyzeRequest) -> str:
    return f"""
Create an opponent analysis report for: {payload.team_name}

Raw statistics:
{payload.stats or "No structured stats provided."}

Raw match observations:
{payload.observations or "No observations provided."}

Return this JSON object exactly:
{{
  "executive_summary": "2-4 sentence overview",
  "tactical_strengths": ["strength 1", "strength 2", "strength 3"],
  "tactical_weaknesses": ["weakness 1", "weakness 2", "weakness 3"],
  "key_players_to_watch": ["player or role 1", "player or role 2"],
  "recommended_match_strategy": "clear match plan",
  "pressing_recommendations": ["pressing trigger 1", "pressing trigger 2"],
  "set_piece_considerations": ["set piece note 1", "set piece note 2"],
  "risk_assessment": "main risks and mitigation"
}}
""".strip()


def _coerce_list(value: object) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def _normalise_report(raw: dict) -> FootballAnalysisReport:
    return FootballAnalysisReport(
        executive_summary=str(raw.get("executive_summary") or "").strip(),
        tactical_strengths=_coerce_list(raw.get("tactical_strengths")),
        tactical_weaknesses=_coerce_list(raw.get("tactical_weaknesses")),
        key_players_to_watch=_coerce_list(raw.get("key_players_to_watch")),
        recommended_match_strategy=str(raw.get("recommended_match_strategy") or "").strip(),
        pressing_recommendations=_coerce_list(raw.get("pressing_recommendations")),
        set_piece_considerations=_coerce_list(raw.get("set_piece_considerations")),
        risk_assessment=str(raw.get("risk_assessment") or "").strip(),
    )


def generate_opponent_report(payload: FootballAnalyzeRequest) -> FootballAnalyzeResponse:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not configured")

    from openai import OpenAI

    client = OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": _system_prompt()},
            {"role": "user", "content": _user_prompt(payload)},
        ],
        temperature=0.25,
    )

    content = response.choices[0].message.content or "{}"
    try:
        raw = json.loads(content)
    except json.JSONDecodeError as exc:
        raise ValueError("OpenAI returned invalid JSON") from exc

    return FootballAnalyzeResponse(
        team_name=payload.team_name.strip(),
        report=_normalise_report(raw),
    )
