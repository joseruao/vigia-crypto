// frontend/src/lib/api.ts
const API_BASE =
  process.env.NEXT_PUBLIC_API_URL ?? "https://vigia-crypto-1.onrender.com";

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
