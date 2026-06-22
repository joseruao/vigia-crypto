// frontend/src/lib/api.ts
// Em desenvolvimento, usa localhost se estiver em localhost
const getApiBase = () => {
  // Se estiver em localhost, sempre usa API local (ignora env var)
  if (typeof window !== 'undefined' && window.location.hostname === 'localhost') {
    return 'http://localhost:8000';
  }
  // Senão, usa env var ou produção
  return process.env.NEXT_PUBLIC_API_URL || 'https://vigia-crypto-1.onrender.com';
};

const API_BASE = getApiBase();

export type Holding = {
  id?: string | null;
  token: string | null;
  exchange: string | null;
  chain: string | null;
  value_usd: number;
  liquidity: number;
  volume_24h: number;
  score: number;
  pair_url?: string | null;
  analysis?: string | null;
  ts?: string | null;
  token_address?: string | null;
};

export type Top100Coin = {
  symbol: string;
  name?: string | null;
  coin_id?: string | null;
  price?: number | null;
  market_cap?: number | null;
  volume_24h?: number | null;
  score?: number | null;
  risk?: string | null;
  signal?: string | null;
  rationale?: string | null;
  rsi?: number | null;
  trend?: string | null;
  support?: number | null;
  resistance?: number | null;
  current_position?: number | null;
  entry_zone?: string | null;
  technical_action?: string | null;
  change_24h?: number | null;
  change_7d?: number | null;
};

export type SmartMoneySignal = {
  id?: number | string | null;
  entity?: string | null;
  token?: string | null;
  chain?: string | null;
  value_usd?: number | null;
  previous_value_usd?: number | null;
  value_delta_usd?: number | null;
  value_delta_pct?: number | null;
  signal_direction?: 'new' | 'increased' | 'decreased' | 'in' | 'out' | string | null;
  score?: number | null;
  pair_url?: string | null;
  ts?: string | null;
  analysis_text?: string | null;
  entity_type?: string | null;
  exchange?: string | null;
};

export async function fetchHoldings(params?: {
  exchange?: string;
  min_score?: number;
  limit?: number;
}): Promise<Holding[]> {
  const q = new URLSearchParams();
  if (params?.exchange) q.set("exchange", params.exchange);
  if (params?.min_score !== undefined) q.set("min_score", String(params.min_score));
  if (params?.limit !== undefined) q.set("limit", String(params.limit));
  const url =
    q.toString().length > 0
      ? `${API_BASE}/alerts/holdings?${q.toString()}`
      : `${API_BASE}/alerts/holdings`;

  const res = await fetch(url, { cache: "no-store" });
  if (!res.ok) return [];
  return res.json();
}

export async function fetchPredictions(): Promise<Holding[]> {
  const res = await fetch(`${API_BASE}/alerts/predictions`, { cache: "no-store" });
  if (!res.ok) return [];
  return res.json();
}

export async function fetchTop100Rankings(params?: {
  mode?: string;
  limit?: number;
}): Promise<Top100Coin[]> {
  const q = new URLSearchParams();
  q.set("mode", params?.mode || "near_support");
  q.set("limit", String(params?.limit ?? 5));
  const res = await fetch(`${API_BASE}/alerts/top100?${q.toString()}`, { cache: "no-store" });
  if (!res.ok) return [];
  const data = await res.json().catch(() => null);
  return Array.isArray(data?.items) ? data.items : [];
}

export type PrelistingWatchlistItem = {
  token: string;
  token_id?: string | null;
  listing_exchange: string;
  max_score: number;
  wallet_count: number;
  classifications: string[];
  labels: string[];
  investigation_status: string;
  source: string;
};

export async function fetchPrelistingWatchlist(): Promise<PrelistingWatchlistItem[]> {
  const res = await fetch(`${API_BASE}/alerts/prelisting-watchlist`, { cache: "no-store" });
  if (!res.ok) return [];
  const data = await res.json().catch(() => null);
  return Array.isArray(data?.items) ? data.items : [];
}

export async function fetchSmartMoneySignals(params?: { limit?: number }): Promise<SmartMoneySignal[]> {
  const q = new URLSearchParams();
  q.set("limit", String(params?.limit ?? 8));
  const res = await fetch(`${API_BASE}/alerts/smart-money?${q.toString()}`, { cache: "no-store" });
  if (!res.ok) return [];
  const data = await res.json().catch(() => null);
  return Array.isArray(data?.items) ? data.items : [];
}

export async function askAlerts(prompt: string): Promise<string> {
  const res = await fetch(`${API_BASE}/alerts/ask`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ prompt }),
  });
  if (!res.ok) return "erro";
  const data = await res.json();
  return data.answer ?? "sem resposta";
}

export type FootballAnalysisReport = {
  executive_summary: string;
  tactical_strengths: string[];
  tactical_weaknesses: string[];
  key_players_to_watch: string[];
  recommended_match_strategy: string;
  pressing_recommendations: string[];
  set_piece_considerations: string[];
  risk_assessment: string;
};

