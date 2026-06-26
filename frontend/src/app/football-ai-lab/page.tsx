'use client';

import type { ReactNode } from 'react';
import { useEffect, useState } from 'react';
import {
  AlertTriangle,
  ChevronDown,
  ClipboardList,
  Download,
  Loader2,
  ShieldAlert,
  Sparkles,
  Target,
  Trophy,
  Users,
  Zap,
} from 'lucide-react';
import {
  ComparisonMetric,
  CompetitionRank,
  DataQuality,
  MatchPrepReport,
  OpponentScoutReport,
  TacticalEvolution,
  TeamEntry,
  generateMatchPrep,
  generateOpponentScout,
  fetchTeams,
  exportPdf,
} from '@/lib/api';

type Mode = 'match' | 'scout';
type Lang = 'en' | 'pt';
type Competition = 'serie_a' | 'world_cup';

const COMP_LABELS: Record<Competition, string> = {
  serie_a: '🇧🇷 Série A',
  world_cup: '🌍 World Cup 2026',
};

// Competitions shown in the toggle. Série A is hidden during World Cup testing —
// add 'serie_a' back here to re-enable it.
const ACTIVE_COMPETITIONS: Competition[] = ['world_cup'];

const t = {
  en: {
    tagline: 'Automated Pre-Match Reports for Professional Football Clubs',
    subtitle: 'AI-powered opponent scouting, tactical analysis and executive reports.',
    keyAlerts: 'Key Alerts',
    feat1: 'Opponent Analysis', feat2: 'Probable XI', feat3: 'Shot Maps & Heatmaps',
    feat4: 'Set Piece Analysis', feat5: 'AI Tactical Insights',
    pdfNote: 'Professional PDF report generated in seconds.',
    modeMatch: 'Match Prep', modeMatchDesc: 'Game plan for an upcoming fixture.',
    modeScout: 'Opponent Scout', modeScoutDesc: 'Deep analysis of a single team.',
    myTeam: 'My team', opponent: 'Opponent', teamToScout: 'Team to scout',
    selectMyTeam: 'Select your team', selectOpponent: 'Select opponent', selectTeam: 'Select a team',
    extraNotes: 'Extra coach notes', optional: 'optional',
    matchPlaceholder: 'Injuries, tactical adjustments, last training notes...',
    scoutPlaceholder: 'Context — known injuries, recent transfers, rivalry history...',
    loadingTeams: 'Loading teams…', generate: 'Generate Professional Report', generating: 'Generating…',
    differentTeams: 'Select two different teams.',
    emptyState: 'Select teams and generate a report.',
    emptyStateSub: 'Live data, no manual entry needed.',
    showRaw: 'Show raw data', hideRaw: 'Hide raw data',
    exportPdf: 'Export PDF', exportingPdf: 'Exporting…',
    source: 'Source', matchPrep: 'Match Preparation', opponentScout: 'Opponent Scout',
    execSummary: 'Executive Summary', oppStrengths: 'Opponent Strengths',
    oppWeaknesses: 'Opponent Weaknesses', keyThreats: 'Key Threats to Neutralise',
    tacticalApproach: 'Tactical Approach', pressingTriggers: 'Pressing Triggers',
    attackingApproach: 'Attacking Approach', setPieces: 'Set Pieces',
    riskAssessment: 'Main Risks', playingStyle: 'Playing Style',
    strengths: 'Strengths', weaknesses: 'Weaknesses', keyPatterns: 'Key Patterns',
    howToBeat: 'How to Beat Them', pressingVuln: 'Pressing Vulnerabilities',
    setPieceTend: 'Set Piece Tendencies', formAnalysis: 'Form Analysis', vs: 'vs',
    group: 'Group',
    dangerPlayers: 'Top Danger Players', howTheyScore: 'How They Score',
    probableLineup: 'Probable XI (inferred from last lineup)', goalsLabel: 'G', assistsLabel: 'A',
    onTargetLabel: 'On target', dangerLabel: 'Danger',
    shotAnalysis: 'Shot Maps', goalTiming: 'Goal Timing',
    matchupEdges: 'Matchup Edges', subNotes: 'Match Management',
    goalLog: 'Goals (scorers & minutes)', goalsScored: 'Scored', goalsConceded: 'Conceded',
    tacticalEvolution: 'Tactical Evolution', unchanged: 'Unchanged', formation: 'Formation',
    headToHead: 'Head-to-Head Comparison',
    competitionContext: 'Competition Context',
    dataConfidence: 'Data Confidence', confidence: 'Confidence',
    matchesAnalysed: 'matches analysed', shotsWithCoords: 'shots with coordinates',
    basedOn: 'Based on',
  },
  pt: {
    tagline: 'Relatórios Automáticos de Pré-Jogo para Clubes Profissionais',
    subtitle: 'Scouting de adversários, análise táctica e relatórios executivos com IA.',
    keyAlerts: 'Alertas Chave',
    feat1: 'Análise do Adversário', feat2: 'Onze Provável', feat3: 'Mapas de Remates & Heatmaps',
    feat4: 'Análise de Bolas Paradas', feat5: 'Insights Tácticos com IA',
    pdfNote: 'Relatório PDF profissional gerado em segundos.',
    modeMatch: 'Preparação de Jogo', modeMatchDesc: 'Plano de jogo para o próximo confronto.',
    modeScout: 'Scout Adversário', modeScoutDesc: 'Análise aprofundada de uma única equipa.',
    myTeam: 'A minha equipa', opponent: 'Adversário', teamToScout: 'Equipa a analisar',
    selectMyTeam: 'Selecionar a minha equipa', selectOpponent: 'Selecionar adversário', selectTeam: 'Selecionar equipa',
    extraNotes: 'Notas extra do treinador', optional: 'opcional',
    matchPlaceholder: 'Lesões, ajustes tácticos, observações do treino...',
    scoutPlaceholder: 'Contexto — lesões conhecidas, transferências recentes...',
    loadingTeams: 'A carregar equipas…', generate: 'Gerar Relatório Profissional', generating: 'A gerar…',
    differentTeams: 'Selecione duas equipas diferentes.',
    emptyState: 'Selecione as equipas e gere um relatório.',
    emptyStateSub: 'Dados em tempo real, sem entrada manual.',
    showRaw: 'Ver dados brutos', hideRaw: 'Ocultar dados brutos',
    exportPdf: 'Exportar PDF', exportingPdf: 'A exportar…',
    source: 'Fonte', matchPrep: 'Preparação de Jogo', opponentScout: 'Scout Adversário',
    execSummary: 'Sumário Executivo', oppStrengths: 'Pontos Fortes do Adversário',
    oppWeaknesses: 'Pontos Fracos do Adversário', keyThreats: 'Ameaças a Neutralizar',
    tacticalApproach: 'Abordagem Táctica', pressingTriggers: 'Gatilhos de Pressão',
    attackingApproach: 'Abordagem Ofensiva', setPieces: 'Bolas Paradas',
    riskAssessment: 'Riscos Principais', playingStyle: 'Estilo de Jogo',
    strengths: 'Pontos Fortes', weaknesses: 'Pontos Fracos', keyPatterns: 'Padrões Identificados',
    howToBeat: 'Como Bater Esta Equipa', pressingVuln: 'Vulnerabilidades à Pressão',
    setPieceTend: 'Tendências em Bolas Paradas', formAnalysis: 'Análise de Forma', vs: 'vs',
    group: 'Grupo',
    dangerPlayers: 'Jogadores Mais Perigosos', howTheyScore: 'Como Marcam',
    probableLineup: 'Onze Provável (inferido do último onze)', goalsLabel: 'G', assistsLabel: 'A',
    onTargetLabel: 'Ao alvo', dangerLabel: 'Perigo',
    shotAnalysis: 'Mapas de Remates', goalTiming: 'Timing dos Golos',
    matchupEdges: 'Confronto Directo', subNotes: 'Gestão de Jogo',
    goalLog: 'Golos (marcadores e minutos)', goalsScored: 'Marcados', goalsConceded: 'Sofridos',
    tacticalEvolution: 'Evolução Táctica', unchanged: 'Inalterado', formation: 'Formação',
    headToHead: 'Comparação Directa',
    competitionContext: 'Contexto na Competição',
    dataConfidence: 'Confiança dos Dados', confidence: 'Confiança',
    matchesAnalysed: 'jogos analisados', shotsWithCoords: 'remates com coordenadas',
    basedOn: 'Baseado em',
  },
} as const;

