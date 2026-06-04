'use client';

import { useEffect, useMemo, useState } from 'react';
import { ExternalLink, LineChart, Radar, Search, ShieldCheck } from 'lucide-react';
import { fetchPredictions, fetchTop100Rankings, type Holding, type Top100Coin } from '@/lib/api';

type Props = {
  onAsk: (prompt: string) => void;
};

function compactUsd(value?: number | null) {
  if (!value || value <= 0) return 'N/A';
  return `$${new Intl.NumberFormat('en-US', {
    notation: 'compact',
    maximumFractionDigits: value >= 1_000_000 ? 1 : 0,
  }).format(value)}`;
}

function displayExchange(exchange?: string | null) {
  const ex = exchange || 'N/A';
  if (ex.startsWith('Binance')) return 'Binance';
  if (ex.startsWith('Coinbase')) return 'Coinbase';
  if (ex.startsWith('Kraken')) return 'Kraken';
  if (ex.startsWith('OKX')) return 'OKX';
  if (ex.includes('Gate')) return 'Gate.io';
  if (ex.includes('Bybit')) return 'Bybit';
  if (ex.includes('Bitget')) return 'Bitget';
  return ex;
}

function chainLabel(chain?: string | null) {
  const c = (chain || '').toLowerCase();
  if (c === 'bsc') return 'BNB';
  if (c === 'avalanche') return 'AVAX';
  if (c === 'ethereum') return 'Ethereum';
  if (c === 'solana') return 'Solana';
  return chain || '';
}

function coingeckoUrl(symbol?: string | null, coinId?: string | null) {
  if (coinId) return `https://www.coingecko.com/en/coins/${coinId}`;
  return `https://www.coingecko.com/en/search?query=${encodeURIComponent(symbol || '')}`;
}

function verdict(score?: number | null) {
  const s = score || 0;
  if (s >= 85) return 'Forte candidato';
  if (s >= 75) return 'Bom sinal';
  if (s >= 65) return 'Observar';
  return 'Sinal inicial';
}

function zoneLabel(zone?: string | null) {
  if (zone === 'ZONA_DE_COMPRA') return 'zona de compra';
  if (zone === 'ZONA_NEUTRA') return 'zona neutra';
  if (zone === 'ZONA_ESTICADA') return 'preco esticado';
  return 'setup tecnico';
}

function top100Reason(coin: Top100Coin) {
  const bits = [];
  if (coin.entry_zone) bits.push(zoneLabel(coin.entry_zone));
  if (coin.rsi) bits.push(`RSI ${coin.rsi.toFixed(0)}`);
  if (coin.support) bits.push(`suporte ${compactUsd(coin.support)}`);
  if (coin.trend) bits.push(String(coin.trend).replaceAll('_', ' ').toLowerCase());
  return bits.slice(0, 3).join(' + ') || coin.rationale || 'score tecnico favoravel';
}

