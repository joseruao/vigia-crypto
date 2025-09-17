'use client';

import { useEffect, useState } from 'react';
import { ChatWindow } from '@/components/ChatWindow';
import { PredictionsPanel } from '@/components/PredictionsPanel';
import { getPredictions } from '@/lib/api';
import type { Prediction } from '@/lib/types';

export default function Page() {
  const [predictions, setPredictions] = useState<Prediction[]>([]);

  useEffect(() => {
    (async () => {
      try {
        const data = await getPredictions();
        if (Array.isArray(data)) {
          setPredictions(data.filter((p) => (p.certeza ?? 0) >= 90));
        }
      } catch {
        setPredictions([]);
      }
    })();
  }, []);

  return (
    <main className="relative flex flex-col flex-1">
      {/* Quadrado canto superior direito */}
      <div className="absolute right-4 top-4 w-64">
        <PredictionsPanel predictions={predictions} />
      </div>

      {/* Chat central */}
      <div className="flex flex-1 items-center justify-center">
        <div className="w-full max-w-3xl">
          <ChatWindow />
        </div>
      </div>
    </main>
  );
}
