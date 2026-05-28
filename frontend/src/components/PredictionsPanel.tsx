// components/PredictionsPanel.tsx
'use client';

import { useEffect, useState } from 'react';
import { useChatHistoryContext } from '@/lib/ChatHistoryProvider';

// Define o tipo Holding localmente
interface Holding {
  id?: string;
  token: string;
  exchange: string;
  value_usd?: number;
  liquidity?: number;
  volume_24h?: number;
  score?: number;
  pair_url?: string;
  token_address?: string;
  analysis?: string;
  analysis_text?: string;
  ai_analysis?: string;
  chain?: string;
}

// Função para buscar predictions (holdings com score alto)
async function getPredictions(): Promise<Holding[]> {
  try {
    // Em desenvolvimento, usa localhost se estiver em localhost
    let API_BASE = process.env.NEXT_PUBLIC_API_URL || 'https://vigia-crypto-1.onrender.com';
    if (typeof window !== 'undefined' && window.location.hostname === 'localhost') {
      API_BASE = 'http://localhost:8000';
    }
    const url = `${API_BASE}/alerts/predictions`;
    console.log('🌐 Fetching from:', url);
    
    const res = await fetch(url, {
      cache: 'no-store',
      headers: {
        'Content-Type': 'application/json',
      },
    });
    
    console.log('📡 Response status:', res.status);
    if (!res.ok) {
      const errorText = await res.text().catch(() => 'Unknown error');
      console.error('❌ Response not OK:', res.status, errorText);
      throw new Error(`Failed to fetch predictions: ${res.status} ${errorText}`);
    }
    
    const data = await res.json();
    console.log('✅ Data received:', Array.isArray(data) ? `Array with ${data.length} items` : typeof data);
    if (Array.isArray(data) && data.length > 0) {
      console.log('📋 First item:', data[0]);
    }
    // Se retornar objeto com items, extrair items; senão usar diretamente
    return Array.isArray(data) ? data : (data?.items || []);
  } catch (error) {
    console.error('❌ Error fetching predictions:', error);
    return [];
  }
}

export function PredictionsPanel() {
  const [items, setItems] = useState<Holding[]>([]);
  const [loading, setLoading] = useState(true);
  const { active } = useChatHistoryContext();

  const hasMessages = (active?.messages?.length ?? 0) > 0;
  const hidden = hasMessages;

  useEffect(() => {
    let mounted = true;
    
    (async () => {
      try {
        console.log('🔍 Buscando predictions...');
        const data = await getPredictions();
        console.log('📊 Predictions recebidas:', data?.length || 0, 'itens');
        if (!mounted) return;
        setItems(Array.isArray(data) ? data : []);
      } catch (e) {
        console.error("❌ Falha a carregar predictions:", e);
        if (mounted) setItems([]);
      } finally {
        if (mounted) setLoading(false);
      }
    })();

    return () => { mounted = false; };
  }, []);

  if (hidden) return null;

  return (
    <div className="fixed inset-x-3 top-3 z-30 sm:inset-x-auto sm:right-4 sm:top-4 sm:w-80">
      <div className="border border-zinc-200 rounded-xl bg-white shadow-md overflow-hidden">
        <div className="px-3 py-2 border-b border-zinc-100">
          <div className="text-xs uppercase tracking-wide text-zinc-500">Previsões de Listing</div>
        </div>

        <div className="max-h-56 overflow-auto p-3 space-y-2 sm:max-h-80">
          {loading ? (
            <div className="text-xs text-zinc-500">A carregar…</div>
          ) : items.length === 0 ? (
            <div className="text-xs text-zinc-500">Sem holdings detetados.</div>
          ) : (
            items.map((h) => (
              <div key={h.id || `${h.token}-${h.exchange}`} className="text-xs bg-zinc-50 border border-zinc-200 rounded-md p-2">
                <div className="font-medium">
                  {h.token}{' '}
                  <span className="text-[10px] text-zinc-500">({h.exchange})</span>
                </div>
                
                {/* ANÁLISE */}
                {(h.analysis || h.analysis_text || h.ai_analysis) && (
                  <div className="mt-1 text-[11px] text-zinc-700 bg-yellow-50 p-1 rounded">
                    {h.analysis || h.analysis_text || h.ai_analysis}
                  </div>
                )}
                
                {/* MÉTRICAS */}
                <div className="mt-1 grid grid-cols-2 gap-x-2 gap-y-1 text-[11px] text-zinc-600">
                  <div>💰 ${h.value_usd?.toLocaleString() || '—'}</div>
                  <div>💧 ${h.liquidity?.toLocaleString() || '—'}</div>
                  <div>📈 ${h.volume_24h?.toLocaleString() || '—'}</div>
                  <div>⭐ {h.score?.toFixed(1) || '—'}</div>
                </div>

                {/* LINKS */}
                <div className="mt-1 flex gap-2 flex-wrap">
                  {h.pair_url && (
                    <a
                      href={h.pair_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-[10px] underline text-emerald-600"
                    >
                      DexScreener
                    </a>
                  )}
                  {h.token_address && (
                    <a
                      href={h.chain === 'solana' 
                        ? `https://solscan.io/token/${h.token_address}`
                        : `https://etherscan.io/token/${h.token_address}`
                      }
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-[10px] underline text-emerald-600"
                    >
                      {h.chain === 'solana' ? 'Solscan' : 'Etherscan'}
                    </a>
                  )}
                  <a
                    href={`https://www.coingecko.com/en/search?query=${encodeURIComponent(h.token)}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-[10px] underline text-emerald-600"
                  >
                    CoinGecko
                  </a>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