export function DashboardHome({ onAsk }: Props) {
  const [predictions, setPredictions] = useState<Holding[]>([]);
  const [top100, setTop100] = useState<Top100Coin[]>([]);
  const [loading, setLoading] = useState(true);
  const [slowWakeup, setSlowWakeup] = useState(false);

  useEffect(() => {
    let mounted = true;
    const timer = window.setTimeout(() => {
      if (mounted) setSlowWakeup(true);
    }, 3500);
    (async () => {
      const [listingRows, topRows] = await Promise.all([
        fetchPredictions(),
        fetchTop100Rankings({ mode: 'near_support', limit: 5 }),
      ]);
      if (!mounted) return;
      setPredictions(Array.isArray(listingRows) ? listingRows.slice(0, 6) : []);
      setTop100(Array.isArray(topRows) ? topRows.slice(0, 5) : []);
      setLoading(false);
      setSlowWakeup(false);
    })();
    return () => {
      mounted = false;
      window.clearTimeout(timer);
    };
  }, []);

  const stats = useMemo(() => {
    const exchanges = new Set(predictions.map((p) => displayExchange(p.exchange)).filter(Boolean));
    const best = predictions[0]?.score ? Math.round(predictions[0].score) : 0;
    return [
      { label: 'Sinais ativos', value: predictions.length || '-' },
      { label: 'Exchanges', value: exchanges.size || '-' },
      { label: 'Melhor score', value: best ? `${best}/100` : '-' },
    ];
  }, [predictions]);

  return (
    <div className="w-full px-4 py-6 sm:px-6 sm:py-10">
      <div className="mx-auto max-w-6xl">
        <div className="mb-5 flex flex-col gap-4 sm:mb-7 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <div className="inline-flex items-center gap-2 rounded-full border border-zinc-200 bg-white px-3 py-1 text-xs font-medium text-zinc-600 shadow-sm">
              <Radar className="h-3.5 w-3.5 text-blue-600" />
              Exchange Wallet Radar
            </div>
            <h1 className="mt-3 text-2xl font-semibold tracking-tight text-zinc-950 sm:text-4xl">
              Exchange wallet intelligence for early listing signals.
            </h1>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-zinc-500 sm:text-base">
              Tracks exchange wallets, detects tokens that are not listed on that exchange yet, scores listing signals, and sends alerts for high-confidence candidates.
            </p>
            <div className="mt-3 flex flex-wrap gap-2 text-xs text-zinc-500">
              <a className="rounded-full border border-zinc-200 bg-white px-3 py-1 hover:bg-zinc-50" href="mailto:jose@joseruao.com">
                jose@joseruao.com
              </a>
              <a className="rounded-full border border-zinc-200 bg-white px-3 py-1 hover:bg-zinc-50" href="https://github.com/joseruao/vigia-crypto" target="_blank" rel="noopener noreferrer">
                GitHub
              </a>
              <span className="rounded-full border border-zinc-200 bg-white px-3 py-1">Telegram alerts</span>
            </div>
          </div>
          <button
            type="button"
            onClick={() => onAsk('Que tokens as exchanges estao a acumular que ainda nao foram listados?')}
            className="inline-flex items-center justify-center gap-2 rounded-xl bg-zinc-950 px-4 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-zinc-800"
          >
            Abrir radar
            <Search className="h-4 w-4" />
          </button>
        </div>

        <div className="mb-5 grid grid-cols-3 gap-2 sm:mb-6 sm:max-w-xl sm:gap-3">
          {stats.map((s) => (
            <div key={s.label} className="rounded-2xl border border-zinc-200 bg-white px-3 py-3 shadow-sm">
              <div className="text-[10px] uppercase tracking-wide text-zinc-400">{s.label}</div>
              <div className="mt-1 text-lg font-semibold text-zinc-950">{s.value}</div>
            </div>
          ))}
        </div>

        <div className="grid gap-4 lg:grid-cols-[1.35fr_0.9fr]">
          <section className="rounded-2xl border border-zinc-200 bg-white p-3 shadow-sm sm:p-4">
            <div className="mb-3 flex items-center justify-between gap-3">
              <div>
                <h2 className="text-sm font-bold uppercase tracking-wide text-zinc-800">Possiveis listings</h2>
                <p className="mt-1 text-xs text-zinc-500">Apenas tokens ainda nao listados na propria exchange.</p>
              </div>
              <button
                type="button"
                onClick={() => onAsk('ver mais listings')}
                className="rounded-lg border border-zinc-200 px-3 py-1.5 text-xs font-semibold text-zinc-700 hover:bg-zinc-50"
              >
                Ver mais
              </button>
            </div>

            {loading ? (
              <div className="rounded-xl bg-zinc-50 p-4 text-sm text-zinc-500">
                {slowWakeup ? 'The backend may take a few seconds to wake up on the first request.' : 'A carregar sinais...'}
              </div>
            ) : predictions.length === 0 ? (
              <div className="rounded-xl bg-zinc-50 p-4 text-sm text-zinc-500">Sem sinais ativos neste momento.</div>
            ) : (
              <div className="grid gap-3 sm:grid-cols-2">
                {predictions.slice(0, 4).map((item) => {
                  const score = Math.round(item.score || 0);
                  return (
                    <article key={`${item.token}-${item.exchange}-${item.chain}`} className="rounded-2xl border border-zinc-200 bg-linear-to-br from-white to-zinc-50 p-4 shadow-sm">
                      <div className="flex items-start justify-between gap-3">
                        <div className="min-w-0">
                          <div className="truncate text-lg font-black text-zinc-950">{item.token}</div>
                          <div className="mt-0.5 text-xs text-zinc-500">
                            {displayExchange(item.exchange)} · {chainLabel(item.chain)}
                          </div>
                        </div>
                        <div className="rounded-xl border border-blue-200 bg-blue-50 px-2.5 py-2 text-center text-blue-700">
                          <div className="text-sm font-black leading-none">{score}/100</div>
                          <div className="mt-1 text-[10px] font-semibold">{verdict(item.score)}</div>
                        </div>
                      </div>

                      <div className="mt-4 grid grid-cols-3 gap-2">
                        <div className="rounded-xl bg-white px-2 py-2 ring-1 ring-zinc-100">
                          <div className="text-[9px] uppercase text-zinc-400">Wallet</div>
                          <div className="truncate text-xs font-semibold text-zinc-800">{compactUsd(item.value_usd)}</div>
                        </div>
                        <div className="rounded-xl bg-white px-2 py-2 ring-1 ring-zinc-100">
                          <div className="text-[9px] uppercase text-zinc-400">Liquidez</div>
                          <div className="truncate text-xs font-semibold text-zinc-800">{compactUsd(item.liquidity)}</div>
                        </div>
                        <div className="rounded-xl bg-white px-2 py-2 ring-1 ring-zinc-100">
                          <div className="text-[9px] uppercase text-zinc-400">Volume</div>
                          <div className="truncate text-xs font-semibold text-zinc-800">{compactUsd(item.volume_24h)}</div>
                        </div>
                      </div>

                      <div className="mt-3 flex flex-wrap gap-2">
                        {item.pair_url ? (
                          <a href={item.pair_url} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 rounded-full bg-emerald-50 px-2.5 py-1 text-xs font-semibold text-emerald-700">
                            DexScreener <ExternalLink className="h-3 w-3" />
                          </a>
                        ) : null}
                        <a href={coingeckoUrl(item.token)} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 rounded-full bg-zinc-100 px-2.5 py-1 text-xs font-semibold text-zinc-700">
                          CoinGecko <ExternalLink className="h-3 w-3" />
                        </a>
                      </div>
                    </article>
                  );
                })}
              </div>
            )}
          </section>

          <section className="rounded-2xl border border-zinc-200 bg-white p-3 shadow-sm sm:p-4">
            <div className="mb-3 flex items-center justify-between gap-3">
              <div>
                <h2 className="text-sm font-bold uppercase tracking-wide text-zinc-800">Top100 hoje</h2>
                <p className="mt-1 text-xs text-zinc-500">Setups perto de suporte com score tecnico.</p>
              </div>
              <LineChart className="h-5 w-5 text-zinc-400" />
            </div>

            {loading ? (
              <div className="rounded-xl bg-zinc-50 p-4 text-sm text-zinc-500">
                {slowWakeup ? 'The backend may take a few seconds to wake up on the first request.' : 'A carregar ranking...'}
              </div>
            ) : top100.length === 0 ? (
              <div className="rounded-xl bg-zinc-50 p-4 text-sm text-zinc-500">Sem ranking top100 disponivel.</div>
            ) : (
              <div className="space-y-2">
                {top100.map((coin) => (
                  <button
                    key={coin.symbol}
                    type="button"
                    onClick={() => onAsk(`analisa ${coin.symbol}`)}
                    className="w-full rounded-xl border border-zinc-200 bg-white p-3 text-left transition hover:border-zinc-300 hover:bg-zinc-50"
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <div className="text-sm font-bold text-zinc-950">{coin.symbol}</div>
                        <div className="text-xs text-zinc-500">{coin.name || coin.symbol}</div>
                      </div>
                      <div className="text-right">
                        <div className="text-sm font-semibold text-zinc-950">{compactUsd(coin.price)}</div>
                        <div className="text-[10px] text-zinc-500">score {Math.round(coin.score || 0)}/100</div>
                      </div>
                    </div>
                    <div className="mt-2 flex items-center gap-1.5 text-xs text-zinc-600">
                      <ShieldCheck className="h-3.5 w-3.5 text-emerald-600" />
                      <span className="line-clamp-1">{top100Reason(coin)}</span>
                    </div>
                  </button>
                ))}
              </div>
            )}
          </section>
        </div>
      </div>
    </div>
  );
}
