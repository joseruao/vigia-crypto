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
