'use client';

import { useEffect, useMemo, useState } from 'react';
import {
  AlertTriangle,
  BadgeEuro,
  CheckCircle2,
  FileSpreadsheet,
  Loader2,
  Lock,
  Scale,
  Upload,
} from 'lucide-react';
import {
  PmeProcurementAnalysis,
  PmeRecommendation,
  analyzePmeProcurement,
} from '@/lib/api';

const euro = new Intl.NumberFormat('pt-PT', {
  style: 'currency',
  currency: 'EUR',
  maximumFractionDigits: 2,
});

function asMoney(value: string | number | null | undefined) {
  const numeric = Number(value ?? 0);
  if (!Number.isFinite(numeric)) return euro.format(0);
  return euro.format(numeric);
}

function Stat({
  label,
  value,
  tone = 'default',
}: {
  label: string;
  value: string;
  tone?: 'default' | 'good' | 'warn';
}) {
  const toneClass = {
    default: 'border-slate-200 bg-white text-slate-950',
    good: 'border-emerald-200 bg-emerald-50 text-emerald-950',
    warn: 'border-amber-200 bg-amber-50 text-amber-950',
  }[tone];
  return (
    <div className={`rounded-lg border p-4 shadow-sm ${toneClass}`}>
      <p className="text-xs font-semibold uppercase tracking-wide opacity-70">{label}</p>
      <p className="mt-2 text-2xl font-bold">{value}</p>
    </div>
  );
}