function SectionCard({ title, icon, children }: { title: string; icon: ReactNode; children: ReactNode }) {
  return (
    <section className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
      <div className="mb-3 flex items-center gap-2">
        <span className="flex h-8 w-8 items-center justify-center rounded-md bg-emerald-50 text-emerald-700">{icon}</span>
        <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-900">{title}</h2>
      </div>
      {children}
    </section>
  );
}

function BulletList({ items }: { items: string[] }) {
  if (!items.length) return <p className="text-sm text-slate-400">—</p>;
  return (
    <ul className="space-y-1.5 text-sm leading-6 text-slate-700">
      {items.map((item, i) => (
        <li key={i} className="flex gap-2">
          <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-emerald-600" />
          <span>{item}</span>
        </li>
      ))}
    </ul>
  );
}

function TeamSelect({ label, value, onChange, teams, placeholder, competition }: {
  label: string; value: string; onChange: (v: string) => void;
  teams: TeamEntry[]; placeholder: string; competition: Competition;
}) {
  const grouped = competition === 'world_cup';
  const groups = grouped ? [...new Set(teams.map(t => t.group))].sort() : [];

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
          {grouped
            ? groups.map(g => (
                <optgroup key={g} label={g}>
                  {teams.filter(t => t.group === g).map(t => (
                    <option key={t.team} value={t.team}>{t.team}</option>
                  ))}
                </optgroup>
              ))
            : teams.map(t => <option key={t.team} value={t.team}>{t.team}</option>)
          }
        </select>
        <ChevronDown className="pointer-events-none absolute right-3 top-3 h-4 w-4 text-slate-400" />
      </div>
    </label>
  );
}

