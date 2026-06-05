'use client';

import { useEffect, useState } from 'react';
import { ExternalLink, Waves } from 'lucide-react';
import { fetchSmartMoneySignals, type SmartMoneySignal } from '@/lib/api';
import { useChatHistoryContext } from '@/lib/ChatHistoryProvider';

function compactUsd(value?: number | null) {
  if (!value || value <= 0) return '$0';
  return `$${new Intl.NumberFormat('en-US', {
    notation: 'compact',
    maximumFractionDigits: value >= 1_000_000 ? 1 : 0,
  }).format(value)}`;
}

function directionLabel(direction?: string | null) {
  if (direction === 'increased') return { label: 'Increased', tone: 'bg-emerald-50 text-emerald-700' };
  if (direction === 'decreased') return { label: 'Reduced', tone: 'bg-amber-50 text-amber-700' };
  return { label: 'New', tone: 'bg-blue-50 text-blue-700' };
}

function chainLabel(chain?: string | null) {
  const c = (chain || '').toLowerCase();
  if (c === 'ethereum') return 'ETH';
  if (c === 'solana') return 'Solana';
  if (c === 'bsc') return 'BNB';
  if (c === 'avalanche') return 'AVAX';
  return chain || '';
}

function deltaText(signal: SmartMoneySignal) {
  const delta = Number(signal.value_delta_usd || 0);
  if (!delta) return compactUsd(signal.value_usd);
  const sign = delta > 0 ? '+' : '-';
  return `${sign}${compactUsd(Math.abs(delta))}`;
}

export function SmartMoneyPanel() {
  const [items, setItems] = useState<SmartMoneySignal[]>([]);
  const [loading, setLoading] = useState(true);
  const { active } = useChatHistoryContext();
  const hasMessages = (active?.messages?.length ?? 0) > 0;

  useEffect(() => {
    let mounted = true;
    (async () => {
      const data = await fetchSmartMoneySignals({ limit: 3 });
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
    <div className="fixed right-4 top-[25rem] z-20 hidden w-[21rem] min-[2100px]:right-[23rem] min-[2100px]:top-[8.25rem] xl:block">
      <div className="overflow-hidden rounded-2xl border border-indigo-100 bg-white/95 shadow-lg shadow-zinc-200/70 backdrop-blur">
        <div className="border-b border-indigo-100 bg-indigo-50/55 px-3.5 py-3">
          <div className="flex items-center justify-between gap-2">
            <div className="flex items-center gap-2">
              <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-white text-indigo-700 ring-1 ring-indigo-100">
                <Waves className="h-4 w-4" />
              </div>
              <div>
                <div className="text-xs font-bold uppercase tracking-wide text-zinc-800">Whale Moves</div>
                <div className="mt-0.5 text-[10px] text-zinc-500">Arkham position deltas</div>
              </div>
            </div>
            {items.length > 0 ? (
              <span className="rounded-full bg-white px-2 py-1 text-[10px] font-semibold text-zinc-600 ring-1 ring-zinc-200">
                {items.length}
              </span>
            ) : null}
          </div>
        </div>

        <div className="max-h-[10rem] space-y-2 overflow-auto p-3">
          {loading ? (
            <div className="text-xs text-zinc-500">Loading moves...</div>
          ) : items.length === 0 ? (
            <div className="text-xs text-zinc-500">No notable smart-money moves yet.</div>
          ) : (
            items.map((signal) => {
              const direction = directionLabel(signal.signal_direction);
              const chain = chainLabel(signal.chain);
              return (
                <div key={signal.id || `${signal.entity}-${signal.token}`} className="rounded-xl border border-indigo-100 bg-white p-2.5 text-xs shadow-sm">
                  <div className="flex items-start justify-between gap-2">
                    <div className="min-w-0">
                      <div className="truncate text-sm font-bold text-zinc-950">{signal.token}</div>
                      <div className="truncate text-[10px] text-zinc-500">
                        {signal.entity || 'Arkham'}{chain ? ` - ${chain}` : ''}
                      </div>
                    </div>
                    <span className={`rounded-full px-2 py-1 text-[10px] font-semibold ${direction.tone}`}>
                      {direction.label}
                    </span>
                  </div>
                  <div className="mt-2 grid grid-cols-2 gap-1.5">
                    <div className="rounded-lg bg-zinc-50 px-2 py-1.5">
                      <div className="text-[10px] uppercase tracking-wide text-zinc-400">Delta</div>
                      <div className="text-sm font-bold text-zinc-950">{deltaText(signal)}</div>
                    </div>
                    <div className="rounded-lg bg-zinc-50 px-2 py-1.5 text-right">
                      <div className="text-[10px] uppercase tracking-wide text-zinc-400">Position</div>
                      <div className="text-sm font-bold text-zinc-950">{compactUsd(signal.value_usd)}</div>
                    </div>
                  </div>
                  <div className="mt-2 flex items-center justify-between gap-2 border-t border-zinc-100 pt-2">
                    <span className="truncate text-[10px] text-zinc-500">Position delta</span>
                    {signal.pair_url ? (
                      <a
                        href={signal.pair_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex shrink-0 items-center gap-1 text-[10px] font-semibold text-zinc-600 hover:text-zinc-950"
                      >
                        Dex <ExternalLink className="h-2.5 w-2.5" />
                      </a>
                    ) : null}
                  </div>
                </div>
              );
            })
          )}
        </div>
      </div>
    </div>
  );
}
