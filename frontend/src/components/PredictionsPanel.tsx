'use client';

import { useEffect, useState } from 'react';
import { getPredictions } from '@/lib/api';
import { Prediction } from '@/lib/types';

export function PredictionsPanel() {
  const [predictions, setPredictions] = useState<Prediction[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const data = await getPredictions();
        setPredictions(data);
      } catch (e) {
        console.error("Erro ao carregar predictions:", e);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  if (loading) {
    return (
      <div className="p-4 text-sm text-gray-500">
        A carregar previsões...
      </div>
    );
  }

  if (predictions.length === 0) {
    return (
      <div className="p-4 text-sm text-gray-500">
        Nenhuma previsão disponível de momento.
      </div>
    );
  }

  return (
    <div className="p-4 space-y-3">
      <h2 className="text-lg font-semibold mb-2">🚨 Predictions</h2>
      {predictions.map((p) => (
        <div
          key={p.id}
          className="border border-zinc-200 rounded-lg p-3 shadow-sm bg-white"
        >
          <div className="font-medium">
            {p.token} <span className="text-xs text-gray-500">({p.exchange})</span>
          </div>
          <div className="text-xs text-gray-600 mt-1 space-y-1">
            <div>💰 Valor: ${p.value_usd?.toLocaleString() ?? '—'}</div>
            <div>💧 Liquidez: ${p.liquidity?.toLocaleString() ?? '—'}</div>
            <div>📊 Volume 24h: ${p.volume_24h?.toLocaleString() ?? '—'}</div>
            <div>⭐ Score: {p.score != null ? p.score.toFixed(1) : '—'}</div>
            <div>🛒 Txns buys: {p.txns_buys ?? 0}</div>
            <div>💸 Txns sells: {p.txns_sells ?? 0}</div>
            <div>👥 Holders top: {p.holders_concentration?.toFixed(1) ?? 0}%</div>
          </div>
          <div className="mt-2 text-xs">
            🔗 <a
              href={p.pair_url || `https://coingecko.com/pt/moedas/${p.token.toLowerCase()}`}
              target="_blank"
              rel="noopener noreferrer"
              className="text-emerald-600 hover:underline"
            >
              Ver token
            </a>
          </div>
        </div>
      ))}
    </div>
  );
}
