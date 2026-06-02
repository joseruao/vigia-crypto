// components/PredictionsPanel.tsx
'use client';

import { useEffect, useState } from 'react';
import { useChatHistoryContext } from '@/lib/ChatHistoryProvider';

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
  ts?: string;
}

function compactUsd(value?: number) {
  if (!value || value <= 0) return null;
  return new Intl.NumberFormat('en-US', {
    notation: 'compact',
    maximumFractionDigits: value >= 1_000_000 ? 1 : 0,
  }).format(value);
}

function metric(label: string, value?: number) {
  const formatted = compactUsd(value);
  return formatted ? { label, value: `$${formatted}` } : null;
}

function displayExchange(exchange: string) {
  const map: Record<string, string> = {
    'Binance 1': 'Binance',
    'Binance 2': 'Binance',
    'Binance 3': 'Binance',
    'Binance 7': 'Binance',
    'Binance 8': 'Binance',
    'Binance 14': 'Binance',
    'Binance 16': 'Binance',
    'Binance BNB 7': 'Binance',
    'Binance BNB 28': 'Binance',
    'Binance BNB 51': 'Binance',
    'Binance BNB 70': 'Binance',
    'Binance BNB Hot Wallet 20': 'Binance',
    'Binance AVAX 74': 'Binance',
    'Binance AVAX Cold Wallet 2': 'Binance',
    'Binance AVAX Cold Wallet 5': 'Binance',
    'Binance AVAX Hot Wallet 10': 'Binance',
    'Coinbase 1': 'Coinbase',
    'Coinbase Hot': 'Coinbase',
    'Coinbase 10': 'Coinbase',
    'Kraken Cold 1': 'Kraken',
    'Kraken Cold 2': 'Kraken',
    'OKX 73': 'OKX',
    'OKX 93': 'OKX',
    'OKX BNB 35': 'OKX',
    'Bybit BNB 17': 'Bybit',
    'Gate BNB Deposit Funder': 'Gate.io',
    'Huobi BNB 1': 'Huobi',
    'Bitget Hot Wallet 1': 'Bitget',
  };
  return map[exchange] || exchange;
}

function explorerFor(chain?: string, tokenAddress?: string) {
  if (!tokenAddress) return null;
  const c = (chain || '').toLowerCase();
  if (c === 'solana') return { label: 'Solscan', href: `https://solscan.io/token/${tokenAddress}` };
  if (c === 'bsc') return { label: 'BscScan', href: `https://bscscan.com/token/${tokenAddress}` };
  if (c === 'avalanche') return { label: 'SnowTrace', href: `https://snowtrace.io/token/${tokenAddress}` };
  return { label: 'Etherscan', href: `https://etherscan.io/token/${tokenAddress}` };
}

function scoreTone(score?: number) {
  if ((score ?? 0) >= 80) return 'bg-emerald-50 text-emerald-700 border-emerald-200';
  if ((score ?? 0) >= 65) return 'bg-blue-50 text-blue-700 border-blue-200';
  return 'bg-zinc-50 text-zinc-600 border-zinc-200';
}

function scoreLabel(score?: number) {
  if ((score ?? 0) >= 80) return 'Forte';
  if ((score ?? 0) >= 65) return 'Boa';
  return 'Observação';
}

function scoreAccent(score?: number) {
  if ((score ?? 0) >= 80) return 'border-l-emerald-500';
  if ((score ?? 0) >= 65) return 'border-l-blue-500';
  return 'border-l-zinc-300';
}

function shortDate(value?: string) {
  if (!value) return null;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return null;
  return new Intl.DateTimeFormat('pt-PT', {
    day: '2-digit',
    month: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  }).format(date);
}

async function getPredictions(): Promise<Holding[]> {
  try {
    let API_BASE = process.env.NEXT_PUBLIC_API_URL || 'https://vigia-crypto-1.onrender.com';
    if (typeof window !== 'undefined' && window.location.hostname === 'localhost') {
      API_BASE = 'http://localhost:8000';
    }

    const res = await fetch(`${API_BASE}/alerts/predictions`, {
      cache: 'no-store',
      headers: { 'Content-Type': 'application/json' },
    });

    if (!res.ok) throw new Error(`Failed to fetch predictions: ${res.status}`);

    const data = await res.json();
    return Array.isArray(data) ? data : (data?.items || []);
  } catch (error) {
    console.error('Error fetching predictions:', error);
    return [];
  }
}

