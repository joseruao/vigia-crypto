'use client';

import { useEffect, useState } from 'react';
import { ExternalLink, LineChart } from 'lucide-react';
import { fetchTop100Rankings, type Top100Coin } from '@/lib/api';
import { useChatHistoryContext } from '@/lib/ChatHistoryProvider';

function compactUsd(value?: number | null) {
  if (!value || value <= 0) return 'N/A';
  if (value < 0.01) return `$${value.toFixed(6)}`;
  if (value < 1) return `$${value.toFixed(4)}`;
  if (value < 1000) {
    return `$${new Intl.NumberFormat('en-US', {
      maximumFractionDigits: 2,
    }).format(value)}`;
  }
  return `$${new Intl.NumberFormat('en-US', {
    notation: 'compact',
    maximumFractionDigits: value >= 1_000_000 ? 1 : 0,
  }).format(value)}`;
}

function coingeckoUrl(symbol?: string | null, coinId?: string | null) {
  if (coinId) return `https://www.coingecko.com/en/coins/${coinId}`;
  return `https://www.coingecko.com/en/search?query=${encodeURIComponent(symbol || '')}`;
}

function zoneLabel(zone?: string | null) {
  if (zone === 'ZONA_DE_COMPRA') return 'Buy zone';
  if (zone === 'ZONA_NEUTRA') return 'Neutral';
  if (zone === 'ZONA_ESTICADA') return 'Extended';
  return 'Setup';
}

function reason(coin: Top100Coin) {
  const parts = [];
  if (coin.rsi) parts.push(`RSI ${coin.rsi.toFixed(0)}`);
  if (coin.support) parts.push(`support ${compactUsd(coin.support)}`);
  if (coin.current_position !== undefined && coin.current_position !== null) {
    parts.push(`${Number(coin.current_position).toFixed(0)}% of range`);
  }
  return parts.join(' · ') || 'Favorable technical score';
}

export function Top100Panel() {
  const [items, setItems] = useState<Top100Coin[]>([]);
  const [loading, setLoading] = useState(true);
  const { active } = useChatHistoryContext();
  const hasMessages = (active?.messages?.length ?? 0) > 0;

  useEffect(() => {
    let mounted = true;
    (async () => {
      const data = await fetchTop100Rankings({ mode: 'near_support', limit: 5 });
      if (mounted) {
        setItems(Array.isArray(data) ? data : []);
        setLoading(false);
      }
    })();
    return () => {
      mounted = false;
    };
  }, []);

  if (hasMessages) return null;

  return (
    <div className="fixed right-4 top-[31rem] z-20 hidden w-[21rem] xl:block">
      <div className="overflow-hidden rounded-2xl border border-zinc-200 bg-white/95 shadow-lg shadow-zinc-200/70 backdrop-blur">
        <div className="border-b border-zinc-100 bg-zinc-50/80 px-3.5 py-3">
          <div className="flex items-center justify-between gap-2">
            <div className="flex items-center gap-2">
              <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-zinc-950 text-white">
                <LineChart className="h-4 w-4" />
              </div>
              <div>
                <div className="text-xs font-bold uppercase tracking-wide text-zinc-800">Top100 Today</div>
                <div className="mt-0.5 text-[10px] text-zinc-500">Technical setups near support</div>
              </div>
            </div>
            {items.length > 0 ? (
              <span className="rounded-full bg-white px-2 py-1 text-[10px] font-semibold text-zinc-600 ring-1 ring-zinc-200">
                {items.length}
              </span>
            ) : null}
          </div>
        </div>

        <div className="max-h-[18rem] space-y-2 overflow-auto p-3">
          {loading ? (
            <div className="text-xs text-zinc-500">Loading ranking...</div>
          ) : items.length === 0 ? (
            <div className="text-xs text-zinc-500">No top100 ranking available.</div>
          ) : (
            items.map((coin) => (
              <div key={coin.symbol} className="rounded-xl border border-zinc-200 bg-white p-3 text-xs shadow-sm">
                <div className="flex items-start justify-between gap-2">
                  <div className="min-w-0">
                    <div className="truncate text-sm font-bold text-zinc-950">{coin.symbol}</div>
                    <div className="truncate text-[10px] text-zinc-500">{coin.name || coin.symbol}</div>
                  </div>
                  <div className="text-right">
                    <div className="text-sm font-bold text-zinc-950">{compactUsd(coin.price)}</div>
                    <div className="text-[10px] text-zinc-500">score {Math.round(coin.score || 0)}/100</div>
                  </div>
                </div>
                <div className="mt-2 flex items-center justify-between gap-2">
                  <span className="rounded-full bg-emerald-50 px-2 py-1 text-[10px] font-semibold text-emerald-700">
                    {zoneLabel(coin.entry_zone)}
                  </span>
                  <a
                    href={coingeckoUrl(coin.symbol, coin.coin_id)}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1 text-[10px] font-semibold text-zinc-600 hover:text-zinc-950"
                  >
                    CoinGecko <ExternalLink className="h-2.5 w-2.5" />
                  </a>
                </div>
                <div className="mt-2 line-clamp-1 text-[11px] text-zinc-600">{reason(coin)}</div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
