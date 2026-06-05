'use client';

import { useEffect, useMemo, useState } from 'react';
import { ExternalLink, LineChart, Radar, Waves } from 'lucide-react';
import {
  fetchPredictions,
  fetchSmartMoneySignals,
  fetchTop100Rankings,
  type Holding,
  type SmartMoneySignal,
  type Top100Coin,
} from '@/lib/api';
import { useChatHistoryContext } from '@/lib/ChatHistoryProvider';

type Tab = 'listings' | 'whales' | 'top100';

function compactUsd(value?: number | null) {
  if (!value || value <= 0) return null;
  if (value < 0.01) return `$${value.toFixed(6)}`;
  if (value < 1) return `$${value.toFixed(4)}`;
  return `$${new Intl.NumberFormat('en-US', {
    notation: value >= 1000 ? 'compact' : 'standard',
    maximumFractionDigits: value >= 1_000_000 ? 1 : 2,
  }).format(value)}`;
}

function displayExchange(exchange?: string | null) {
  const raw = exchange || '';
  if (raw.startsWith('Binance')) return 'Binance';
  if (raw.startsWith('Coinbase')) return 'Coinbase';
  if (raw.startsWith('Kraken')) return 'Kraken';
  if (raw.startsWith('OKX')) return 'OKX';
  if (raw.startsWith('Gate')) return 'Gate.io';
  if (raw.startsWith('Bybit')) return 'Bybit';
  if (raw.startsWith('Bitget')) return 'Bitget';
  return raw;
}

function chainLabel(chain?: string | null) {
  const c = (chain || '').toLowerCase();
  if (c === 'ethereum') return 'ETH';
  if (c === 'solana') return 'Solana';
  if (c === 'bsc') return 'BNB';
  if (c === 'avalanche') return 'AVAX';
  return chain || '';
}

function coingeckoUrl(symbol?: string | null, coinId?: string | null) {
  if (coinId) return `https://www.coingecko.com/en/coins/${coinId}`;
  return `https://www.coingecko.com/en/search?query=${encodeURIComponent(symbol || '')}`;
}

function scoreTone(score?: number | null) {
  if ((score ?? 0) >= 85) return 'bg-emerald-600 text-white';
  if ((score ?? 0) >= 70) return 'bg-blue-50 text-blue-700 ring-1 ring-blue-200';
  return 'bg-zinc-50 text-zinc-600 ring-1 ring-zinc-200';
}

function scoreLabel(score?: number | null) {
  if ((score ?? 0) >= 85) return 'Strong';
  if ((score ?? 0) >= 70) return 'Signal';
  return 'Watch';
}

function deltaText(signal: SmartMoneySignal) {
  const delta = Number(signal.value_delta_usd || 0);
  const value = compactUsd(Math.abs(delta || Number(signal.value_usd || 0))) || '$0';
  if (!delta) return value;
  return `${delta > 0 ? '+' : '-'}${value}`;
}

function top100Reason(coin: Top100Coin) {
  const parts = [];
  if (coin.rsi) parts.push(`RSI ${coin.rsi.toFixed(0)}`);
  if (coin.support) parts.push(`support ${compactUsd(coin.support)}`);
  if (coin.current_position !== undefined && coin.current_position !== null) {
    parts.push(`${Number(coin.current_position).toFixed(0)}% range`);
  }
  return parts.join(' / ') || 'technical setup';
}

