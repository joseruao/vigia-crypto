'use client';

import type { ReactNode } from 'react';
import { useEffect, useState } from 'react';
import {
  AlertTriangle,
  CheckCircle2,
  Download,
  FileText,
  Gavel,
  Loader2,
  Lock,
  Scale,
  ShieldCheck,
  Upload,
} from 'lucide-react';
import { DevilsAdvocateReport, analyzeDevilsAdvocate } from '@/lib/api';

type Lang = 'pt' | 'en';
const MAX_FILE_BYTES = 12 * 1024 * 1024;

function ListBlock({ items, empty = '—' }: { items?: string[]; empty?: string }) {
  const safeItems = Array.isArray(items) ? items : [];
  if (!safeItems.length) return <p className="text-sm text-slate-400">{empty}</p>;
  return (
    <ul className="space-y-2 text-sm leading-6 text-slate-700">
      {safeItems.map((item, index) => (
        <li key={index} className="flex gap-2">
          <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-slate-900" />
          <span>{item}</span>
        </li>
      ))}
    </ul>
  );
}

function ReportSection({
  title,
  icon,
  children,
  tone = 'default',
}: {
  title: string;
  icon: ReactNode;
  children: ReactNode;
  tone?: 'default' | 'warn' | 'good' | 'dark';
}) {
  const toneClass = {
    default: 'border-slate-200 bg-white text-slate-900',
    warn: 'border-amber-200 bg-amber-50 text-amber-950',
    good: 'border-emerald-200 bg-emerald-50 text-emerald-950',
    dark: 'border-slate-900 bg-slate-950 text-white',
  }[tone];

  return (
    <section className={`rounded-lg border p-5 shadow-sm ${toneClass}`}>
      <div className="mb-3 flex items-center gap-2">
        <span className={tone === 'dark' ? 'text-white' : 'text-slate-700'}>{icon}</span>
        <h2 className="text-sm font-bold uppercase tracking-wide">{title}</h2>
      </div>
      {children}
    </section>
  );
}

