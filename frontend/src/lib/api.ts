const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

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
// Adicionar função para buscar holdings
export async function getHoldings(): Promise<Holding[]> {
  const res = await fetch('/api/holdings');
  if (!res.ok) throw new Error('Failed to fetch holdings');
  return res.json();
}

// Atualizar o tipo Prediction para Holding
export interface Holding {
  id: string;
  token: string;
  exchange: string;
  value_usd: number;
  liquidity: number;
  volume_24h: number;
  score: number;
  pair_url?: string;
  token_address?: string;
  analysis?: string; // ⬅️ NOVO CAMPO
}