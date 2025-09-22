// src/types.ts
export interface Prediction {
  id: number;
  exchange: string;
  token: string;
  token_address: string;
  amount: number;
  value_usd: number;
  price: number;
  liquidity: number;
  volume_24h: number;
  pair_url: string;
  signature: string;
  timestamp: number | null;
  ts: string | null;
  listed_exchanges: string[];
  special: boolean;
  score: number;
  txns_buys: number;
  txns_sells: number;
  holders_concentration: number;
}