export default function DevilsAdvocatePage() {
  const [file, setFile] = useState<File | null>(null);
  const [language, setLanguage] = useState<Lang>('pt');
  const [accessCode, setAccessCode] = useState('');
  const [report, setReport] = useState<DevilsAdvocateReport | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  // Local (desktop/Ollama) vs cloud (joseruao.com/OpenAI) — drives the privacy notice.
  const [isLocal, setIsLocal] = useState(false);

  useEffect(() => {
    const saved = localStorage.getItem('devils_advocate_access_code');
    if (saved) setAccessCode(saved);
    setIsLocal(window.location.hostname === 'localhost');
  }, []);

  // Persist the code as soon as it's typed — not only after a successful
  // analysis — so it survives reloads even while debugging failed requests.
  useEffect(() => {
    if (accessCode.trim()) {
      localStorage.setItem('devils_advocate_access_code', accessCode.trim());
    }
  }, [accessCode]);

  async function handleAnalyze() {
    if (!file || loading) return;
    if (!accessCode.trim()) {
      setError('Introduza o código de acesso para usar a ferramenta.');
      return;
    }
    if (file.size > MAX_FILE_BYTES) {
      setError('O ficheiro é demasiado grande. Limite máximo: 12 MB.');
      return;
    }
    setLoading(true);
    setError('');
    setReport(null);
    try {
      const result = await analyzeDevilsAdvocate({
        file,
        jurisdiction: 'Portugal',
        legal_area: 'Fiscal',
        document_type: 'Documento fiscal',
        represented_side: 'Contribuinte',
        objective: 'Encontrar argumentos, contra-argumentos, riscos, falhas, prova em falta e pontos jurídicos que exigem verificação humana',
        language,
        accessCode: accessCode.trim(),
      });
      setReport(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erro ao analisar documento.');
    } finally {
      setLoading(false);
    }
  }

  const canSubmit = Boolean(file) && accessCode.trim().length > 0 && !loading;
  const legalReferences = report?.legal_references_used ?? [];
  const riskMatrix = report?.risk_matrix ?? [];
  const unverifiedLegalPoints = report?.unverified_legal_points ?? [];
  const caseTheory = report?.case_theory ?? [];
  const opponentTheory = report?.opponent_theory ?? [];
  const burdenAndProof = report?.burden_and_proof ?? [];
  const hearingQuestions = report?.hearing_questions ?? [];
  const nextActions = report?.next_actions ?? [];

  return (
    <main className="min-h-screen bg-slate-50 text-slate-950">
      <style
        dangerouslySetInnerHTML={{
          __html:
            '@media print { html, body { background: #fff !important; } * { -webkit-print-color-adjust: exact; print-color-adjust: exact; } }',
        }}
      />
      <div className="mx-auto flex w-full max-w-7xl flex-col gap-6 px-4 py-6 sm:px-6 lg:px-8">
        <header className="flex flex-wrap items-start justify-between gap-4 border-b border-slate-200 pb-5">
          <div>
            <h1 className="text-3xl font-semibold">Devil&apos;s Advocate</h1>
            <p className="mt-1 text-sm font-medium text-red-700">
              Every argument deserves an opponent before reaching the courtroom.
            </p>
          </div>
          <button
            type="button"
            onClick={() => setLanguage((value) => (value === 'pt' ? 'en' : 'pt'))}
            className="rounded-md border border-slate-200 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 shadow-sm transition hover:border-slate-400 print:hidden"
          >
            {language === 'pt' ? 'PT' : 'EN'}
          </button>
        </header>

        <div className="grid gap-6 xl:grid-cols-[360px_1fr] print:block">
          <section className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm print:hidden">
            <div className="mb-5 flex items-center gap-2">
              <span className="flex h-8 w-8 items-center justify-center rounded-md bg-red-50 text-red-700">
                <Scale className="h-4 w-4" />
              </span>
              <h2 className="text-base font-semibold">Análise</h2>
            </div>

            <div className="space-y-4">
              <label className="block">
                <span className="mb-1.5 flex items-center gap-1.5 text-sm font-medium text-slate-700">
                  <Lock className="h-3.5 w-3.5" /> Código de acesso
                </span>
                <input
                  type="password"
                  value={accessCode}
                  onChange={(event) => setAccessCode(event.target.value)}
                  placeholder="Código privado de beta"
                  autoComplete="off"
                  className="block w-full rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-800 shadow-sm focus:border-slate-500 focus:outline-none"
                />
              </label>

              <label className="block">
                <span className="mb-1.5 block text-sm font-medium text-slate-700">Documento</span>
                <div className="rounded-lg border border-dashed border-slate-300 bg-slate-50 p-4">
                  <input
                    type="file"
                    accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                    onChange={(event) => setFile(event.target.files?.[0] ?? null)}
                    className="block w-full text-sm text-slate-600 file:mr-3 file:rounded-md file:border-0 file:bg-slate-950 file:px-3 file:py-2 file:text-sm file:font-semibold file:text-white"
                  />
                  {file && (
                    <p className="mt-3 flex items-center gap-2 text-xs font-medium text-slate-500">
                      <FileText className="h-3.5 w-3.5" />
                      {file.name}
                    </p>
                  )}
                </div>
              </label>

              <div className="rounded-md border border-slate-200 bg-slate-50 p-3 text-xs leading-5 text-slate-500">
                Portugal · Fiscal · análise adversarial com pontos não verificados destacados
                <br />
                Repetir o mesmo ficheiro usa cache temporária no backend durante os testes.
              </div>

              {isLocal ? (
                <div className="flex gap-2 rounded-md border border-emerald-200 bg-emerald-50 p-3 text-xs leading-5 text-emerald-800">
                  <ShieldCheck className="mt-0.5 h-4 w-4 shrink-0" />
                  <span>
                    <strong>Privacidade:</strong> esta versão corre inteiramente na sua máquina
                    (modelo local). O documento <strong>não é enviado para nenhum serviço externo</strong> —
                    nada sai do computador.
                  </span>
                </div>
              ) : (
                <div className="flex gap-2 rounded-md border border-amber-200 bg-amber-50 p-3 text-xs leading-5 text-amber-800">
                  <ShieldCheck className="mt-0.5 h-4 w-4 shrink-0" />
                  <span>
                    <strong>Privacidade:</strong> o texto do documento é enviado para um modelo de
                    IA de terceiros (OpenAI, EUA) para análise. Não carregue documentos cujo conteúdo
                    não possa partilhar com um subcontratante. Confirme o cumprimento do segredo
                    profissional e do RGPD antes de usar dados reais de clientes.
                  </span>
                </div>
              )}

              {error && (
                <div className="flex gap-2 rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700">
                  <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
                  <span>{error}</span>
                </div>
              )}

              <button
                type="button"
                onClick={handleAnalyze}
                disabled={!canSubmit}
                className="inline-flex h-14 w-full items-center justify-center gap-2 rounded-lg bg-red-800 px-4 text-base font-bold text-white shadow-md transition hover:bg-red-900 disabled:cursor-not-allowed disabled:bg-slate-300"
              >
                {loading ? <Loader2 className="h-5 w-5 animate-spin" /> : <Upload className="h-5 w-5" />}
                {loading ? 'A analisar...' : 'Analisar documento'}
              </button>
            </div>
          </section>

          <section className="min-h-[640px] rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
            {!report ? (
              <div className="flex h-full min-h-[560px] flex-col items-center justify-center text-center">
                <div className="flex h-14 w-14 items-center justify-center rounded-lg bg-red-50 text-red-700">
                  <Gavel className="h-7 w-7" />
                </div>
                <h2 className="mt-4 text-xl font-semibold">Relatório adversarial</h2>
                <p className="mt-2 max-w-md text-sm leading-6 text-slate-500">
                  Upload de PDF/DOCX, contraditório, auditoria e pontos jurídicos não verificados.
                </p>
              </div>
            ) : (
              <div className="space-y-5">
                <div className="flex justify-end print:hidden">
                  <button
                    type="button"
                    onClick={() => window.print()}
                    className="inline-flex items-center gap-2 rounded-md border border-slate-300 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 shadow-sm transition hover:border-slate-400"
                  >
                    <Download className="h-3.5 w-3.5" /> Exportar PDF
                  </button>
                </div>

                <ReportSection title="Sumário" icon={<Scale className="h-4 w-4" />} tone="dark">
                  <p className="whitespace-pre-line text-sm leading-6 text-slate-100">{report.executive_summary}</p>
                  <p className="mt-4 text-xs text-slate-400">
                    {report.document_name} · {report.jurisdiction} · {report.legal_area} · {report.represented_side}
                  </p>
                </ReportSection>

                <ReportSection title="Aviso de fontes" icon={<ShieldCheck className="h-4 w-4" />} tone="warn">
                  <p className="text-sm leading-6">{report.source_note}</p>
                  <p className="mt-2 text-sm leading-6 font-semibold">{report.confidence_note}</p>
                </ReportSection>

                {report.content_truncated && (
                  <ReportSection title="Documento truncado" icon={<AlertTriangle className="h-4 w-4" />} tone="warn">
                    <p className="text-sm leading-6">
                      O documento excedeu o limite analisável (80 páginas ou ~65 000 caracteres) e foi
                      cortado. A análise cobre apenas a parte inicial — divida o documento e analise os
                      restantes blocos separadamente.
                    </p>
                  </ReportSection>
                )}

                {unverifiedLegalPoints.length > 0 && (
                  <ReportSection title="Não verificado nas fontes" icon={<AlertTriangle className="h-4 w-4" />} tone="warn">
                    <ListBlock items={unverifiedLegalPoints} />
                  </ReportSection>
                )}

                {(caseTheory.length > 0 || opponentTheory.length > 0) && (
                  <div className="grid gap-5 lg:grid-cols-2">
                    <ReportSection title="Teoria do caso" icon={<Scale className="h-4 w-4" />} tone="good">
                      <ListBlock items={caseTheory} />
                    </ReportSection>

                    <ReportSection title="Teoria da contraparte" icon={<Gavel className="h-4 w-4" />}>
                      <ListBlock items={opponentTheory} />
                    </ReportSection>
                  </div>
                )}

                <div className="grid gap-5 lg:grid-cols-2">
                  <ReportSection title="Factos extraídos" icon={<FileText className="h-4 w-4" />}>
                    <ListBlock items={report.extracted_facts} />
                  </ReportSection>

                  <ReportSection title="Perguntas ao advogado" icon={<CheckCircle2 className="h-4 w-4" />}>
                    <ListBlock items={report.questions_for_lawyer} />
                  </ReportSection>
                </div>

                <div className="grid gap-5 lg:grid-cols-2">
                  <ReportSection title="Advocate" icon={<Scale className="h-4 w-4" />} tone="good">
                    <ListBlock items={report.advocate_argument} />
                  </ReportSection>

                  <ReportSection title="Opponent" icon={<Gavel className="h-4 w-4" />}>
                    <ListBlock items={report.opponent_argument} />
                  </ReportSection>
                </div>

                <ReportSection title="Audit" icon={<ShieldCheck className="h-4 w-4" />}>
                  <ListBlock items={report.audit_findings} />
                </ReportSection>

                {(burdenAndProof.length > 0 || hearingQuestions.length > 0) && (
                  <div className="grid gap-5 lg:grid-cols-2">
                    <ReportSection title="Ónus e prova" icon={<ShieldCheck className="h-4 w-4" />}>
                      <ListBlock items={burdenAndProof} />
                    </ReportSection>

                    <ReportSection title="Perguntas de confronto" icon={<Gavel className="h-4 w-4" />}>
                      <ListBlock items={hearingQuestions} />
                    </ReportSection>
                  </div>
                )}

                <div className="grid gap-5 lg:grid-cols-2">
                  <ReportSection title="Prova em falta" icon={<FileText className="h-4 w-4" />}>
                    <ListBlock items={report.missing_evidence} />
                  </ReportSection>

                  <ReportSection title="Fontes citadas no documento" icon={<FileText className="h-4 w-4" />}>
                    <ListBlock items={report.cited_sources_in_document} empty="Sem fontes identificadas no documento." />
                  </ReportSection>
                </div>

                {riskMatrix.length > 0 && (
                  <ReportSection title="Matriz de risco" icon={<AlertTriangle className="h-4 w-4" />}>
                    <div className="grid gap-3 sm:grid-cols-2">
                      {riskMatrix.map((risk, index) => (
                        <div key={index} className="rounded-md border border-slate-200 bg-slate-50 p-4">
                          <h3 className="mb-2 text-sm font-bold text-slate-900">{risk.title}</h3>
                          <ListBlock items={risk.points} />
                        </div>
                      ))}
                    </div>
                  </ReportSection>
                )}

                {nextActions.length > 0 && (
                  <ReportSection title="Próximos passos" icon={<CheckCircle2 className="h-4 w-4" />} tone="good">
                    <ListBlock items={nextActions} />
                  </ReportSection>
                )}

                <ReportSection title="Leis usadas em cada ponto" icon={<FileText className="h-4 w-4" />}>
                  {legalReferences.length > 0 ? (
                    <div className="space-y-3">
                      {legalReferences.map((ref, index) => (
                        <div key={index} className="rounded-md border border-slate-200 bg-slate-50 p-4">
                          <div className="mb-2 flex flex-wrap items-center gap-2">
                            <span className="rounded bg-slate-950 px-2 py-1 text-xs font-bold text-white">
                              {ref.source}
                            </span>
                            <span className="text-xs font-semibold uppercase tracking-wide text-slate-400">
                              {ref.status}
                            </span>
                          </div>
                          <p className="text-sm leading-6 text-slate-700">{ref.point}</p>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-sm leading-6 text-slate-500">
                      Nenhuma lei, artigo, prazo, taxa, decisão ou informação vinculativa foi usado como fonte verificada neste relatório.
                    </p>
                  )}
                </ReportSection>
              </div>
            )}
          </section>
        </div>
      </div>
    </main>
  );
}