function ListingCard({ item }: { item: Holding }) {
  const score = Number(item.score || 0);
  return (
    <div className="rounded-xl border border-zinc-200 bg-white p-3 text-xs shadow-sm">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <div className="truncate text-sm font-bold text-zinc-950">{item.token}</div>
          <div className="truncate text-[10px] text-zinc-500">
            {displayExchange(item.exchange)}{item.chain ? ` · ${chainLabel(item.chain)}` : ''}
          </div>
        </div>
        {score ? (
          <div className={`rounded-lg px-2 py-1 text-right text-[10px] font-semibold ${scoreTone(score)}`}>
            <div>{score.toFixed(0)}/100</div>
            <div className="opacity-75">{scoreLabel(score)}</div>
          </div>
        ) : null}
      </div>
      <div className="mt-3 grid grid-cols-2 gap-2">
        <div className="rounded-lg bg-zinc-50 px-2 py-1.5">
          <div className="text-[9px] uppercase tracking-wide text-zinc-400">Wallet</div>
          <div className="font-semibold text-zinc-900">{compactUsd(item.value_usd) || 'N/A'}</div>
        </div>
        <div className="rounded-lg bg-zinc-50 px-2 py-1.5">
          <div className="text-[9px] uppercase tracking-wide text-zinc-400">Liquidity</div>
          <div className="font-semibold text-zinc-900">{compactUsd(item.liquidity) || 'N/A'}</div>
        </div>
      </div>
      <div className="mt-3 flex gap-2 border-t border-zinc-100 pt-2">
        {item.pair_url ? (
          <a href={item.pair_url} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 rounded-full bg-emerald-50 px-2 py-1 text-[10px] font-semibold text-emerald-700">
            DexScreener <ExternalLink className="h-2.5 w-2.5" />
          </a>
        ) : null}
        <a href={coingeckoUrl(item.token)} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 rounded-full bg-zinc-50 px-2 py-1 text-[10px] font-semibold text-zinc-600">
          CoinGecko <ExternalLink className="h-2.5 w-2.5" />
        </a>
      </div>
    </div>
  );
}

function WhaleCard({ item }: { item: SmartMoneySignal }) {
  return (
    <div className="rounded-xl border border-indigo-100 bg-white p-3 text-xs shadow-sm">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <div className="truncate text-sm font-bold text-zinc-950">{item.token}</div>
          <div className="truncate text-[10px] text-zinc-500">
            {item.entity || 'Arkham'}{item.chain ? ` · ${chainLabel(item.chain)}` : ''}
          </div>
        </div>
        <span className="rounded-full bg-indigo-50 px-2 py-1 text-[10px] font-semibold text-indigo-700">
          {item.signal_direction || 'move'}
        </span>
      </div>
      <div className="mt-3 grid grid-cols-2 gap-2">
        <div className="rounded-lg bg-zinc-50 px-2 py-1.5">
          <div className="text-[9px] uppercase tracking-wide text-zinc-400">Delta</div>
          <div className="font-semibold text-zinc-900">{deltaText(item)}</div>
        </div>
        <div className="rounded-lg bg-zinc-50 px-2 py-1.5 text-right">
          <div className="text-[9px] uppercase tracking-wide text-zinc-400">Position</div>
          <div className="font-semibold text-zinc-900">{compactUsd(item.value_usd) || '$0'}</div>
        </div>
      </div>
    </div>
  );
}

function Top100Card({ item }: { item: Top100Coin }) {
  return (
    <div className="rounded-xl border border-zinc-200 bg-white p-3 text-xs shadow-sm">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <div className="truncate text-sm font-bold text-zinc-950">{item.symbol}</div>
          <div className="truncate text-[10px] text-zinc-500">{item.name || item.symbol}</div>
        </div>
        <div className="text-right">
          <div className="text-sm font-bold text-zinc-950">{compactUsd(item.price) || 'N/A'}</div>
          <div className="text-[10px] text-zinc-500">score {Math.round(item.score || 0)}/100</div>
        </div>
      </div>
      <div className="mt-2 flex items-center justify-between gap-2">
        <span className="rounded-full bg-emerald-50 px-2 py-1 text-[10px] font-semibold text-emerald-700">
          Buy zone
        </span>
        <a href={coingeckoUrl(item.symbol, item.coin_id)} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 text-[10px] font-semibold text-zinc-600">
          CoinGecko <ExternalLink className="h-2.5 w-2.5" />
        </a>
      </div>
      <div className="mt-2 line-clamp-1 text-[11px] text-zinc-600">{top100Reason(item)}</div>
    </div>
  );
}

