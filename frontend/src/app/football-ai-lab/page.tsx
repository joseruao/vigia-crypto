'use client';

import type { ReactNode } from 'react';
import { useEffect, useState } from 'react';
import {
  AlertTriangle,
  ChevronDown,
  ClipboardList,
  Loader2,
  ShieldAlert,
  Sparkles,
  Target,
  Trophy,
  Users,
  Zap,
} from 'lucide-react';
import { MatchPrepReport, generateMatchPrep, fetchSerieATeams } from '@/lib/api';

function SectionCard({ title, icon, children }: { title: string; icon: ReactNode; children: ReactNode }) {
  return (
    <section className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
      <div className="mb-3 flex items-center gap-2 text-slate-950">
        <span className="flex h-8 w-8 items-center justify-center rounded-md bg-emerald-50 text-emerald-700">
          {icon}
        </span>
        <h2 className="text-sm font-semibold uppercase tracking-wide">{title}</h2>
      </div>
      {children}
    </section>
  );
}

function BulletList({ items }: { items: string[] }) {
  if (!items.length) {
    return <p className="text-sm leading-6 text-slate-500">No data available.</p>;
  }
  return (
    <ul className="space-y-2 text-sm leading-6 text-slate-700">
      {items.map((item, i) => (
        <li key={i} className="flex gap-2">
          <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-emerald-600" />
          <span>{item}</span>
        </li>
      ))}
    </ul>
  );
}

function TeamSelect({
  label,
  value,
  onChange,
  teams,
  placeholder,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  teams: string[];
  placeholder: string;
}) {
  return (
    <label className="block">
      <span className="mb-1.5 block text-sm font-medium text-slate-700">{label}</span>
      <div className="relative">
        <select
          value={value}
          onChange={(e) => onChange(e.target.value)}
          className="h-11 w-full appearance-none rounded-md border border-slate-300 bg-white px-3 pr-9 text-sm text-slate-950 outline-none transition focus:border-emerald-600 focus:ring-2 focus:ring-emerald-100"
        >
          <option value="">{placeholder}</option>
          {teams.map((t) => (
            <option key={t} value={t}>{t}</option>
          ))}
        </select>
        <ChevronDown className="pointer-events-none absolute right-3 top-3 h-4 w-4 text-slate-400" />
      </div>
    </label>
  );
}

