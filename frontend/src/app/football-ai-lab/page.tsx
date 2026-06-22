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
  MatchPrepReport,
  OpponentScoutReport,
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

const t = {
  en: {
    subtitle: 'Match preparation reports powered by live ESPN data.',
    modeMatch: 'Match Prep', modeMatchDesc: 'Game plan for an upcoming fixture.',
    modeScout: 'Opponent Scout', modeScoutDesc: 'Deep analysis of a single team.',
    myTeam: 'My team', opponent: 'Opponent', teamToScout: 'Team to scout',
    selectMyTeam: 'Select your team', selectOpponent: 'Select opponent', selectTeam: 'Select a team',
    extraNotes: 'Extra coach notes', optional: 'optional',
    matchPlaceholder: 'Injuries, tactical adjustments, last training notes...',
    scoutPlaceholder: 'Context — known injuries, recent transfers, rivalry history...',
    loadingTeams: 'Loading teams…', generate: 'Generate Report', generating: 'Generating…',
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
    riskAssessment: 'Risk Assessment', playingStyle: 'Playing Style',
    strengths: 'Strengths', weaknesses: 'Weaknesses', keyPatterns: 'Key Patterns',
    howToBeat: 'How to Beat Them', pressingVuln: 'Pressing Vulnerabilities',
    setPieceTend: 'Set Piece Tendencies', formAnalysis: 'Form Analysis', vs: 'vs',
    group: 'Group',
    dangerPlayers: 'Top Danger Players', howTheyScore: 'How They Score',
    probableLineup: 'Probable XI', goalsLabel: 'G', assistsLabel: 'A',
    onTargetLabel: 'On target', dangerLabel: 'Danger',
  },
  pt: {
    subtitle: 'Relatórios de preparação com dados ESPN em tempo real.',
    modeMatch: 'Preparação de Jogo', modeMatchDesc: 'Plano de jogo para o próximo confronto.',
    modeScout: 'Scout Adversário', modeScoutDesc: 'Análise aprofundada de uma única equipa.',
    myTeam: 'A minha equipa', opponent: 'Adversário', teamToScout: 'Equipa a analisar',
    selectMyTeam: 'Selecionar a minha equipa', selectOpponent: 'Selecionar adversário', selectTeam: 'Selecionar equipa',
    extraNotes: 'Notas extra do treinador', optional: 'opcional',
    matchPlaceholder: 'Lesões, ajustes tácticos, observações do treino...',
    scoutPlaceholder: 'Contexto — lesões conhecidas, transferências recentes...',
    loadingTeams: 'A carregar equipas…', generate: 'Gerar Relatório', generating: 'A gerar…',
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
    riskAssessment: 'Avaliação de Risco', playingStyle: 'Estilo de Jogo',
    strengths: 'Pontos Fortes', weaknesses: 'Pontos Fracos', keyPatterns: 'Padrões Identificados',
    howToBeat: 'Como Bater Esta Equipa', pressingVuln: 'Vulnerabilidades à Pressão',
    setPieceTend: 'Tendências em Bolas Paradas', formAnalysis: 'Análise de Forma', vs: 'vs',
    group: 'Grupo',
    dangerPlayers: 'Jogadores Mais Perigosos', howTheyScore: 'Como Marcam',
    probableLineup: 'Onze Provável', goalsLabel: 'G', assistsLabel: 'A',
    onTargetLabel: 'Ao alvo', dangerLabel: 'Perigo',
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
  const [competition, setCompetition] = useState<Competition>('serie_a');
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
            <p className="text-xs font-semibold uppercase tracking-wide text-emerald-700">Experimental module</p>
            <h1 className="mt-1 text-3xl font-semibold">Football AI Lab</h1>
            <p className="mt-1 max-w-2xl text-sm leading-6 text-slate-500">{T.subtitle}</p>
          </div>
          <div className="flex items-center gap-2">
            {/* Competition toggle */}
            <div className="flex rounded-md border border-slate-200 bg-white overflow-hidden shadow-sm">
              {(Object.keys(COMP_LABELS) as Competition[]).map((c) => (
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
                <p className="mt-2 max-w-sm text-sm text-slate-400">{T.emptyStateSub}</p>
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
                  <p className="mt-3 max-w-3xl text-sm leading-6 text-slate-200">
                    {matchReport?.executive_summary ?? scoutReport?.executive_summary}
                  </p>
                  <p className="mt-3 text-xs text-slate-500">
                    {T.source}: {matchReport?.data_source ?? scoutReport?.data_source}
                  </p>
                </div>

                {/* Match Prep sections */}
                {matchReport && <>
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
                </>}

                {/* Scout sections */}
                {scoutReport && <>
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

                  {scoutReport.how_they_score && scoutReport.how_they_score.length > 0 && (
                    <SectionCard title={T.howTheyScore} icon={<Target className="h-4 w-4" />}>
                      <BulletList items={scoutReport.how_they_score} />
                    </SectionCard>
                  )}

                  {scoutReport.probable_lineup && scoutReport.probable_lineup.length > 0 && (
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