export function IntelPanel() {
  const [tab, setTab] = useState<Tab>('listings');
  const [listings, setListings] = useState<Holding[]>([]);
  const [whales, setWhales] = useState<SmartMoneySignal[]>([]);
  const [top100, setTop100] = useState<Top100Coin[]>([]);
  const [loading, setLoading] = useState(true);
  const { active } = useChatHistoryContext();
  const hasMessages = (active?.messages?.length ?? 0) > 0;

  useEffect(() => {
    let mounted = true;
    Promise.all([
      fetchPredictions().catch(() => []),
      fetchSmartMoneySignals({ limit: 5 }).catch(() => []),
      fetchTop100Rankings({ mode: 'near_support', limit: 5 }).catch(() => []),
    ]).then(([p, w, t]) => {
      if (!mounted) return;
      setListings(p);
      setWhales(w);
      setTop100(t);
      setLoading(false);
    });
    return () => {
      mounted = false;
    };
  }, []);

  const tabs = useMemo(() => [
    { id: 'listings' as const, label: 'Listings', count: listings.length, icon: Radar },
    { id: 'whales' as const, label: 'Whales', count: whales.length, icon: Waves },
    { id: 'top100' as const, label: 'Top100', count: top100.length, icon: LineChart },
  ], [listings.length, whales.length, top100.length]);

  if (hasMessages) return null;

  return (
    <aside className="fixed right-4 top-4 z-30 hidden w-[21rem] xl:block">
      <div className="overflow-hidden rounded-2xl border border-zinc-200 bg-white/95 shadow-lg shadow-zinc-200/70 backdrop-blur">
        <div className="border-b border-zinc-100 bg-zinc-50/80 p-2">
          <div className="grid grid-cols-3 gap-1">
            {tabs.map((item) => {
              const Icon = item.icon;
              const active = tab === item.id;
              return (
                <button
                  key={item.id}
                  type="button"
                  onClick={() => setTab(item.id)}
                  className={`flex items-center justify-center gap-1.5 rounded-xl px-2 py-2 text-[11px] font-semibold transition ${
                    active ? 'bg-white text-zinc-950 shadow-sm ring-1 ring-zinc-200' : 'text-zinc-500 hover:bg-white/70'
                  }`}
                >
                  <Icon className="h-3.5 w-3.5" />
                  <span>{item.label}</span>
                  <span className="rounded-full bg-zinc-100 px-1.5 text-[10px] text-zinc-500">{item.count}</span>
                </button>
              );
            })}
          </div>
        </div>

        <div className="px-3.5 py-3">
          <div className="text-xs font-bold uppercase tracking-wide text-zinc-800">
            {tab === 'listings' ? 'Listing Radar' : tab === 'whales' ? 'Whale Moves' : 'Top100 Setups'}
          </div>
          <div className="mt-0.5 text-[10px] text-zinc-500">
            {tab === 'listings'
              ? 'Unlisted tokens detected in exchange wallets'
              : tab === 'whales'
                ? 'Arkham entity position changes'
                : 'Technical setups near support'}
          </div>
        </div>

        <div className="max-h-[25rem] space-y-2.5 overflow-auto border-t border-zinc-100 p-3">
          {loading ? <div className="text-xs text-zinc-500">Loading intel...</div> : null}
          {!loading && tab === 'listings' && (
            listings.length ? listings.slice(0, 5).map((item) => <ListingCard key={item.id || `${item.exchange}-${item.token}`} item={item} />)
              : <div className="text-xs text-zinc-500">No fresh unlisted-token signals in the last 2 weeks. Monitoring continues.</div>
          )}
          {!loading && tab === 'whales' && (
            whales.length ? whales.slice(0, 5).map((item) => <WhaleCard key={item.id || `${item.entity}-${item.token}`} item={item} />)
              : <div className="text-xs text-zinc-500">No notable whale moves yet.</div>
          )}
          {!loading && tab === 'top100' && (
            top100.length ? top100.slice(0, 5).map((item) => <Top100Card key={item.symbol} item={item} />)
              : <div className="text-xs text-zinc-500">No top100 ranking available.</div>
          )}
        </div>
      </div>
    </aside>
  );
}
