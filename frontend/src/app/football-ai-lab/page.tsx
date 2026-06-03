'use client';

import type { ReactNode } from 'react';
import { useMemo, useState } from 'react';
import {
  AlertTriangle,
  ClipboardList,
  Loader2,
  ShieldAlert,
  Sparkles,
  Target,
  Trophy,
  Users,
  Zap,
} from 'lucide-react';
import {
  FootballAnalysisReport,
  analyzeFootballOpponent,
} from '@/lib/api';

function SectionCard({
  title,
  icon,
  children,
}: {
  title: string;
  icon: ReactNode;
  children: ReactNode;
}) {
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
    return <p className="text-sm leading-6 text-slate-500">No clear signal found in the supplied notes.</p>;
  }

  return (
    <ul className="space-y-2 text-sm leading-6 text-slate-700">
      {items.map((item, index) => (
        <li key={`${item}-${index}`} className="flex gap-2">
          <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-emerald-600" />
          <span>{item}</span>
        </li>
      ))}
    </ul>
  );
}

export default function FootballAiLabPage() {
  const [teamName, setTeamName] = useState('');
  const [stats, setStats] = useState('');
  const [observations, setObservations] = useState('');
  const [report, setReport] = useState<FootballAnalysisReport | null>(null);
  const [reportedTeam, setReportedTeam] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const canSubmit = useMemo(() => {
    return teamName.trim().length > 0 && (stats.trim().length > 0 || observations.trim().length > 0);
  }, [teamName, stats, observations]);

  async function handleGenerate() {
    if (!canSubmit || loading) return;
    setLoading(true);
    setError('');

    try {
      const result = await analyzeFootballOpponent({
        team_name: teamName.trim(),
        stats: stats.trim(),
        observations: observations.trim(),
      });
      setReport(result.report);
      setReportedTeam(result.team_name);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Could not generate the report.';
      setError(message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="min-h-screen bg-slate-50 text-slate-950">
      <div className="mx-auto flex w-full max-w-7xl flex-col gap-6 px-4 py-6 sm:px-6 lg:px-8">
        <header className="border-b border-slate-200 pb-5">
          <div>
            <div>
              <p className="text-xs font-semibold uppercase tracking-wide text-emerald-700">Experimental module</p>
              <h1 className="mt-2 text-3xl font-semibold tracking-normal text-slate-950">Football AI Lab</h1>
              <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-600">
                Turn coach notes and match stats into a structured opposition report for tactical preparation.
              </p>
            </div>
          </div>
        </header>

        <div className="grid gap-6 xl:grid-cols-[420px_1fr]">
          <section className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
            <div className="mb-5 flex items-center gap-2">
              <span className="flex h-8 w-8 items-center justify-center rounded-md bg-slate-100 text-slate-700">
                <Target className="h-4 w-4" />
              </span>
              <h2 className="text-base font-semibold">Opponent Inputs</h2>
            </div>

            <div className="space-y-4">
              <label className="block">
                <span className="mb-1.5 block text-sm font-medium text-slate-700">Team name</span>
                <input
                  value={teamName}
                  onChange={(event) => setTeamName(event.target.value)}
                  placeholder="e.g. Sporting CP U19"
                  className="h-11 w-full rounded-md border border-slate-300 bg-white px-3 text-sm text-slate-950 outline-none transition placeholder:text-slate-400 focus:border-emerald-600 focus:ring-2 focus:ring-emerald-100"
                />
              </label>

              <label className="block">
                <span className="mb-1.5 block text-sm font-medium text-slate-700">Statistics</span>
                <textarea
                  value={stats}
                  onChange={(event) => setStats(event.target.value)}
                  placeholder="Paste metrics, formations, event notes, recent results..."
                  rows={8}
                  className="w-full resize-y rounded-md border border-slate-300 bg-white px-3 py-2 text-sm leading-6 text-slate-950 outline-none transition placeholder:text-slate-400 focus:border-emerald-600 focus:ring-2 focus:ring-emerald-100"
                />
              </label>

              <label className="block">
                <span className="mb-1.5 block text-sm font-medium text-slate-700">Raw match observations</span>
                <textarea
                  value={observations}
                  onChange={(event) => setObservations(event.target.value)}
                  placeholder="Describe build-up, pressing, transitions, key players, set pieces..."
                  rows={10}
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
                Generate Report
              </button>
            </div>
          </section>

          <section className="min-h-[640px] rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
            {!report ? (
              <div className="flex h-full min-h-[560px] flex-col items-center justify-center text-center">
                <div className="flex h-14 w-14 items-center justify-center rounded-lg bg-emerald-50 text-emerald-700">
                  <Trophy className="h-7 w-7" />
                </div>
                <h2 className="mt-4 text-xl font-semibold">Opponent report preview</h2>
                <p className="mt-2 max-w-md text-sm leading-6 text-slate-500">
                  Add a team name plus observations or stats, then generate a professional tactical report.
                </p>
              </div>
            ) : (
              <div className="space-y-5">
                <div className="rounded-lg bg-slate-950 p-6 text-white">
                  <p className="text-xs font-semibold uppercase tracking-wide text-emerald-300">Opponent Analysis</p>
                  <h2 className="mt-2 text-2xl font-semibold">{reportedTeam}</h2>
                  <p className="mt-4 max-w-3xl text-sm leading-6 text-slate-200">{report.executive_summary}</p>
                </div>

                <div className="grid gap-5 lg:grid-cols-2">
                  <SectionCard title="Tactical Strengths" icon={<Zap className="h-4 w-4" />}>
                    <BulletList items={report.tactical_strengths} />
                  </SectionCard>
                  <SectionCard title="Tactical Weaknesses" icon={<ShieldAlert className="h-4 w-4" />}>
                    <BulletList items={report.tactical_weaknesses} />
                  </SectionCard>
                  <SectionCard title="Key Players To Watch" icon={<Users className="h-4 w-4" />}>
                    <BulletList items={report.key_players_to_watch} />
                  </SectionCard>
                  <SectionCard title="Pressing Recommendations" icon={<Target className="h-4 w-4" />}>
                    <BulletList items={report.pressing_recommendations} />
                  </SectionCard>
                </div>

                <SectionCard title="Recommended Match Strategy" icon={<ClipboardList className="h-4 w-4" />}>
                  <p className="text-sm leading-6 text-slate-700">{report.recommended_match_strategy}</p>
                </SectionCard>

                <div className="grid gap-5 lg:grid-cols-2">
                  <SectionCard title="Set Piece Considerations" icon={<Trophy className="h-4 w-4" />}>
                    <BulletList items={report.set_piece_considerations} />
                  </SectionCard>
                  <SectionCard title="Risk Assessment" icon={<AlertTriangle className="h-4 w-4" />}>
                    <p className="text-sm leading-6 text-slate-700">{report.risk_assessment}</p>
                  </SectionCard>
                </div>
              </div>
            )}
          </section>
        </div>
      </div>
    </main>
  );
}
