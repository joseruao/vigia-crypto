// Roles suportados nas mensagens do chat
export type Role = 'user' | 'assistant';

// Mensagem de chat
export interface Message {
  role: Role;
  content: string;
}

// Uma sessão/conversa no histórico
export interface Session {
  id: string;            // uuid
  title: string;         // primeiro prompt ou título editado
  messages: Message[];   // histórico da conversa
  createdAt: number;     // Date.now()
  updatedAt: number;     // Date.now()
}

// Prediction (registo vindo do backend / Supabase)
export interface Prediction {
  id: number;
  exchange: string;
  token: string;

  token_address?: string | null;
  amount?: number | null;
  value_usd?: number | null;
  price?: number | null;
  liquidity?: number | null;
  volume_24h?: number | null;

  pair_url?: string | null;
  signature?: string | null;

  timestamp?: number | null; // pode vir null
  ts?: string | null;        // ISO string no backend

  listed_exchanges?: string[];
  special?: boolean;

  score?: number | null;
  txns_buys?: number | null;
  txns_sells?: number | null;
  holders_concentration?: number | null;
}