function RecommendationRow({ rec }: { rec: PmeRecommendation }) {
  const [open, setOpen] = useState(false);
  return (
    <>
      <tr className="border-b border-slate-100 align-top">
        <td className="px-4 py-4">
          <div className="font-semibold text-slate-950">{rec.product}</div>
          <button
            type="button"
            onClick={() => setOpen((value) => !value)}
            className="mt-2 inline-flex items-center gap-1 text-xs font-semibold text-slate-500 hover:text-slate-900"
          >
            <Scale className="h-3.5 w-3.5" />
            {open ? 'Fechar alternativas' : 'Ver alternativas'}
          </button>
        </td>
        <td className="px-4 py-4 font-semibold text-emerald-800">{rec.recommended_supplier}</td>
        <td className="px-4 py-4 font-semibold text-slate-900">
          <div>{asMoney(rec.price)}</div>
          <div className="mt-1 text-xs font-medium text-slate-400">
            qtd. {Number(rec.requested_quantity ?? 1).toLocaleString('pt-PT')}
          </div>
        </td>
        <td className="px-4 py-4 text-sm leading-6 text-slate-600">{rec.reason}</td>
        <td className="px-4 py-4 text-right font-bold text-emerald-800">
          <div>{asMoney(rec.estimated_savings)}</div>
          <div className="mt-1 text-xs font-medium text-slate-400">
            custo {asMoney(rec.estimated_total_cost)}
          </div>
        </td>
      </tr>
      {open && (
        <tr className="border-b border-slate-100 bg-slate-50">
          <td colSpan={5} className="px-4 py-4">
            <div className="overflow-hidden rounded-lg border border-slate-200 bg-white">
              <table className="w-full min-w-[720px] text-left text-sm">
                <thead className="bg-slate-100 text-xs uppercase tracking-wide text-slate-500">
                  <tr>
                    <th className="px-3 py-2">Fornecedor</th>
                    <th className="px-3 py-2">Produto</th>
                    <th className="px-3 py-2">Preço</th>
                    <th className="px-3 py-2">Valor ofertas</th>
                    <th className="px-3 py-2">Custo efetivo</th>
                    <th className="px-3 py-2">Condições</th>
                  </tr>
                </thead>
                <tbody>
                  {rec.alternatives.map((item, index) => (
                    <tr key={`${item.supplier}-${item.product}-${index}`} className="border-t border-slate-100">
                      <td className="px-3 py-2 font-semibold text-slate-800">{item.supplier}</td>
                      <td className="px-3 py-2 text-slate-600">{item.product}</td>
                      <td className="px-3 py-2">{asMoney(item.unit_price)}</td>
                      <td className="px-3 py-2 text-emerald-800">
                        {asMoney(item.commercial_value)}
                      </td>
                      <td className="px-3 py-2 font-semibold">{asMoney(item.effective_unit_price)}</td>
                      <td className="px-3 py-2 text-slate-500">
                        {item.commercial_terms?.length
                          ? item.commercial_terms.map((term) => term.label).join(', ')
                          : item.promotions || item.notes || '-'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </td>
        </tr>
      )}
    </>
  );
}

export default function PmePage() {
  const [files, setFiles] = useState<File[]>([]);
  const [needsText, setNeedsText] = useState('');
  const [commercialValuesText, setCommercialValuesText] = useState(
    'copos=0.80\ntacas=1.20\njarros=3.00\nguarda sol=25.00'
  );
  const [accessCode, setAccessCode] = useState('');
  const [isLocal, setIsLocal] = useState(true);
  const [analysis, setAnalysis] = useState<PmeProcurementAnalysis | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const fileNames = useMemo(() => files.map((file) => file.name).join(', '), [files]);
  const canAnalyze = files.length > 0 && !loading && (isLocal || accessCode.trim().length > 0);

  useEffect(() => {
    if (typeof window !== 'undefined') {
      setIsLocal(window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1');
      const saved = localStorage.getItem('pme_access_code');
      if (saved) setAccessCode(saved);
    }
  }, []);

  async function handleAnalyze() {
    if (!canAnalyze) return;
    if (!isLocal && accessCode.trim()) {
      localStorage.setItem('pme_access_code', accessCode.trim());
    }
    setLoading(true);
    setError('');
    setAnalysis(null);
    try {
      const result = await analyzePmeProcurement({
        files,
        needsText,
        commercialValuesText,
        accessCode: isLocal ? '' : accessCode.trim(),
      });
      setAnalysis(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'A análise falhou.');
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="min-h-screen bg-stone-50 text-slate-950">
      <div className="mx-auto flex w-full max-w-7xl flex-col gap-6 px-4 py-6 sm:px-6 lg:px-8">
        <header className="flex flex-wrap items-center justify-between gap-4 border-b border-stone-200 pb-5">
          <div>
            <h1 className="text-3xl font-semibold">PME</h1>
            <p className="mt-1 text-sm font-medium text-emerald-800">Find hidden money.</p>
          </div>
          <div className="flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs font-bold uppercase tracking-wide text-slate-500 shadow-sm">
            <CheckCircle2 className="h-4 w-4 text-emerald-700" />
            Compras semanais
          </div>
        </header>

        <div className="grid gap-6 xl:grid-cols-[360px_1fr]">
          <section className="rounded-lg border border-stone-200 bg-white p-5 shadow-sm">
            <div className="mb-5 flex items-center gap-2">
              <span className="flex h-9 w-9 items-center justify-center rounded-md bg-emerald-50 text-emerald-800">
                <FileSpreadsheet className="h-5 w-5" />
              </span>
              <h2 className="text-base font-semibold">Catálogos</h2>
            </div>

            <div className="space-y-4">
              {!isLocal && (
                <label className="block">
                  <span className="mb-1.5 flex items-center gap-1.5 text-sm font-medium text-slate-700">
                    <Lock className="h-3.5 w-3.5" /> Código de acesso
                  </span>
                  <input
                    type="password"
                    value={accessCode}
                    onChange={(event) => setAccessCode(event.target.value)}
                    placeholder="Código privado"
                    autoComplete="off"
                    className="block w-full rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-800 shadow-sm focus:border-emerald-600 focus:outline-none"
                  />
                </label>
              )}

              <label className="block">
                <span className="mb-1.5 block text-sm font-medium text-slate-700">Ficheiros</span>
                <div className="rounded-lg border border-dashed border-slate-300 bg-stone-50 p-4">
                  <input
                    type="file"
                    multiple
                    accept=".csv,.tsv,.txt,.pdf,.docx,text/csv,text/tab-separated-values,text/plain,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                    onChange={(event) => setFiles(Array.from(event.target.files ?? []))}
                    className="block w-full text-sm text-slate-600 file:mr-3 file:rounded-md file:border-0 file:bg-slate-950 file:px-3 file:py-2 file:text-sm file:font-semibold file:text-white"
                  />
                  {fileNames && (
                    <p className="mt-3 text-xs font-medium leading-5 text-slate-500">{fileNames}</p>
                  )}
                </div>
              </label>

              <label className="block">
                <span className="mb-1.5 block text-sm font-medium text-slate-700">
                  Lista de compra da semana <span className="font-normal text-slate-400">(opcional)</span>
                </span>
                <textarea
                  value={needsText}
                  onChange={(event) => setNeedsText(event.target.value)}
                  rows={5}
                  placeholder={'20; Coca Cola 24x33cl\n10; Super Bock 20L\n5; Agua 1.5L'}
                  className="block w-full resize-none rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-800 shadow-sm focus:border-emerald-600 focus:outline-none"
                />
              </label>

              <label className="block">
                <span className="mb-1.5 block text-sm font-medium text-slate-700">
                  Valor das ofertas <span className="font-normal text-slate-400">(editável)</span>
                </span>
                <textarea
                  value={commercialValuesText}
                  onChange={(event) => setCommercialValuesText(event.target.value)}
                  rows={4}
                  className="block w-full resize-none rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-800 shadow-sm focus:border-emerald-600 focus:outline-none"
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
                onClick={handleAnalyze}
                disabled={!canAnalyze}
                className="inline-flex h-13 w-full items-center justify-center gap-2 rounded-lg bg-emerald-800 px-4 text-base font-bold text-white shadow-md transition hover:bg-emerald-900 disabled:cursor-not-allowed disabled:bg-slate-300"
              >
                {loading ? <Loader2 className="h-5 w-5 animate-spin" /> : <Upload className="h-5 w-5" />}
                {loading ? 'A processar...' : 'Comparar compras'}
              </button>

              <div className="rounded-lg border border-slate-200 bg-slate-50 p-4 text-xs leading-5 text-slate-600">
                <p className="font-semibold text-slate-800">Colunas aceites</p>
                <p className="mt-1">fornecedor, produto, descrição, quantidade, unidade, preço, total, promoções, notas</p>
              </div>
            </div>
          </section>

          <section className="space-y-5">
            <div className="grid gap-4 md:grid-cols-3">
              <Stat
                label="Poupança estimada"
                value={asMoney(analysis?.estimated_savings_week)}
                tone="good"
              />
              <Stat label="Produtos comparados" value={String(analysis?.products_compared ?? 0)} />
              <Stat label="Linhas lidas" value={String(analysis?.total_items ?? 0)} tone="warn" />
            </div>

            {analysis?.warnings?.length ? (
              <div className="rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
                <div className="mb-2 flex items-center gap-2 font-semibold">
                  <AlertTriangle className="h-4 w-4" />
                  Atenção
                </div>
                <ul className="space-y-1">
                  {analysis.warnings.map((warning, index) => (
                    <li key={index}>{warning}</li>
                  ))}
                </ul>
              </div>
            ) : null}

            <div className="overflow-hidden rounded-lg border border-stone-200 bg-white shadow-sm">
              <div className="flex items-center justify-between gap-3 border-b border-stone-200 px-5 py-4">
                <div className="flex items-center gap-2">
                  <BadgeEuro className="h-5 w-5 text-emerald-800" />
                  <h2 className="text-base font-semibold">Recomendações</h2>
                </div>
              </div>

              {analysis && analysis.recommendations.length > 0 ? (
                <div className="overflow-x-auto">
                  <table className="w-full min-w-[920px] text-left">
                    <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
                      <tr>
                        <th className="px-4 py-3">Produto</th>
                        <th className="px-4 py-3">Fornecedor</th>
                        <th className="px-4 py-3">Preço</th>
                        <th className="px-4 py-3">Razão</th>
                        <th className="px-4 py-3 text-right">Poupança</th>
                      </tr>
                    </thead>
                    <tbody>
                      {analysis.recommendations.map((rec, index) => (
                        <RecommendationRow key={`${rec.product}-${index}`} rec={rec} />
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <div className="flex min-h-[420px] flex-col items-center justify-center px-6 text-center">
                  <div className="flex h-14 w-14 items-center justify-center rounded-lg bg-emerald-50 text-emerald-800">
                    <Scale className="h-7 w-7" />
                  </div>
                  <h3 className="mt-4 text-xl font-semibold">Sem comparação ainda</h3>
                  <p className="mt-2 max-w-md text-sm leading-6 text-slate-500">
                    Carregue catálogos com produtos equivalentes de pelo menos dois fornecedores.
                  </p>
                </div>
              )}
            </div>
          </section>
        </div>
      </div>
    </main>
  );
}
