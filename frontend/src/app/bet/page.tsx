'use client';

import { useEffect, useState } from 'react';
import { AlertTriangle, Loader2, RefreshCw, TrendingUp, Info } from 'lucide-react';
import { BetBoard, BetEdge, BetMatch, fetchBetBoard } from '@/lib/api';

const MARKET_LABEL: Record<string, string> = {
  goals: 'Goals',
  corners: 'Corners',
  cards: 'Cards',
};
const MARKET_COLOR: Record<string, string> = {
  goals: 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30',
  corners: 'bg-sky-500/15 text-sky-300 border-sky-500/30',
  cards: 'bg-amber-500/15 text-amber-300 border-amber-500/30',
};

function pct(x: number) {
  return `${(x * 100).toFixed(0)}%`;
}

function kickoff(iso: string) {
  try {
    return new Date(iso).toLocaleString(undefined, {
      weekday: 'short', day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit',
    });
  } catch {
    return iso;
  }
}

function PickRow({ e }: { e: BetEdge }) {
  return (
    <div className={`flex flex-wrap items-center gap-x-3 gap-y-1 py-2.5 px-3 rounded-lg text-sm ${
      e.best ? 'bg-emerald-500/[0.08] border border-emerald-500/25' : 'border-b border-white/5'
    }`}>
      <span className={`px-2 py-0.5 rounded border text-xs font-medium ${MARKET_COLOR[e.market] ?? 'bg-white/10 text-white/70 border-white/20'}`}>
        {MARKET_LABEL[e.market] ?? e.market}
      </span>
      {e.best && (
        <span className="px-1.5 py-0.5 rounded bg-emerald-500/20 text-emerald-300 text-[10px] font-semibold uppercase tracking-wide">
          Top pick
        </span>
      )}
      <span className="font-semibold text-white capitalize w-24">
        {e.side} {e.line}
      </span>
      <span className="text-white/90">@ {e.odd.toFixed(2)}</span>
      <span className="text-white/40 text-xs">{e.book}</span>
      <span className="ml-auto flex items-center gap-3">
        <span className="text-white/60 text-xs">
          model <b className="text-white/90">{pct(e.model_prob)}</b> vs fair {pct(e.fair_prob)}
        </span>
        <span className="text-emerald-400 font-semibold flex items-center gap-1">
          <TrendingUp size={14} /> {pct(e.edge)}
        </span>
      </span>
      {e.warning && (
        <span className="w-full flex items-center gap-1.5 text-amber-400/80 text-xs">
          <AlertTriangle size={12} /> {e.warning}
        </span>
      )}
    </div>
  );
}

function MatchCard({ m }: { m: BetMatch }) {
  const unresolved = !m.home_resolved || !m.away_resolved;
  const collapsed = m.candidates - m.picks.length;
  return (
    <div className="rounded-xl border border-white/10 bg-white/[0.03] p-4">
      <div className="flex items-center justify-between mb-1">
        <h3 className="font-semibold text-white">{m.home} <span className="text-white/40">vs</span> {m.away}</h3>
        <span className="text-xs text-white/40">{kickoff(m.commence)}</span>
      </div>
      <div className="text-xs text-white/40 mb-3">
        history sample: {m.min_games} game{m.min_games === 1 ? '' : 's'} per team
        {unresolved && <span className="text-amber-400/80"> · one team unresolved — no model</span>}
      </div>
      {m.picks.length === 0 ? (
        <p className="text-sm text-white/40">No positive-edge bets.</p>
      ) : (
        <div className="space-y-1.5">
          {m.picks.map((e, i) => <PickRow key={i} e={e} />)}
          {collapsed > 0 && (
            <p className="text-[11px] text-white/30 pt-1">
              best line per market shown · {collapsed} weaker candidate{collapsed === 1 ? '' : 's'} hidden
            </p>
          )}
        </div>
      )}
    </div>
  );
}

export default function BetPage() {
  const [board, setBoard] = useState<BetBoard | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      setBoard(await fetchBetBoard(48));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, []);

  return (
    <main className="min-h-screen bg-[#0a0e14] text-white px-4 py-8 md:px-8">
      <div className="max-w-3xl mx-auto">
        <header className="mb-6">
          <h1 className="text-2xl font-bold flex items-center gap-2">
            ⚽ Football Bet <span className="text-sm font-normal text-white/40">value board</span>
          </h1>
          <p className="text-white/50 text-sm mt-1">
            Where our data-derived estimate disagrees with the bookmaker&apos;s price.
          </p>
        </header>

        {/* Honest framing banner */}
        <div className="rounded-xl border border-amber-500/30 bg-amber-500/[0.07] p-4 mb-6 text-sm text-amber-200/90 flex gap-3">
          <Info size={18} className="shrink-0 mt-0.5" />
          <p>
            <b>Informational tool, not financial advice — and not guaranteed winners.</b>{' '}
            During the World Cup, team histories are tiny (1–3 games), so almost every
            row is flagged as thin-sample noise. Corners/cards come mostly from Pinnacle
            (a sharp book), so real edges there are rare. This finds divergences and
            demands discipline; it does not promise profit. Bet responsibly.
          </p>
        </div>

        <div className="flex items-center justify-between mb-4">
          <div className="text-xs text-white/40">
            {board && (
              <>
                {board.matches.length} matches · {board.total_value_rows} value rows ·
                {' '}{board.credits_remaining ?? '?'} API credits left
              </>
            )}
          </div>
          <button
            onClick={load}
            disabled={loading}
            className="flex items-center gap-1.5 text-sm px-3 py-1.5 rounded-lg border border-white/15 hover:bg-white/5 disabled:opacity-50"
          >
            {loading ? <Loader2 size={14} className="animate-spin" /> : <RefreshCw size={14} />}
            Refresh
          </button>
        </div>

        {error && (
          <div className="rounded-xl border border-red-500/30 bg-red-500/[0.07] p-4 text-red-300 text-sm">
            {error}
            {error.toLowerCase().includes('odds_api_key') && (
              <p className="mt-2 text-red-300/70">
                The server is missing ODDS_API_KEY. Add it to the Railway environment.
              </p>
            )}
          </div>
        )}

        {loading && !board && (
          <div className="flex items-center gap-2 text-white/50 py-12 justify-center">
            <Loader2 className="animate-spin" /> Scanning fixtures…
          </div>
        )}

        {board && !loading && board.matches.length === 0 && (
          <p className="text-white/50 py-8 text-center">
            No fixtures kicking off in the next {board.hours_ahead}h.
          </p>
        )}

        <div className="space-y-4">
          {board?.matches.map((m, i) => <MatchCard key={i} m={m} />)}
        </div>

        <footer className="mt-8 text-xs text-white/30">
          Source: {board?.source ?? 'The Odds API + ESPN'}. Cached ~30 min.
          18+. Gamble responsibly.
        </footer>
      </div>
    </main>
  );
}
