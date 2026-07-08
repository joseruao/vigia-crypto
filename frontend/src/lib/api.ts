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
  opponent_ranks?: CompetitionRank[];
  comparison?: ComparisonMetric[];
  data_quality?: DataQuality;
  images?: {
    shotmap_for?: string;
    shotmap_against?: string;
    timing?: string;
    formation?: string;
    comparison?: string;
  };
};

export type DataQuality = {
  provider: string;
  matches_analysed: number;
  shots_with_coordinates: number;
  xg_source: string;
  lineup_source: string;
  confidence: 'low' | 'medium' | 'high' | string;
  confidence_label: string;
  warnings: string[];
};

export type CompetitionRank = {
  metric: string;
  label: string;
  value: string;
  rank: number;
  total: number;
  good: boolean;
  bad: boolean;
  text: string;
};

export type ComparisonMetric = {
  label: string;
  my: number;
  opp: number;
  my_disp: string;
  opp_disp: string;
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
  competition_ranks?: CompetitionRank[];
  data_quality?: DataQuality;
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

// ---------------------------------------------------------------------------
// Football Bet — value board
// ---------------------------------------------------------------------------

export interface BetEdge {
  market: string;        // "goals" | "corners" | "cards"
  book: string;
  line: number;
  side: string;          // "over" | "under"
  odd: number;
  model_prob: number;
  fair_prob: number;
  edge: number;
  ev_per_unit: number;
  n_games: number;
  lambda: number;
  warning: string | null;
  best?: boolean;
}

export interface BetMatch {
  sport_key: string;
  home: string;
  away: string;
  commence: string;
  home_resolved: boolean;
  away_resolved: boolean;
  home_games: number;
  away_games: number;
  min_games: number;
  picks: BetEdge[];       // curated: best pick per market (top one has best=true)
  candidates: number;     // how many raw rows were collapsed
  edges: BetEdge[];       // full list
}

export interface BetBoard {
  source: string;
  competitions: string[];
  hours_ahead: number;
  last_n: number;
  credits_remaining: number | null;
  total_value_rows: number;
  disclaimer: string;
  matches: BetMatch[];
}

export async function fetchBetBoard(hours: number = 48): Promise<BetBoard> {
  const res = await fetch(`${API_BASE}/api/bet/scan?hours=${hours}`, { cache: "no-store" });
  if (!res.ok) {
    const data = await res.json().catch(() => null);
    throw new Error(data?.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

// ---------------------------------------------------------------------------
// Devil's Advocate - private legal argument stress test
// ---------------------------------------------------------------------------

export type DevilsAdvocateRisk = {
  title: string;
  points: string[];
};

export type DevilsAdvocateLegalReference = {
  point: string;
  source: string;
  status: string;
};

export type DevilsAdvocateReport = {
  document_name: string;
  jurisdiction: string;
  legal_area: string;
  document_type: string;
  represented_side: string;
  objective: string;
  source_note: string;
  executive_summary: string;
  case_theory: string[];
  opponent_theory: string[];
  extracted_facts: string[];
  advocate_argument: string[];
  opponent_argument: string[];
  audit_findings: string[];
  burden_and_proof: string[];
  hearing_questions: string[];
  next_actions: string[];
  unverified_legal_points: string[];
  missing_evidence: string[];
  questions_for_lawyer: string[];
  risk_matrix: DevilsAdvocateRisk[];
  cited_sources_in_document: string[];
  legal_references_used: DevilsAdvocateLegalReference[];
  confidence_note: string;
  content_truncated: boolean;
};

export async function analyzeDevilsAdvocate(input: {
  file: File;
  jurisdiction: string;
  legal_area: string;
  document_type: string;
  represented_side: string;
  objective: string;
  language: "pt" | "en";
  accessCode: string;
  provider?: "openai" | "mistral";
}): Promise<DevilsAdvocateReport> {
  const form = new FormData();
  form.set("file", input.file);
  form.set("jurisdiction", input.jurisdiction);
  form.set("legal_area", input.legal_area);
  form.set("document_type", input.document_type);
  form.set("represented_side", input.represented_side);
  form.set("objective", input.objective);
  form.set("language", input.language);
  form.set("provider", input.provider ?? "openai");

  // Local models (Ollama, desktop app) on modest hardware are slow — give them
  // far more room. Cloud stays at 2 min so a hung backend surfaces quickly.
  const onLocalhost =
    typeof window !== "undefined" && window.location.hostname === "localhost";
  // Cloud reasoning models (gpt-5.x) can take a few minutes even on small input.
  // Wait longer than the backend's own timeout so a slow result is delivered
  // instead of being abandoned after it was already generated and billed.
  // Local models are free and slow-is-normal — allow up to 30 min (only catches a
  // hung server). Cloud stays short to fail fast and bound cost.
  const timeoutMs = onLocalhost ? 1_800_000 : 270_000;
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);
  let res: Response;
  try {
    res = await fetch(`${API_BASE}/api/devils-advocate/analyze`, {
      method: "POST",
      headers: { "X-Access-Code": input.accessCode },
      body: form,
      signal: controller.signal,
    });
  } catch (err) {
    if (err instanceof DOMException && err.name === "AbortError") {
      throw new Error("A análise demorou demasiado. Tente novamente.");
    }
    throw err;
  } finally {
    clearTimeout(timeout);
  }
  if (!res.ok) {
    const data = await res.json().catch(() => null);
    const err = new Error(data?.detail || `HTTP ${res.status}`);
    err.name = `HTTP_${res.status}`;
    throw err;
  }
  const data = await res.json();
  return data.report;
}

export type AcordaoSummary = {
  source_label: string;
  tribunal: string;
  processo: string;
  data: string;
  relator: string;
  descritores: string[];
  sumario_oficial: string;
  questao_juridica: string[];
  decisao: string;
  fundamentacao: string[];
  normas_citadas: string[];
  jurisprudencia_citada: string[];
  relevancia: string[];
  source_note: string;
  confidence_note: string;
  content_truncated: boolean;
};

export async function summarizeAcordao(input: {
  file?: File | null;
  url?: string;
  language: "pt" | "en";
  accessCode: string;
  provider?: "openai" | "mistral";
}): Promise<AcordaoSummary> {
  const form = new FormData();
  if (input.url && input.url.trim()) form.set("url", input.url.trim());
  else if (input.file) form.set("file", input.file);
  form.set("language", input.language);
  form.set("provider", input.provider ?? "openai");

  const onLocalhost =
    typeof window !== "undefined" && window.location.hostname === "localhost";
  const timeoutMs = onLocalhost ? 1_800_000 : 270_000;
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);
  let res: Response;
  try {
    res = await fetch(`${API_BASE}/api/devils-advocate/summarize`, {
      method: "POST",
      headers: { "X-Access-Code": input.accessCode },
      body: form,
      signal: controller.signal,
    });
  } catch (err) {
    if (err instanceof DOMException && err.name === "AbortError") {
      throw new Error("O resumo demorou demasiado. Tente novamente.");
    }
    throw err;
  } finally {
    clearTimeout(timeout);
  }
  if (!res.ok) {
    const data = await res.json().catch(() => null);
    const err = new Error(data?.detail || `HTTP ${res.status}`);
    err.name = `HTTP_${res.status}`;
    throw err;
  }
  const data = await res.json();
  return data.summary;
}

// ---------------------------------------------------------------------------
// PME - purchasing comparison MVP
// ---------------------------------------------------------------------------

export type PmeCatalogItem = {
  supplier: string;
  product: string;
  description: string;
  quantity: string;
  unit: string;
  unit_price: string;
  total_price?: string | null;
  promotions: string;
  notes: string;
  source_file: string;
  normalized_product: string;
  effective_unit_price: string;
  confidence: string;
  commercial_value: string;
  commercial_terms: PmeCommercialTerm[];
};

export type PmeCommercialTerm = {
  type: string;
  label: string;
  quantity: string;
  unit: string;
  estimated_unit_value: string;
  estimated_total_value: string;
  confidence: string;
  raw_text: string;
};

export type PmeRecommendation = {
  product: string;
  recommended_supplier: string;
  price: string;
  requested_quantity: string;
  estimated_total_cost: string;
  baseline_total_cost: string;
  reason: string;
  estimated_savings: string;
  alternatives: PmeCatalogItem[];
};

export type PmeProcurementAnalysis = {
  total_items: number;
  products_compared: number;
  estimated_savings_week: string;
  recommendations: PmeRecommendation[];
  warnings: string[];
};

export async function analyzePmeProcurement(input: {
  files: File[];
  needsText?: string;
  commercialValuesText?: string;
  accessCode?: string;
}): Promise<PmeProcurementAnalysis> {
  const form = new FormData();
  input.files.forEach((file) => form.append("files", file));
  form.set("needs_text", input.needsText ?? "");
  form.set("commercial_values_text", input.commercialValuesText ?? "");
  const res = await fetch(`${API_BASE}/api/pme/procurement/analyze`, {
    method: "POST",
    headers: input.accessCode ? { "X-Access-Code": input.accessCode } : undefined,
    body: form,
  });
  if (!res.ok) {
    const data = await res.json().catch(() => null);
    throw new Error(data?.detail || `HTTP ${res.status}`);
  }
  return res.json();
}