function DataConfidenceBar({ dq, lang }: { dq: DataQuality; lang: Lang }) {
  const T = t[lang];
  if (!dq.matches_analysed) return null;
  // Coach-facing: just the sample size, stated neutrally. The full provenance
  // (provider, xG source, warnings) still feeds the model internally to keep
  // the prose honest, but a coach doesn't need to see "no xG / scraped ESPN".
  return (
    <p className="text-xs font-medium text-slate-400">
      {T.basedOn} {dq.matches_analysed} {T.matchesAnalysed}
    </p>
  );
}

function RankingsSection({ ranks, title, lang }: {
  ranks: CompetitionRank[]; title: string; lang: Lang;
}) {
  const T = t[lang];
  if (!ranks.length) return null;
  const tone = (r: CompetitionRank) =>
    r.good ? 'border-emerald-300 bg-emerald-50 text-emerald-800' :
    r.bad ? 'border-red-300 bg-red-50 text-red-800' :
    'border-slate-200 bg-slate-50 text-slate-700';
  return (
    <SectionCard title={title || T.competitionContext} icon={<Trophy className="h-4 w-4" />}>
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        {ranks.map((r, i) => (
          <div key={i} className={`rounded-lg border px-3 py-3 text-center ${tone(r)}`}>
            <p className="text-2xl font-bold leading-none">#{r.rank}</p>
            <p className="mt-1 text-xs font-medium opacity-70">/ {r.total}</p>
            <p className="mt-1.5 text-sm font-semibold">{r.label}</p>
            <p className="text-xs opacity-80">{r.value} / {lang === 'pt' ? 'jogo' : 'game'}</p>
          </div>
        ))}
      </div>
    </SectionCard>
  );
}

function ComparisonSection({ metrics, myName, oppName, lang }: {
  metrics: ComparisonMetric[]; myName: string; oppName: string; lang: Lang;
}) {
  const T = t[lang];
  if (!metrics.length) return null;
  return (
    <SectionCard title={T.headToHead} icon={<Target className="h-4 w-4" />}>
      <div className="mb-3 flex items-center justify-between text-sm font-bold">
        <span className="text-emerald-700">{myName}</span>
        <span className="text-red-600">{oppName}</span>
      </div>
      <div className="space-y-3">
        {metrics.map((m, i) => {
          const max = Math.max(m.my, m.opp, 0.0001);
          const myPct = (m.my / max) * 100;
          const oppPct = (m.opp / max) * 100;
          return (
            <div key={i}>
              <p className="mb-1 text-center text-xs font-medium text-slate-400">{m.label}</p>
              <div className="flex items-center gap-2">
                <span className="w-10 shrink-0 text-right text-xs font-bold text-emerald-700">{m.my_disp}</span>
                <div className="flex flex-1 items-center justify-end">
                  <div className="h-3 rounded-l bg-emerald-600" style={{ width: `${myPct}%` }} />
                </div>
                <div className="h-3 w-px shrink-0 bg-slate-300" />
                <div className="flex flex-1 items-center justify-start">
                  <div className="h-3 rounded-r bg-red-500" style={{ width: `${oppPct}%` }} />
                </div>
                <span className="w-10 shrink-0 text-left text-xs font-bold text-red-600">{m.opp_disp}</span>
              </div>
            </div>
          );
        })}
      </div>
    </SectionCard>
  );
}

