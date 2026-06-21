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
import {
  MatchPrepReport,
  OpponentScoutReport,
  generateMatchPrep,
  generateOpponentScout,
  fetchSerieATeams,
} from '@/lib/api';

type Mode = 'match' | 'scout';
type Lang = 'en' | 'pt';

const t = {
  en: {
    title: 'Football AI Lab',
    subtitle: 'Match preparation reports for Campeonato Brasileiro Série A — powered by live ESPN data.',
    modeMatch: 'Match Prep',
    modeScout: 'Opponent Scout',
    modeMatchDesc: 'Game plan for an upcoming fixture between two teams.',
    modeScoutDesc: 'Deep standalone analysis of a single opponent.',
    myTeam: 'My team',
    opponent: 'Opponent',
    teamToScout: 'Team to scout',
    selectMyTeam: 'Select your team',
    selectOpponent: 'Select opponent',
    selectTeam: 'Select a team',
    extraNotes: 'Extra coach notes',
    extraNotesHint: 'optional',
    extraPlaceholderMatch: 'Injuries, tactical adjustments, last training observations...',
    extraPlaceholderScout: 'Add context — known injuries, recent transfers, rivalry history...',
    loading: 'Loading Série A teams…',
    generate: 'Generate Report',
    generating: 'Generating report…',
    differentTeams: 'Select two different teams.',
    emptyState: 'Select teams and generate a report.',
    emptyStateSub: 'Live Série A data — no manual data entry needed.',
    showRaw: 'Show raw data used',
    hideRaw: 'Hide raw data',
    source: 'Source',
    matchPrep: 'Match Preparation',
    opponentScout: 'Opponent Scout',
    execSummary: 'Executive Summary',
    oppStrengths: 'Opponent Strengths',
    oppWeaknesses: 'Opponent Weaknesses',
    keyThreats: 'Key Threats to Neutralise',
    tacticalApproach: 'Tactical Approach',
    pressingTriggers: 'Pressing Triggers',
    attackingApproach: 'Attacking Approach',
    setPieces: 'Set Pieces',
    riskAssessment: 'Risk Assessment',
    playingStyle: 'Playing Style',
    strengths: 'Strengths',
    weaknesses: 'Weaknesses',
    keyPatterns: 'Key Patterns',
    howToBeat: 'How to Beat Them',
    pressingVuln: 'Pressing Vulnerabilities',
    setPieceTend: 'Set Piece Tendencies',
    formAnalysis: 'Form Analysis',
    vs: 'vs',
  },
  pt: {
    title: 'Football AI Lab',
    subtitle: 'Relatórios de preparação para o Campeonato Brasileiro Série A — dados ESPN em tempo real.',
    modeMatch: 'Preparação de Jogo',
    modeScout: 'Scout Adversário',
    modeMatchDesc: 'Plano de jogo para o próximo confronto entre duas equipas.',
    modeScoutDesc: 'Análise aprofundada de uma única equipa adversária.',
    myTeam: 'A minha equipa',
    opponent: 'Adversário',
    teamToScout: 'Equipa a analisar',
    selectMyTeam: 'Selecionar a minha equipa',
    selectOpponent: 'Selecionar adversário',
    selectTeam: 'Selecionar equipa',
    extraNotes: 'Notas extra do treinador',
    extraNotesHint: 'opcional',
    extraPlaceholderMatch: 'Lesões, ajustes tácticos, observações do último treino...',
    extraPlaceholderScout: 'Contexto adicional — lesões conhecidas, transferências recentes...',
    loading: 'A carregar equipas da Série A…',
    generate: 'Gerar Relatório',
    generating: 'A gerar relatório…',
    differentTeams: 'Selecione duas equipas diferentes.',
    emptyState: 'Selecione as equipas e gere um relatório.',
    emptyStateSub: 'Dados da Série A em tempo real — sem necessidade de entrada manual.',
    showRaw: 'Ver dados brutos utilizados',
    hideRaw: 'Ocultar dados brutos',
    source: 'Fonte',
    matchPrep: 'Preparação de Jogo',
    opponentScout: 'Scout Adversário',
    execSummary: 'Sumário Executivo',
    oppStrengths: 'Pontos Fortes do Adversário',
    oppWeaknesses: 'Pontos Fracos do Adversário',
    keyThreats: 'Ameaças a Neutralizar',
    tacticalApproach: 'Abordagem Táctica',
    pressingTriggers: 'Gatilhos de Pressão',
    attackingApproach: 'Abordagem Ofensiva',
    setPieces: 'Bolas Paradas',
    riskAssessment: 'Avaliação de Risco',
    playingStyle: 'Estilo de Jogo',
    strengths: 'Pontos Fortes',
    weaknesses: 'Pontos Fracos',
    keyPatterns: 'Padrões Identificados',
    howToBeat: 'Como Bater Esta Equipa',
    pressingVuln: 'Vulnerabilidades à Pressão',
    setPieceTend: 'Tendências em Bolas Paradas',
    formAnalysis: 'Análise de Forma',
    vs: 'vs',
  },
} as const;

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
  if (!items.length) return <p className="text-sm leading-6 text-slate-500">—</p>;
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

