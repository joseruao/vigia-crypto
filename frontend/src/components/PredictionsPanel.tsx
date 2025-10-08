'use client';

import { useEffect, useState } from 'react';
import { getPredictions } from '@/lib/api';
import { Prediction } from '@/lib/types';
import { useChatHistoryContext } from '@/lib/ChatHistoryProvider';

export function PredictionsPanel() {
  const [items, setItems] = useState<Prediction[]>([]);
  const [loading, setLoading] = useState(true);
  const { active } = useChatHistoryContext();

  // Esconde quando já existem mensagens na conversa
  const hasMessages = (active?.messages?.length ?? 0) > 0;
  const hidden = hasMessages;

  useEffect(() => {
    let mounted = true;
    (async () => {
      try {
        const data = await getPredictions();
        if (!mounted) return;
        setItems(Array.isArray(data) ? data : []);
      } catch (e) {
        console.error("Falha a carregar predictions:", e);
        if (mounted) setItems([]);
      } finally {
        if (mounted) setLoading(false);
      }
    })();
    return () => { mounted = false; };
  }, []);

  if (hidden) return null;

  return (
    <div className="fixed top-4 right-4 z-30 w-80">
      <div className="border border-zinc-200 rounded-xl bg-white shadow-md overflow-hidden">
        <div className="px-3 py-2 border-b border-zinc-100">
          <div className="text-xs uppercase tracking-wide text-zinc-500">Listings</div>
        </div>

        <div className="max-h-80 overflow-auto p-3 space-y-2">
          {loading ? (
            <div className="text-xs text-zinc-500">A carregar…</div>
          ) : items.length === 0 ? (
            <div className="text-xs text-zinc-500">Sem dados agora.</div>
          ) : (
            items.map((p) => (
              <div key={p.id} className="text-xs bg-zinc-50 border border-zinc-200 rounded-md p-2">
                <div className="font-medium">
                  {p.token}{' '}
                  <span className="text-[10px] text-zinc-500">({p.exchange})</span>
                </div>
                <div className="mt-1 grid grid-cols-2 gap-x-2 gap-y-1 text-[11px] text-zinc-600">
                  <div>💰 ${p.value_usd != null ? p.value_usd.toLocaleString() : '—'}</div>
                  <div>💧 ${p.liquidity != null ? p.liquidity.toLocaleString() : '—'}</div>
                  <div>📈 ${p.volume_24h != null ? p.volume_24h.toLocaleString() : '—'}</div>
                  <div>⭐ {p.score != null ? p.score.toFixed(1) : '—'}</div>
                </div>
                <div className="mt-1 flex gap-2">
                  {p.pair_url && (
                    <a
                      href={p.pair_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="underline text-emerald-600"
                    >
                      DexScreener
                    </a>
                  )}
                  {p.token_address && (
                    <a
                      href={`https://solscan.io/token/${p.token_address}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="underline text-emerald-600"
                    >
                      Solscan
                    </a>
                  )}
                  <a
                    href={`https://www.coingecko.com/en/search?query=${encodeURIComponent(p.token)}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="underline text-emerald-600"
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
