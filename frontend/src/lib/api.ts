// frontend/src/lib/api.ts
const API_BASE =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, '') ||
  "https://vigia-crypto-1.onrender.com";

export async function getPredictions() {
  try {
    const res = await fetch(`${API_BASE}/alerts/predictions`);
    if (!res.ok) throw new Error(`Erro HTTP: ${res.status}`);
    return res.json();
  } catch (err) {
    console.error("Erro a buscar predictions:", err);
    return [];
  }
}

export async function getHoldings(): Promise<Holding[]> {
  try {
    const res = await fetch(`${API_BASE}/alerts/holdings`);
    if (!res.ok) throw new Error(`Erro HTTP: ${res.status}`);
    return res.json();
  } catch (err) {
    console.error("Erro a buscar holdings:", err);
    return [];
  }
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
}
