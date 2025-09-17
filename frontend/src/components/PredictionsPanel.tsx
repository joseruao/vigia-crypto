'use client';

type Prediction = { exchange: string; token: string; certeza?: number; confidence?: number };

export function PredictionsPanel({ predictions }: { predictions: Prediction[] }) {
  if (!predictions || predictions.length === 0) return null;

  return (
    <div className="rounded-lg border border-zinc-300 bg-white p-3 text-xs text-black shadow">
      <div className="flex items-center gap-2 mb-2">
        <img src="/logo_small.png" alt="JR" className="h-5 w-5" />
        <span className="text-sm font-semibold">Listings</span>
      </div>

      {predictions.map((p, i) => {
        const pct = typeof p.certeza === 'number' ? p.certeza : Math.round((p.confidence ?? 0) * 100);
        return (
          <div key={i} className="flex justify-between mb-1">
            <span>{p.token} · {p.exchange}</span>
            <span>{pct}%</span>
          </div>
        );
      })}
    </div>
  );
}