export type FootballAnalyzeResponse = {
  team_name: string;
  report: FootballAnalysisReport;
};

export type FootballTeamContext = {
  team_name: string;
  source: string;
  stats: string;
  observations: string;
};

export type MatchPrepReport = {
  my_team: string;
  opponent_team: string;
  data_source: string;
  executive_summary: string;
  opponent_strengths: string[];
  opponent_weaknesses: string[];
  key_threats: string[];
  tactical_approach: string;
  pressing_triggers: string[];
  attacking_approach: string[];
  set_piece_plan: string[];
  risk_assessment: string;
  raw_stats_used: string;
  opponent_danger_players?: DangerPlayer[];
  opponent_alerts?: string[];
  opponent_goals_log?: string[];
  my_team_alerts?: string[];
  matchup_insights?: string[];
  substitution_notes?: string[];
  opponent_lineup?: string[];
  opponent_tactical_evolution?: TacticalEvolution;
  images?: {
    shotmap_for?: string;
    shotmap_against?: string;
    timing?: string;
    formation?: string;
  };
};

export type TacticalEvolutionMatch = {
  date: string;
  opponent: string;
  score: string;
  result: string;
  formation_name: string;
  starters: string[];
  changes_from_prev: string[];
};

export type TacticalEvolution = {
  matches: TacticalEvolutionMatch[];
  most_common_formation: string;
  formation_changes: number;
  avg_xi_changes: number;
  summary: string[];
};

export type DangerPlayer = {
  player: string;
  score: number;
  goals: number;
  assists: number;
  shots: number;
  on_target: number;
  xg?: number | null;
};

export type OpponentScoutReport = {
  team: string;
  data_source: string;
  executive_summary: string;
  playing_style: string;
  strengths: string[];
  weaknesses: string[];
  key_patterns: string[];
  how_to_beat_them: string[];
  pressing_vulnerabilities: string[];
  set_piece_tendencies: string[];
  form_analysis: string;
  raw_stats_used: string;
  top_danger_players?: DangerPlayer[];
  key_alerts?: string[];
  goals_log_for?: string[];
  goals_log_against?: string[];
  how_they_score?: string[];
  how_they_concede?: string[];
  probable_lineup?: string[];
  has_xg?: boolean;
  tactical_evolution?: TacticalEvolution;
  viz_payload?: Record<string, unknown>;
  images?: {
    shotmap_for?: string;
    shotmap_against?: string;
    timing?: string;
    formation?: string;
  };
};

export type TeamEntry = { team: string; group: string };

export async function fetchTeams(competition: string = "serie_a"): Promise<TeamEntry[]> {
  const res = await fetch(`${API_BASE}/api/football/teams?competition=${competition}`, { cache: "no-store" });
  if (!res.ok) return [];
  return res.json();
}

export async function exportPdf(input: {
  report_type: "match_prep" | "scout";
  language: string;
  report: object;
}): Promise<Blob> {
  const res = await fetch(`${API_BASE}/api/football/export-pdf`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
  if (!res.ok) {
    const data = await res.json().catch(() => null);
    throw new Error(data?.detail || `HTTP ${res.status}`);
  }
  return res.blob();
}

export async function generateMatchPrep(input: {
  my_team: string;
  opponent_team: string;
  extra_notes?: string;
  language?: string;
  competition?: string;
}): Promise<MatchPrepReport> {
  const res = await fetch(`${API_BASE}/api/football/match-prep`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });

  if (!res.ok) {
    const data = await res.json().catch(() => null);
    throw new Error(data?.detail || `HTTP ${res.status}`);
  }

  return res.json();
}

export async function generateOpponentScout(input: {
  team: string;
  extra_notes?: string;
  language?: string;
  competition?: string;
}): Promise<OpponentScoutReport> {
  const res = await fetch(`${API_BASE}/api/football/opponent-scout`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
  if (!res.ok) {
    const data = await res.json().catch(() => null);
    throw new Error(data?.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

export async function fetchSerieATeams(): Promise<string[]> {
  const res = await fetch(`${API_BASE}/api/football/serie-a/teams`, {
    cache: "no-store",
  });
  if (!res.ok) return [];
  return res.json();
}

export async function analyzeFootballOpponent(input: {
  team_name: string;
  stats: string;
  observations: string;
}): Promise<FootballAnalyzeResponse> {
  const res = await fetch(`${API_BASE}/api/football/analyze`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });

  if (!res.ok) {
    const data = await res.json().catch(() => null);
    throw new Error(data?.detail || `HTTP ${res.status}`);
  }

  return res.json();
}

export async function fetchFootballTeamContext(teamName: string): Promise<FootballTeamContext> {
  const q = new URLSearchParams({ team_name: teamName });
  const res = await fetch(`${API_BASE}/api/football/team-context?${q.toString()}`, {
    cache: "no-store",
  });

  if (!res.ok) {
    const data = await res.json().catch(() => null);
    throw new Error(data?.detail || `HTTP ${res.status}`);
  }

  return res.json();
}
