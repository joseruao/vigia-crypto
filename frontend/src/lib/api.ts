// frontend/src/lib/api.ts
export const API_BASE =
  (process.env.NEXT_PUBLIC_API_URL?.trim() as string) ||
  "https://vigia-crypto-1.onrender.com";

export interface Prediction {
  id: string;
  token: string;
  exchange: string;
  score: number;
  liquidity: number;
  volume_24h: number;
  value_usd?: number;
  pair_url?: string;
  token_address?: string;
  ts?: string;
}

export interface Holding {
  id?: string;
  token: string;
  exchange: string;
  value_usd: number;
  liquidity: number;
  volume_24h: number;
  score: number;
  pair_url?: string;
  token_address?: string;
  analysis?: string;
  chain?: string;
  ts?: string;
}

export async function getPredictions(): Promise<Prediction[]> {
  const res = await fetch(`${API_BASE}/alerts/predictions`, { cache: "no-store" });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export async function getHoldings(): Promise<Holding[]> {
  const res = await fetch(`${API_BASE}/alerts/holdings`, { cache: "no-store" });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}
