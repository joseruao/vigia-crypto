'use client';

import { useEffect, useState } from 'react';
import { ChatWindow } from '@/components/ChatWindow';
import { PredictionsPanel } from '@/components/PredictionsPanel';
import { getPredictions } from '@/lib/api';
import type { Prediction } from '@/lib/types';

export default function Page() {
  const [predictions, setPredictions] = useState<Prediction[]>([]);

  useEffect(() => {
    console.log("API_URL =>", process.env.NEXT_PUBLIC_API_URL);

    (async () => {
      try {
        const data = await getPredictions();
        if (Array.isArray(data)) {
          // Para já vamos mostrar >=70 para garantir que aparecem
          setPredictions(data.filter((p) => (p.score ?? 0) >= 70));
        }
      } catch {
        setPredictions([]);
      }
    })();
  }, []);

  return (
    <main className="flex flex-col items-center justify-center min-h-screen bg-white px-4">
      <div className="w-full max-w-3xl space-y-6">
        {predictions.length > 0 && <PredictionsPanel predictions={predictions} />}
        <ChatWindow />
      </div>
    </main>
  );
}