export function PredictionsPanel() {
  const [items, setItems] = useState<Holding[]>([]);
  const [loading, setLoading] = useState(true);
  const [lang, setLang] = useState<'pt' | 'en'>('pt');
  const [expanded, setExpanded] = useState(false);
  const { active } = useChatHistoryContext();

  const hasMessages = (active?.messages?.length ?? 0) > 0;
  const title = lang === 'pt' ? 'Previsões de Listing' : 'Listing Predictions';
  const visibleItems = expanded ? items : items.slice(0, 3);

  useEffect(() => {
    let mounted = true;
    const browserLang = navigator.language.toLowerCase();
    setLang(browserLang.startsWith('pt') ? 'pt' : 'en');

    (async () => {
      const data = await getPredictions();
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
    <div className="fixed right-4 top-4 z-30 hidden w-80 sm:block">
      <div aria-label={title} className="overflow-hidden rounded-xl border border-zinc-200 bg-white shadow-md">
        <div className="border-b border-zinc-100 px-3 py-2.5">
          <div className="flex items-center justify-between gap-2">
            <div>
              <div className="text-xs font-semibold uppercase tracking-wide text-zinc-700">{title}</div>
              <div className="mt-0.5 text-[10px] text-zinc-500">
                {lang === 'pt' ? 'Sinais on-chain em exchanges' : 'On-chain exchange signals'}
              </div>
            </div>
            {items.length > 0 ? (
              <span className="rounded-full bg-emerald-50 px-2 py-1 text-[10px] font-semibold text-emerald-700">
                {items.length}
              </span>
            ) : null}
          </div>
        </div>

        <div className="max-h-56 space-y-2 overflow-auto p-3 sm:max-h-80">
          {loading ? (
            <div className="text-xs text-zinc-500">A carregar...</div>
          ) : items.length === 0 ? (
            <div className="text-xs text-zinc-500">
              {lang === 'pt' ? 'Sem sinais novos.' : 'No fresh signals.'}
            </div>
          ) : (
            visibleItems.map((h) => {
              const updatedAt = shortDate(h.ts);
              const exchange = displayExchange(h.exchange);
              const explorer = explorerFor(h.chain, h.token_address);
              const metrics = [
                metric('Valor', h.value_usd),
                metric('Liquidez', h.liquidity),
                metric('Volume', h.volume_24h),
              ].filter(Boolean) as Array<{ label: string; value: string }>;

              return (
                <div
                  key={h.id || `${h.token}-${h.exchange}`}
                  className={`rounded-lg border border-l-4 border-zinc-200 bg-white p-2.5 text-xs shadow-sm ${scoreAccent(h.score)}`}
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="min-w-0">
                      <div className="truncate font-semibold text-zinc-900">{h.token}</div>
                      <div className="flex flex-wrap items-center gap-x-2 gap-y-0.5 text-[10px] text-zinc-500">
                        <span>{exchange}</span>
                        {updatedAt ? <span>{updatedAt}</span> : null}
                      </div>
                    </div>
                    {h.score ? (
                      <div className={`shrink-0 rounded-md border px-2 py-1 text-right ${scoreTone(h.score)}`}>
                        <div className="text-[10px] font-semibold leading-none">{h.score.toFixed(0)}/100</div>
                        <div className="mt-0.5 text-[9px] font-medium leading-none opacity-75">{scoreLabel(h.score)}</div>
                      </div>
                    ) : null}
                  </div>

                  {metrics.length > 0 && (
                    <div className="mt-2 grid grid-cols-3 gap-1.5">
                      {metrics.map((m) => (
                        <div key={m.label} className="rounded-md bg-zinc-50 px-2 py-1">
                          <div className="text-[9px] uppercase tracking-wide text-zinc-400">{m.label}</div>
                          <div className="truncate text-[11px] font-medium text-zinc-700">{m.value}</div>
                        </div>
                      ))}
                    </div>
                  )}

                  <div className="mt-2 flex flex-wrap gap-2 border-t border-zinc-100 pt-2">
                    {h.pair_url && (
                      <a href={h.pair_url} target="_blank" rel="noopener noreferrer" className="text-[10px] underline text-emerald-600">
                        DexScreener
                      </a>
                    )}
                    {explorer && (
                      <a
                        href={explorer.href}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-[10px] underline text-emerald-600"
                      >
                        {explorer.label}
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
              );
            })
          )}
          {!loading && items.length > 3 ? (
            <button
              type="button"
              onClick={() => setExpanded((v) => !v)}
              className="w-full rounded-lg border border-zinc-200 bg-zinc-50 px-3 py-2 text-xs font-medium text-zinc-700 transition hover:bg-zinc-100"
            >
              {expanded
                ? (lang === 'pt' ? 'Ver menos' : 'Show less')
                : (lang === 'pt' ? `Ver mais ${items.length - 3}` : `Show ${items.length - 3} more`)}
            </button>
          ) : null}
        </div>
      </div>
    </div>
  );
}