function TacticalEvolutionSection({ evo, lang }: { evo: TacticalEvolution; lang: Lang }) {
  const T = t[lang];
  if (!evo.matches || evo.matches.length === 0) return null;

  const resultColor = (r: string) =>
    r === 'W' ? 'bg-emerald-600 text-white' :
    r === 'D' ? 'bg-amber-500 text-white' :
    'bg-red-600 text-white';

  return (
    <SectionCard title={T.tacticalEvolution} icon={<ClipboardList className="h-4 w-4" />}>
      {/* Summary lines */}
      {evo.summary && evo.summary.length > 0 && (
        <div className="mb-3 flex flex-wrap gap-2">
          {evo.summary.map((s, i) => (
            <span key={i} className="rounded-full bg-slate-100 px-3 py-1 text-xs font-medium text-slate-700">{s}</span>
          ))}
        </div>
      )}
      {/* Match-by-match timeline */}
      <div className="space-y-2">
        {evo.matches.map((m, i) => {
          const hasChanges = m.changes_from_prev && m.changes_from_prev.length > 0;
          const isFormationChange = m.changes_from_prev?.some(c => c.startsWith('Formation:'));
          return (
            <div
              key={i}
              className={`rounded-md border px-3 py-2 ${isFormationChange ? 'border-amber-300 bg-amber-50' : 'border-slate-200 bg-white'}`}
            >
              <div className="flex flex-wrap items-center gap-2">
                <span className="text-xs text-slate-400 w-20 shrink-0">{m.date}</span>
                <span className="text-xs font-medium text-slate-700">vs {m.opponent}</span>
                <span className={`rounded px-1.5 py-0.5 text-xs font-bold ${resultColor(m.result)}`}>
                  {m.result} {m.score}
                </span>
                {m.formation_name && (
                  <span className="rounded bg-slate-900 px-2 py-0.5 text-xs font-semibold text-white">
                    {m.formation_name}
                  </span>
                )}
              </div>
              {hasChanges && (
                <div className="mt-1.5 flex flex-wrap gap-1.5">
                  {m.changes_from_prev.map((c, j) => (
                    <span
                      key={j}
                      className={`rounded-full px-2 py-0.5 text-xs ${
                        c === 'Unchanged XI' || c === 'Inalterado'
                          ? 'bg-slate-100 text-slate-400'
                          : c.startsWith('Formation:')
                          ? 'bg-amber-200 text-amber-900 font-semibold'
                          : 'bg-blue-50 text-blue-700'
                      }`}
                    >
                      {c}
                    </span>
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </SectionCard>
  );
}

function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

export default function FootballAiLabPage() {
  const [teams, setTeams] = useState<TeamEntry[]>([]);
  const [mode, setMode] = useState<Mode>('match');
  const [lang, setLang] = useState<Lang>('en');
  const [competition, setCompetition] = useState<Competition>(ACTIVE_COMPETITIONS[0]);
  const [myTeam, setMyTeam] = useState('');
  const [opponentTeam, setOpponentTeam] = useState('');
  const [scoutTeam, setScoutTeam] = useState('');
  const [extraNotes, setExtraNotes] = useState('');
  const [matchReport, setMatchReport] = useState<MatchPrepReport | null>(null);
  const [scoutReport, setScoutReport] = useState<OpponentScoutReport | null>(null);
  const [loading, setLoading] = useState(false);
  const [loadingTeams, setLoadingTeams] = useState(true);
  const [exportingPdf, setExportingPdf] = useState(false);
  const [error, setError] = useState('');
  const [showRaw, setShowRaw] = useState(false);
  const [reportLang, setReportLang] = useState<Lang | null>(null);

  const T = t[lang];

  useEffect(() => {
    setLoadingTeams(true);
    setMyTeam('');
    setOpponentTeam('');
    setScoutTeam('');
    fetchTeams(competition).then(setTeams).finally(() => setLoadingTeams(false));
  }, [competition]);

  async function handleGenerate() {
    if (loading) return;
    setLoading(true);
    setError('');
    setMatchReport(null);
    setScoutReport(null);
    setShowRaw(false);

    try {
      if (mode === 'match') {
        const r = await generateMatchPrep({ my_team: myTeam, opponent_team: opponentTeam, extra_notes: extraNotes, language: lang, competition });
        setMatchReport(r);
      } else {
        const r = await generateOpponentScout({ team: scoutTeam, extra_notes: extraNotes, language: lang, competition });
        setScoutReport(r);
      }
      setReportLang(lang);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not generate the report.');
    } finally {
      setLoading(false);
    }
  }

  async function handleExportPdf() {
    if (exportingPdf) return;
    setExportingPdf(true);
    try {
      let blob: Blob;
      let filename: string;
      if (matchReport) {
        blob = await exportPdf({ report_type: 'match_prep', language: lang, report: matchReport as unknown as object });
        filename = `match_prep_${matchReport.my_team}_vs_${matchReport.opponent_team}.pdf`.replace(/\s+/g, '_');
      } else if (scoutReport) {
        blob = await exportPdf({ report_type: 'scout', language: lang, report: scoutReport as unknown as object });
        filename = `scout_${scoutReport.team}.pdf`.replace(/\s+/g, '_');
      } else return;
      downloadBlob(blob, filename);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'PDF export failed.');
    } finally {
      setExportingPdf(false);
    }
  }

  const canSubmit = mode === 'match'
    ? myTeam.length > 0 && opponentTeam.length > 0 && myTeam !== opponentTeam
    : scoutTeam.length > 0;

  const hasReport = matchReport !== null || scoutReport !== null;
  const langMismatch = hasReport && reportLang !== null && reportLang !== lang;

  return (
    <main className="min-h-screen bg-slate-50 text-slate-950">
      <div className="mx-auto flex w-full max-w-7xl flex-col gap-6 px-4 py-6 sm:px-6 lg:px-8">

        {/* Header */}
        <header className="flex flex-wrap items-start justify-between gap-4 border-b border-slate-200 pb-5">
          <div>
            <h1 className="text-3xl font-semibold">Football AI Lab</h1>
            <p className="mt-1 text-sm font-medium text-emerald-700">{T.tagline}</p>
            <p className="mt-1 max-w-2xl text-sm leading-6 text-slate-500">{T.subtitle}</p>
          </div>
          <div className="flex items-center gap-2">
            {/* Competition toggle — hidden when only one competition is active */}
            {ACTIVE_COMPETITIONS.length > 1 ? (
              <div className="flex rounded-md border border-slate-200 bg-white overflow-hidden shadow-sm">
                {ACTIVE_COMPETITIONS.map((c) => (
                  <button
                    key={c}
                    onClick={() => setCompetition(c)}
                    className={`px-3 py-1.5 text-xs font-semibold transition ${
                      competition === c
                        ? 'bg-slate-950 text-white'
                        : 'text-slate-600 hover:bg-slate-50'
                    }`}
                  >
                    {COMP_LABELS[c]}
                  </button>
                ))}
              </div>
            ) : (
              <span className="rounded-md border border-slate-200 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 shadow-sm">
                {COMP_LABELS[ACTIVE_COMPETITIONS[0]]}
              </span>
            )}
            {/* Language toggle */}
            <button
              onClick={() => setLang(l => l === 'en' ? 'pt' : 'en')}
              className="rounded-md border border-slate-200 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 shadow-sm transition hover:border-slate-400"
            >
              {lang === 'en' ? '🇬🇧 EN' : '🇵🇹 PT'}
            </button>
          </div>
        </header>

        {/* Mode selector */}
        <div className="flex gap-3">
          {(['match', 'scout'] as Mode[]).map((m) => (
            <button
              key={m}
              onClick={() => { setMode(m); setMatchReport(null); setScoutReport(null); setError(''); setReportLang(null); }}
              className={`flex-1 rounded-lg border p-4 text-left transition ${
                mode === m
                  ? 'border-emerald-600 bg-emerald-50 text-emerald-900'
                  : 'border-slate-200 bg-white text-slate-600 hover:border-slate-300'
              }`}
            >
              <p className="text-sm font-semibold">{m === 'match' ? T.modeMatch : T.modeScout}</p>
              <p className="mt-0.5 text-xs text-slate-500">{m === 'match' ? T.modeMatchDesc : T.modeScoutDesc}</p>
            </button>
          ))}
        </div>

        <div className="grid gap-6 xl:grid-cols-[360px_1fr]">
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
                <div className="flex items-center gap-2 py-4 text-sm text-slate-400">
                  <Loader2 className="h-4 w-4 animate-spin" /> {T.loadingTeams}
                </div>
              ) : mode === 'match' ? (
                <>
                  <TeamSelect label={T.myTeam} value={myTeam} onChange={setMyTeam}
                    teams={teams} placeholder={T.selectMyTeam} competition={competition} />
                  <TeamSelect label={T.opponent} value={opponentTeam} onChange={setOpponentTeam}
                    teams={teams.filter(t => t.team !== myTeam)} placeholder={T.selectOpponent} competition={competition} />
                </>
              ) : (
                <TeamSelect label={T.teamToScout} value={scoutTeam} onChange={setScoutTeam}
                  teams={teams} placeholder={T.selectTeam} competition={competition} />
              )}

              <label className="block">
                <span className="mb-1.5 block text-sm font-medium text-slate-700">
                  {T.extraNotes} <span className="font-normal text-slate-400">({T.optional})</span>
                </span>
                <textarea
                  value={extraNotes}
                  onChange={(e) => setExtraNotes(e.target.value)}
                  placeholder={mode === 'match' ? T.matchPlaceholder : T.scoutPlaceholder}
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
                className="inline-flex h-14 w-full items-center justify-center gap-2 rounded-lg bg-emerald-700 px-4 text-base font-bold text-white shadow-md transition hover:bg-emerald-800 disabled:cursor-not-allowed disabled:bg-slate-300"
              >
                {loading ? <Loader2 className="h-5 w-5 animate-spin" /> : <Sparkles className="h-5 w-5" />}
                {loading ? T.generating : T.generate}
              </button>
              <p className="text-center text-xs text-slate-400">{T.pdfNote}</p>
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
                <p className="mt-2 max-w-sm text-sm text-slate-400">{T.emptyStateSub}</p>

                <div className="mt-8 grid w-full max-w-2xl grid-cols-2 gap-3 sm:grid-cols-3">
                  {[
                    { icon: <ShieldAlert className="h-5 w-5" />, label: T.feat1 },
                    { icon: <Users className="h-5 w-5" />, label: T.feat2 },
                    { icon: <Target className="h-5 w-5" />, label: T.feat3 },
                    { icon: <Trophy className="h-5 w-5" />, label: T.feat4 },
                    { icon: <Sparkles className="h-5 w-5" />, label: T.feat5 },
                  ].map((f, i) => (
                    <div key={i} className="flex items-center gap-2 rounded-lg border border-slate-200 bg-slate-50 px-3 py-3 text-left">
                      <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-emerald-100 text-emerald-700">
                        {f.icon}
                      </span>
                      <span className="text-xs font-semibold text-slate-700">{f.label}</span>
                    </div>
                  ))}
                </div>
                <p className="mt-5 text-xs text-slate-400">{T.pdfNote}</p>
              </div>
            ) : (
              <div className="space-y-5">
                {/* Lang mismatch warning */}
                {langMismatch && (
                  <div className="flex items-start gap-3 rounded-md border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800">
                    <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-amber-500" />
                    <span>
                      {lang === 'pt'
                        ? 'Este relatório foi gerado em inglês. Clique em "Gerar Relatório" para obter a versão em português.'
                        : 'This report was generated in Portuguese. Click "Generate Report" to get the English version.'}
                    </span>
                  </div>
                )}

                {/* Cover bar */}
                <div className="rounded-lg bg-slate-950 p-6 text-white">
                  <p className="text-xs font-semibold uppercase tracking-wide text-emerald-300">
                    {matchReport ? T.matchPrep : T.opponentScout} — {COMP_LABELS[competition]}
                  </p>
                  <h2 className="mt-1 text-xl font-semibold">
                    {matchReport
                      ? `${matchReport.my_team} ${T.vs} ${matchReport.opponent_team}`
                      : scoutReport?.team}
                  </h2>
                  <p className="mt-3 max-w-3xl whitespace-pre-line text-sm leading-6 text-slate-200">
                    {matchReport?.executive_summary ?? scoutReport?.executive_summary}
                  </p>
                  <p className="mt-3 text-xs text-slate-500">
                    {T.source}: {matchReport?.data_source ?? scoutReport?.data_source}
                  </p>
                </div>

                {/* Data Confidence — provenance + sample size, top of every report */}
                {(matchReport?.data_quality ?? scoutReport?.data_quality) && (
                  <DataConfidenceBar
                    dq={(matchReport?.data_quality ?? scoutReport?.data_quality) as DataQuality}
                    lang={reportLang ?? lang}
                  />
                )}

                {/* Key Alerts — prominent, top of scout report */}
                {scoutReport?.key_alerts && scoutReport.key_alerts.length > 0 && (
                  <div className="rounded-lg border border-red-200 bg-red-50 p-4">
                    <h3 className="mb-2 flex items-center gap-2 text-sm font-bold uppercase tracking-wide text-red-700">
                      <AlertTriangle className="h-4 w-4" /> {T.keyAlerts}
                    </h3>
                    <ul className="space-y-2">
                      {scoutReport.key_alerts.map((a, i) => (
                        <li key={i} className="flex gap-2 border-l-2 border-red-500 pl-3 text-sm font-medium text-red-900">
                          {a}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* Match Prep sections */}
                {matchReport && <>
                  {/* Matchup edges — the cross-data differentiator */}
                  {matchReport.matchup_insights && matchReport.matchup_insights.length > 0 && (
                    <div className="rounded-lg border border-red-200 bg-red-50 p-4">
                      <h3 className="mb-2 flex items-center gap-2 text-sm font-bold uppercase tracking-wide text-red-700">
                        <AlertTriangle className="h-4 w-4" /> {T.matchupEdges}
                      </h3>
                      <ul className="space-y-2">
                        {matchReport.matchup_insights.map((m, i) => (
                          <li key={i} className="border-l-2 border-red-500 pl-3 text-sm font-medium text-red-900">{m}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {matchReport.opponent_ranks && matchReport.opponent_ranks.length > 0 && (
                    <RankingsSection
                      ranks={matchReport.opponent_ranks}
                      title={`${T.competitionContext} — ${matchReport.opponent_team}`}
                      lang={reportLang ?? lang}
                    />
                  )}

                  {matchReport.comparison && matchReport.comparison.length > 0 && (
                    <ComparisonSection
                      metrics={matchReport.comparison}
                      myName={matchReport.my_team}
                      oppName={matchReport.opponent_team}
                      lang={reportLang ?? lang}
                    />
                  )}

                  <div className="grid gap-5 lg:grid-cols-2">
                    <SectionCard title={T.oppStrengths} icon={<Zap className="h-4 w-4" />}>
                      <BulletList items={matchReport.opponent_strengths} />
                    </SectionCard>
                    <SectionCard title={T.oppWeaknesses} icon={<ShieldAlert className="h-4 w-4" />}>
                      <BulletList items={matchReport.opponent_weaknesses} />
                    </SectionCard>
                  </div>

                  {matchReport.opponent_danger_players && matchReport.opponent_danger_players.length > 0 && (
                    <SectionCard title={`${T.dangerPlayers} — ${matchReport.opponent_team}`} icon={<Zap className="h-4 w-4" />}>
                      <div className="overflow-hidden rounded-md border border-slate-200">
                        <table className="w-full text-sm">
                          <thead className="bg-slate-50 text-xs uppercase text-slate-500">
                            <tr>
                              <th className="px-3 py-2 text-left font-semibold">#</th>
                              <th className="px-3 py-2 text-left font-semibold">{T.dangerLabel}</th>
                              <th className="px-2 py-2 text-center font-semibold">{T.goalsLabel}</th>
                              <th className="px-2 py-2 text-center font-semibold">{T.assistsLabel}</th>
                              <th className="px-2 py-2 text-center font-semibold">{T.onTargetLabel}</th>
                            </tr>
                          </thead>
                          <tbody>
                            {matchReport.opponent_danger_players.map((p, i) => (
                              <tr key={i} className={i === 0 ? 'bg-emerald-50' : 'bg-white'}>
                                <td className="px-3 py-2 text-slate-400">{i + 1}</td>
                                <td className="px-3 py-2 font-medium text-slate-900">{p.player}</td>
                                <td className="px-2 py-2 text-center text-slate-700">{p.goals}</td>
                                <td className="px-2 py-2 text-center text-slate-700">{p.assists}</td>
                                <td className="px-2 py-2 text-center text-slate-700">{p.on_target}/{p.shots}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </SectionCard>
                  )}

                  {matchReport.opponent_tactical_evolution && (matchReport.opponent_tactical_evolution.matches?.length ?? 0) > 0 && (
                    <TacticalEvolutionSection evo={matchReport.opponent_tactical_evolution} lang={reportLang ?? lang} />
                  )}

                  {matchReport.opponent_goals_log && matchReport.opponent_goals_log.length > 0 && (
                    <SectionCard title={`${T.goalLog} — ${matchReport.opponent_team}`} icon={<Trophy className="h-4 w-4" />}>
                      <p className="text-sm text-slate-700">{matchReport.opponent_goals_log.join('  ·  ')}</p>
                    </SectionCard>
                  )}

                  {(matchReport.images?.shotmap_for || matchReport.images?.shotmap_against) && (
                    <SectionCard title={`${T.shotAnalysis} — ${matchReport.opponent_team}`} icon={<Target className="h-4 w-4" />}>
                      <div className="grid gap-4 sm:grid-cols-2">
                        {matchReport.images?.shotmap_for && (
                          /* eslint-disable-next-line @next/next/no-img-element */
                          <img src={matchReport.images.shotmap_for} alt="Opponent shots" className="rounded-md" />
                        )}
                        {matchReport.images?.shotmap_against && (
                          /* eslint-disable-next-line @next/next/no-img-element */
                          <img src={matchReport.images.shotmap_against} alt="Opponent shots conceded" className="rounded-md" />
                        )}
                      </div>
                    </SectionCard>
                  )}
                  <SectionCard title={T.keyThreats} icon={<Users className="h-4 w-4" />}>
                    <BulletList items={matchReport.key_threats} />
                  </SectionCard>
                  <SectionCard title={T.tacticalApproach} icon={<ClipboardList className="h-4 w-4" />}>
                    <p className="whitespace-pre-line text-sm leading-6 text-slate-700">{matchReport.tactical_approach}</p>
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

                  {matchReport.substitution_notes && matchReport.substitution_notes.length > 0 && (
                    <SectionCard title={T.subNotes} icon={<Users className="h-4 w-4" />}>
                      <BulletList items={matchReport.substitution_notes} />
                    </SectionCard>
                  )}
                </>}

                {/* Scout sections */}
                {scoutReport && <>
                  {scoutReport.competition_ranks && scoutReport.competition_ranks.length > 0 && (
                    <RankingsSection ranks={scoutReport.competition_ranks} title={T.competitionContext} lang={reportLang ?? lang} />
                  )}

                  <SectionCard title={T.playingStyle} icon={<ClipboardList className="h-4 w-4" />}>
                    <p className="text-sm leading-6 text-slate-700">{scoutReport.playing_style}</p>
                  </SectionCard>

                  {scoutReport.top_danger_players && scoutReport.top_danger_players.length > 0 && (
                    <SectionCard title={T.dangerPlayers} icon={<Zap className="h-4 w-4" />}>
                      <div className="overflow-hidden rounded-md border border-slate-200">
                        <table className="w-full text-sm">
                          <thead className="bg-slate-50 text-xs uppercase text-slate-500">
                            <tr>
                              <th className="px-3 py-2 text-left font-semibold">#</th>
                              <th className="px-3 py-2 text-left font-semibold">{T.teamToScout.split(' ')[0]}</th>
                              <th className="px-2 py-2 text-center font-semibold">{T.goalsLabel}</th>
                              <th className="px-2 py-2 text-center font-semibold">{T.assistsLabel}</th>
                              <th className="px-2 py-2 text-center font-semibold">{T.onTargetLabel}</th>
                              <th className="px-2 py-2 text-center font-semibold">{T.dangerLabel}</th>
                            </tr>
                          </thead>
                          <tbody>
                            {scoutReport.top_danger_players.map((p, i) => (
                              <tr key={i} className={i === 0 ? 'bg-emerald-50' : 'bg-white'}>
                                <td className="px-3 py-2 text-slate-400">{i + 1}</td>
                                <td className="px-3 py-2 font-medium text-slate-900">{p.player}</td>
                                <td className="px-2 py-2 text-center text-slate-700">{p.goals}</td>
                                <td className="px-2 py-2 text-center text-slate-700">{p.assists}</td>
                                <td className="px-2 py-2 text-center text-slate-700">{p.on_target}/{p.shots}</td>
                                <td className="px-2 py-2 text-center font-semibold text-emerald-700">{p.score}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </SectionCard>
                  )}

                  {scoutReport.tactical_evolution && (scoutReport.tactical_evolution.matches?.length ?? 0) > 0 && (
                    <TacticalEvolutionSection evo={scoutReport.tactical_evolution} lang={reportLang ?? lang} />
                  )}

                  {scoutReport.how_they_score && scoutReport.how_they_score.length > 0 && (
                    <SectionCard title={T.howTheyScore} icon={<Target className="h-4 w-4" />}>
                      <BulletList items={scoutReport.how_they_score} />
                    </SectionCard>
                  )}

                  {((scoutReport.goals_log_for?.length ?? 0) > 0 || (scoutReport.goals_log_against?.length ?? 0) > 0) && (
                    <SectionCard title={T.goalLog} icon={<Trophy className="h-4 w-4" />}>
                      {scoutReport.goals_log_for && scoutReport.goals_log_for.length > 0 && (
                        <p className="text-sm text-slate-700">
                          <span className="font-semibold text-emerald-700">{T.goalsScored}: </span>
                          {scoutReport.goals_log_for.join('  ·  ')}
                        </p>
                      )}
                      {scoutReport.goals_log_against && scoutReport.goals_log_against.length > 0 && (
                        <p className="mt-1.5 text-sm text-slate-700">
                          <span className="font-semibold text-red-700">{T.goalsConceded}: </span>
                          {scoutReport.goals_log_against.join('  ·  ')}
                        </p>
                      )}
                    </SectionCard>
                  )}

                  {scoutReport.images?.formation ? (
                    <SectionCard title={T.probableLineup} icon={<Users className="h-4 w-4" />}>
                      {/* eslint-disable-next-line @next/next/no-img-element */}
                      <img src={scoutReport.images.formation} alt="Formation"
                        className="mx-auto max-h-[520px] rounded-md" />
                    </SectionCard>
                  ) : scoutReport.probable_lineup && scoutReport.probable_lineup.length > 0 && (
                    <SectionCard title={T.probableLineup} icon={<Users className="h-4 w-4" />}>
                      <div className="flex flex-wrap gap-2">
                        {scoutReport.probable_lineup.map((name, i) => (
                          <span key={i} className="rounded-full bg-slate-100 px-3 py-1 text-xs font-medium text-slate-700">
                            {name}
                          </span>
                        ))}
                      </div>
                    </SectionCard>
                  )}

                  {(scoutReport.images?.shotmap_for || scoutReport.images?.shotmap_against) && (
                    <SectionCard title={T.shotAnalysis} icon={<Target className="h-4 w-4" />}>
                      <div className="grid gap-4 sm:grid-cols-2">
                        {scoutReport.images?.shotmap_for && (
                          /* eslint-disable-next-line @next/next/no-img-element */
                          <img src={scoutReport.images.shotmap_for} alt="Shots taken" className="rounded-md" />
                        )}
                        {scoutReport.images?.shotmap_against && (
                          /* eslint-disable-next-line @next/next/no-img-element */
                          <img src={scoutReport.images.shotmap_against} alt="Shots conceded" className="rounded-md" />
                        )}
                      </div>
                    </SectionCard>
                  )}

                  {scoutReport.images?.timing && (
                    <SectionCard title={T.goalTiming} icon={<Zap className="h-4 w-4" />}>
                      {/* eslint-disable-next-line @next/next/no-img-element */}
                      <img src={scoutReport.images.timing} alt="Goal timing" className="w-full rounded-md" />
                    </SectionCard>
                  )}
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
                </>}

                {/* Footer actions */}
                <div className="flex items-center justify-between border-t border-slate-100 pt-4">
                  <button
                    onClick={() => setShowRaw(v => !v)}
                    className="text-xs text-slate-400 underline hover:text-slate-600"
                  >
                    {showRaw ? T.hideRaw : T.showRaw}
                  </button>
                  <button
                    onClick={handleExportPdf}
                    disabled={exportingPdf}
                    className="inline-flex items-center gap-2 rounded-md bg-slate-950 px-4 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-slate-800 disabled:bg-slate-400"
                  >
                    {exportingPdf
                      ? <><Loader2 className="h-4 w-4 animate-spin" />{T.exportingPdf}</>
                      : <><Download className="h-4 w-4" />{T.exportPdf}</>
                    }
                  </button>
                </div>

                {showRaw && (
                  <pre className="overflow-x-auto rounded-md bg-slate-900 p-4 text-xs leading-5 text-slate-300">
                    {matchReport?.raw_stats_used ?? scoutReport?.raw_stats_used}
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