export default function FootballAiLabPage() {
  const [teams, setTeams] = useState<string[]>([]);
  const [myTeam, setMyTeam] = useState('');
  const [opponentTeam, setOpponentTeam] = useState('');
  const [extraNotes, setExtraNotes] = useState('');
  const [report, setReport] = useState<MatchPrepReport | null>(null);
  const [loading, setLoading] = useState(false);
  const [loadingTeams, setLoadingTeams] = useState(true);
  const [error, setError] = useState('');
  const [showRaw, setShowRaw] = useState(false);

  useEffect(() => {
    fetchSerieATeams()
      .then(setTeams)
      .finally(() => setLoadingTeams(false));
  }, []);

  async function handleGenerate() {
    if (!myTeam || !opponentTeam || loading) return;
    if (myTeam === opponentTeam) {
      setError('Select two different teams.');
      return;
    }
    setLoading(true);
    setError('');
    setReport(null);

    try {
      const result = await generateMatchPrep({
        my_team: myTeam,
        opponent_team: opponentTeam,
        extra_notes: extraNotes.trim(),
      });
      setReport(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not generate the report.');
    } finally {
      setLoading(false);
    }
  }

  const canSubmit = myTeam.length > 0 && opponentTeam.length > 0 && myTeam !== opponentTeam;

  return (
    <main className="min-h-screen bg-slate-50 text-slate-950">
      <div className="mx-auto flex w-full max-w-7xl flex-col gap-6 px-4 py-6 sm:px-6 lg:px-8">
        <header className="border-b border-slate-200 pb-5">
          <p className="text-xs font-semibold uppercase tracking-wide text-emerald-700">Experimental module</p>
          <h1 className="mt-2 text-3xl font-semibold tracking-normal text-slate-950">Football AI Lab</h1>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-600">
            Match preparation reports for Campeonato Brasileiro Série A — powered by live ESPN data.
          </p>
        </header>

        <div className="grid gap-6 xl:grid-cols-[380px_1fr]">
          {/* --- Input panel --- */}
          <section className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
            <div className="mb-5 flex items-center gap-2">
              <span className="flex h-8 w-8 items-center justify-center rounded-md bg-slate-100 text-slate-700">
                <Target className="h-4 w-4" />
              </span>
              <h2 className="text-base font-semibold">Match Setup</h2>
            </div>

            <div className="space-y-4">
              {loadingTeams ? (
                <div className="flex items-center gap-2 py-4 text-sm text-slate-500">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Loading Série A teams…
                </div>
              ) : (
                <>
                  <TeamSelect
                    label="My team"
                    value={myTeam}
                    onChange={setMyTeam}
                    teams={teams}
                    placeholder="Select your team"
                  />
                  <TeamSelect
                    label="Opponent"
                    value={opponentTeam}
                    onChange={setOpponentTeam}
                    teams={teams.filter((t) => t !== myTeam)}
                    placeholder="Select opponent"
                  />
                </>
              )}

              <label className="block">
                <span className="mb-1.5 block text-sm font-medium text-slate-700">
                  Extra coach notes <span className="font-normal text-slate-400">(optional)</span>
                </span>
                <textarea
                  value={extraNotes}
                  onChange={(e) => setExtraNotes(e.target.value)}
                  placeholder="Add context not in the data — injuries, tactical adjustments, last training observations..."
                  rows={5}
                  className="w-full resize-y rounded-md border border-slate-300 bg-white px-3 py-2 text-sm leading-6 text-slate-950 outline-none transition placeholder:text-slate-400 focus:border-emerald-600 focus:ring-2 focus:ring-emerald-100"
                />
              </label>

              {error && (
                <div className="flex gap-2 rounded-md border border-red-200 bg-red-50 p-3 text-sm leading-5 text-red-700">
                  <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
                  <span>{error}</span>
                </div>
              )}

              <button
                type="button"
                onClick={handleGenerate}
                disabled={!canSubmit || loading}
                className="inline-flex h-11 w-full items-center justify-center gap-2 rounded-md bg-emerald-700 px-4 text-sm font-semibold text-white shadow-sm transition hover:bg-emerald-800 disabled:cursor-not-allowed disabled:bg-slate-300"
              >
                {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
                {loading ? 'Generating report…' : 'Generate Match Prep Report'}
              </button>
            </div>
          </section>

          {/* --- Report panel --- */}
          <section className="min-h-[640px] rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
            {!report ? (
              <div className="flex h-full min-h-[560px] flex-col items-center justify-center text-center">
                <div className="flex h-14 w-14 items-center justify-center rounded-lg bg-emerald-50 text-emerald-700">
                  <Trophy className="h-7 w-7" />
                </div>
                <h2 className="mt-4 text-xl font-semibold">Match preparation report</h2>
                <p className="mt-2 max-w-md text-sm leading-6 text-slate-500">
                  Select your team and the opponent. The report is generated from live Série A data — no manual data entry needed.
                </p>
              </div>
            ) : (
              <div className="space-y-5">
                {/* Header */}
                <div className="rounded-lg bg-slate-950 p-6 text-white">
                  <p className="text-xs font-semibold uppercase tracking-wide text-emerald-300">Match Preparation</p>
                  <h2 className="mt-1 text-xl font-semibold">
                    {report.my_team} <span className="text-slate-400">vs</span> {report.opponent_team}
                  </h2>
                  <p className="mt-4 max-w-3xl text-sm leading-6 text-slate-200">{report.executive_summary}</p>
                  <p className="mt-3 text-xs text-slate-500">Source: {report.data_source}</p>
                </div>

                {/* Opponent analysis */}
                <div className="grid gap-5 lg:grid-cols-2">
                  <SectionCard title="Opponent Strengths" icon={<Zap className="h-4 w-4" />}>
                    <BulletList items={report.opponent_strengths} />
                  </SectionCard>
                  <SectionCard title="Opponent Weaknesses" icon={<ShieldAlert className="h-4 w-4" />}>
                    <BulletList items={report.opponent_weaknesses} />
                  </SectionCard>
                </div>

                <SectionCard title="Key Threats to Neutralise" icon={<Users className="h-4 w-4" />}>
                  <BulletList items={report.key_threats} />
                </SectionCard>

                {/* Game plan */}
                <SectionCard title="Tactical Approach" icon={<ClipboardList className="h-4 w-4" />}>
                  <p className="text-sm leading-6 text-slate-700">{report.tactical_approach}</p>
                </SectionCard>

                <div className="grid gap-5 lg:grid-cols-2">
                  <SectionCard title="Pressing Triggers" icon={<Target className="h-4 w-4" />}>
                    <BulletList items={report.pressing_triggers} />
                  </SectionCard>
                  <SectionCard title="Attacking Approach" icon={<Zap className="h-4 w-4" />}>
                    <BulletList items={report.attacking_approach} />
                  </SectionCard>
                </div>

                <div className="grid gap-5 lg:grid-cols-2">
                  <SectionCard title="Set Pieces" icon={<Trophy className="h-4 w-4" />}>
                    <BulletList items={report.set_piece_plan} />
                  </SectionCard>
                  <SectionCard title="Risk Assessment" icon={<AlertTriangle className="h-4 w-4" />}>
                    <p className="text-sm leading-6 text-slate-700">{report.risk_assessment}</p>
                  </SectionCard>
                </div>

                {/* Raw data toggle */}
                <button
                  type="button"
                  onClick={() => setShowRaw((v) => !v)}
                  className="text-xs text-slate-400 underline hover:text-slate-600"
                >
                  {showRaw ? 'Hide raw data' : 'Show raw data used'}
                </button>
                {showRaw && (
                  <pre className="overflow-x-auto rounded-md bg-slate-900 p-4 text-xs leading-5 text-slate-300">
                    {report.raw_stats_used}
                  </pre>
                )}
              </div>
            )}
          </section>
        </div>
      </div>
    </main>
  );
}