function TeamSelect({ label, value, onChange, teams, placeholder }: {
  label: string; value: string; onChange: (v: string) => void;
  teams: string[]; placeholder: string;
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
          {teams.map((team) => <option key={team} value={team}>{team}</option>)}
        </select>
        <ChevronDown className="pointer-events-none absolute right-3 top-3 h-4 w-4 text-slate-400" />
      </div>
    </label>
  );
}

export default function FootballAiLabPage() {
  const [teams, setTeams] = useState<string[]>([]);
  const [mode, setMode] = useState<Mode>('match');
  const [lang, setLang] = useState<Lang>('en');
  const [myTeam, setMyTeam] = useState('');
  const [opponentTeam, setOpponentTeam] = useState('');
  const [scoutTeam, setScoutTeam] = useState('');
  const [extraNotes, setExtraNotes] = useState('');
  const [matchReport, setMatchReport] = useState<MatchPrepReport | null>(null);
  const [scoutReport, setScoutReport] = useState<OpponentScoutReport | null>(null);
  const [loading, setLoading] = useState(false);
  const [loadingTeams, setLoadingTeams] = useState(true);
  const [error, setError] = useState('');
  const [showRaw, setShowRaw] = useState(false);

  const T = t[lang];

  useEffect(() => {
    fetchSerieATeams().then(setTeams).finally(() => setLoadingTeams(false));
  }, []);

  async function handleGenerate() {
    if (loading) return;
    setLoading(true);
    setError('');
    setMatchReport(null);
    setScoutReport(null);
    setShowRaw(false);

    try {
      if (mode === 'match') {
        if (!myTeam || !opponentTeam) return;
        const r = await generateMatchPrep({ my_team: myTeam, opponent_team: opponentTeam, extra_notes: extraNotes, language: lang });
        setMatchReport(r);
      } else {
        if (!scoutTeam) return;
        const r = await generateOpponentScout({ team: scoutTeam, extra_notes: extraNotes, language: lang });
        setScoutReport(r);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not generate the report.');
    } finally {
      setLoading(false);
    }
  }

  const canSubmit = mode === 'match'
    ? myTeam.length > 0 && opponentTeam.length > 0 && myTeam !== opponentTeam
    : scoutTeam.length > 0;

  const hasReport = matchReport !== null || scoutReport !== null;

  return (
    <main className="min-h-screen bg-slate-50 text-slate-950">
      <div className="mx-auto flex w-full max-w-7xl flex-col gap-6 px-4 py-6 sm:px-6 lg:px-8">

        {/* Header */}
        <header className="flex items-start justify-between border-b border-slate-200 pb-5">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-emerald-700">Experimental module</p>
            <h1 className="mt-2 text-3xl font-semibold">{T.title}</h1>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-600">{T.subtitle}</p>
          </div>
          {/* Language toggle */}
          <button
            onClick={() => setLang(l => l === 'en' ? 'pt' : 'en')}
            className="mt-1 flex items-center gap-1.5 rounded-md border border-slate-300 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 shadow-sm transition hover:border-slate-400"
          >
            {lang === 'en' ? '🇬🇧 EN' : '🇵🇹 PT'}
          </button>
        </header>

        {/* Mode selector */}
        <div className="flex gap-3">
          {(['match', 'scout'] as Mode[]).map((m) => (
            <button
              key={m}
              onClick={() => { setMode(m); setMatchReport(null); setScoutReport(null); setError(''); }}
              className={`flex-1 rounded-lg border p-4 text-left transition ${
                mode === m
                  ? 'border-emerald-600 bg-emerald-50 text-emerald-900'
                  : 'border-slate-200 bg-white text-slate-700 hover:border-slate-300'
              }`}
            >
              <p className="text-sm font-semibold">{m === 'match' ? T.modeMatch : T.modeScout}</p>
              <p className="mt-0.5 text-xs text-slate-500">{m === 'match' ? T.modeMatchDesc : T.modeScoutDesc}</p>
            </button>
          ))}
        </div>

        <div className="grid gap-6 xl:grid-cols-[380px_1fr]">
          {/* Input panel */}
          <section className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
            <div className="mb-5 flex items-center gap-2">
              <span className="flex h-8 w-8 items-center justify-center rounded-md bg-slate-100 text-slate-700">
                <Target className="h-4 w-4" />
              </span>
              <h2 className="text-base font-semibold">{mode === 'match' ? T.modeMatch : T.modeScout}</h2>
            </div>

            <div className="space-y-4">
              {loadingTeams ? (
                <div className="flex items-center gap-2 py-4 text-sm text-slate-500">
                  <Loader2 className="h-4 w-4 animate-spin" /> {T.loading}
                </div>
              ) : mode === 'match' ? (
                <>
                  <TeamSelect label={T.myTeam} value={myTeam} onChange={setMyTeam} teams={teams} placeholder={T.selectMyTeam} />
                  <TeamSelect label={T.opponent} value={opponentTeam} onChange={setOpponentTeam} teams={teams.filter(t => t !== myTeam)} placeholder={T.selectOpponent} />
                </>
              ) : (
                <TeamSelect label={T.teamToScout} value={scoutTeam} onChange={setScoutTeam} teams={teams} placeholder={T.selectTeam} />
              )}

              <label className="block">
                <span className="mb-1.5 block text-sm font-medium text-slate-700">
                  {T.extraNotes} <span className="font-normal text-slate-400">({T.extraNotesHint})</span>
                </span>
                <textarea
                  value={extraNotes}
                  onChange={(e) => setExtraNotes(e.target.value)}
                  placeholder={mode === 'match' ? T.extraPlaceholderMatch : T.extraPlaceholderScout}
                  rows={5}
                  className="w-full resize-y rounded-md border border-slate-300 bg-white px-3 py-2 text-sm leading-6 text-slate-950 outline-none transition placeholder:text-slate-400 focus:border-emerald-600 focus:ring-2 focus:ring-emerald-100"
                />
              </label>

              {error && (
                <div className="flex gap-2 rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700">
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
                {loading ? T.generating : T.generate}
              </button>
            </div>
          </section>

          {/* Report panel */}
          <section className="min-h-[640px] rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
            {!hasReport ? (
              <div className="flex h-full min-h-[560px] flex-col items-center justify-center text-center">
                <div className="flex h-14 w-14 items-center justify-center rounded-lg bg-emerald-50 text-emerald-700">
                  <Trophy className="h-7 w-7" />
                </div>
                <h2 className="mt-4 text-xl font-semibold">{T.emptyState}</h2>
                <p className="mt-2 max-w-md text-sm leading-6 text-slate-500">{T.emptyStateSub}</p>
              </div>
            ) : matchReport ? (
              <div className="space-y-5">
                <div className="rounded-lg bg-slate-950 p-6 text-white">
                  <p className="text-xs font-semibold uppercase tracking-wide text-emerald-300">{T.matchPrep}</p>
                  <h2 className="mt-1 text-xl font-semibold">
                    {matchReport.my_team} <span className="text-slate-400">{T.vs}</span> {matchReport.opponent_team}
                  </h2>
                  <p className="mt-4 max-w-3xl text-sm leading-6 text-slate-200">{matchReport.executive_summary}</p>
                  <p className="mt-3 text-xs text-slate-500">{T.source}: {matchReport.data_source}</p>
                </div>

                <div className="grid gap-5 lg:grid-cols-2">
                  <SectionCard title={T.oppStrengths} icon={<Zap className="h-4 w-4" />}>
                    <BulletList items={matchReport.opponent_strengths} />
                  </SectionCard>
                  <SectionCard title={T.oppWeaknesses} icon={<ShieldAlert className="h-4 w-4" />}>
                    <BulletList items={matchReport.opponent_weaknesses} />
                  </SectionCard>
                </div>

                <SectionCard title={T.keyThreats} icon={<Users className="h-4 w-4" />}>
                  <BulletList items={matchReport.key_threats} />
                </SectionCard>

                <SectionCard title={T.tacticalApproach} icon={<ClipboardList className="h-4 w-4" />}>
                  <p className="text-sm leading-6 text-slate-700">{matchReport.tactical_approach}</p>
                </SectionCard>

                <div className="grid gap-5 lg:grid-cols-2">
                  <SectionCard title={T.pressingTriggers} icon={<Target className="h-4 w-4" />}>
                    <BulletList items={matchReport.pressing_triggers} />
                  </SectionCard>
                  <SectionCard title={T.attackingApproach} icon={<Zap className="h-4 w-4" />}>
                    <BulletList items={matchReport.attacking_approach} />
                  </SectionCard>
                </div>

                <div className="grid gap-5 lg:grid-cols-2">
                  <SectionCard title={T.setPieces} icon={<Trophy className="h-4 w-4" />}>
                    <BulletList items={matchReport.set_piece_plan} />
                  </SectionCard>
                  <SectionCard title={T.riskAssessment} icon={<AlertTriangle className="h-4 w-4" />}>
                    <p className="text-sm leading-6 text-slate-700">{matchReport.risk_assessment}</p>
                  </SectionCard>
                </div>

                <button onClick={() => setShowRaw(v => !v)} className="text-xs text-slate-400 underline hover:text-slate-600">
                  {showRaw ? T.hideRaw : T.showRaw}
                </button>
                {showRaw && <pre className="overflow-x-auto rounded-md bg-slate-900 p-4 text-xs leading-5 text-slate-300">{matchReport.raw_stats_used}</pre>}
              </div>
            ) : scoutReport ? (
              <div className="space-y-5">
                <div className="rounded-lg bg-slate-950 p-6 text-white">
                  <p className="text-xs font-semibold uppercase tracking-wide text-emerald-300">{T.opponentScout}</p>
                  <h2 className="mt-1 text-xl font-semibold">{scoutReport.team}</h2>
                  <p className="mt-4 max-w-3xl text-sm leading-6 text-slate-200">{scoutReport.executive_summary}</p>
                  <p className="mt-3 text-xs text-slate-500">{T.source}: {scoutReport.data_source}</p>
                </div>

                <SectionCard title={T.playingStyle} icon={<ClipboardList className="h-4 w-4" />}>
                  <p className="text-sm leading-6 text-slate-700">{scoutReport.playing_style}</p>
                </SectionCard>

                <div className="grid gap-5 lg:grid-cols-2">
                  <SectionCard title={T.strengths} icon={<Zap className="h-4 w-4" />}>
                    <BulletList items={scoutReport.strengths} />
                  </SectionCard>
                  <SectionCard title={T.weaknesses} icon={<ShieldAlert className="h-4 w-4" />}>
                    <BulletList items={scoutReport.weaknesses} />
                  </SectionCard>
                </div>

                <SectionCard title={T.keyPatterns} icon={<Target className="h-4 w-4" />}>
                  <BulletList items={scoutReport.key_patterns} />
                </SectionCard>

                <SectionCard title={T.howToBeat} icon={<Trophy className="h-4 w-4" />}>
                  <BulletList items={scoutReport.how_to_beat_them} />
                </SectionCard>

                <div className="grid gap-5 lg:grid-cols-2">
                  <SectionCard title={T.pressingVuln} icon={<Users className="h-4 w-4" />}>
                    <BulletList items={scoutReport.pressing_vulnerabilities} />
                  </SectionCard>
                  <SectionCard title={T.setPieceTend} icon={<AlertTriangle className="h-4 w-4" />}>
                    <BulletList items={scoutReport.set_piece_tendencies} />
                  </SectionCard>
                </div>

                <SectionCard title={T.formAnalysis} icon={<Zap className="h-4 w-4" />}>
                  <p className="text-sm leading-6 text-slate-700">{scoutReport.form_analysis}</p>
                </SectionCard>

                <button onClick={() => setShowRaw(v => !v)} className="text-xs text-slate-400 underline hover:text-slate-600">
                  {showRaw ? T.hideRaw : T.showRaw}
                </button>
                {showRaw && <pre className="overflow-x-auto rounded-md bg-slate-900 p-4 text-xs leading-5 text-slate-300">{scoutReport.raw_stats_used}</pre>}
              </div>
            ) : null}
          </section>
        </div>
      </div>
    </main>
  );
}
