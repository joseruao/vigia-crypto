'use client';

type Props = { visible: boolean; onSelect: (text: string) => void };

const SUGGESTIONS: Record<'pt' | 'en', { label: string; prompt: string }[]> = {
  pt: [
    { label: '📊 Perto do suporte', prompt: 'Quais do top100 estao perto do suporte?' },
    { label: '🔍 RSI mais baixo', prompt: 'Quais do top100 tem RSI mais baixo?' },
    { label: '🏦 Potencial de listing', prompt: 'Que tokens as exchanges estao a acumular que ainda nao foram listados?' },
    { label: '📈 Analisa BTC', prompt: 'Analisa BTC' },
    { label: '📈 Analisa ETH', prompt: 'Analisa ETH' },
  ],
  en: [
    { label: '📊 Near support', prompt: 'Which top 100 coins are near support?' },
    { label: '🔍 Lowest RSI', prompt: 'Which top 100 coins have the lowest RSI?' },
    { label: '🏦 Listing potential', prompt: 'Which tokens are exchanges accumulating that are not yet listed?' },
    { label: '📈 Analyze BTC', prompt: 'Analyze BTC' },
    { label: '📈 Analyze ETH', prompt: 'Analyze ETH' },
  ],
};

function getLang(): 'pt' | 'en' {
  if (typeof navigator === 'undefined') return 'pt';
  return navigator.language.toLowerCase().startsWith('pt') ? 'pt' : 'en';
}

export function Suggestions({ visible, onSelect }: Props) {
  if (!visible) return null;
  const items = SUGGESTIONS[getLang()];

  return (
    <div className="mb-4 grid w-full gap-2 sm:grid-cols-2 lg:grid-cols-3">
      {items.map((s, i) => (
        <button
          key={i}
          onClick={() => onSelect(s.prompt)}
          className="rounded-xl border border-zinc-300 bg-white/85 px-4 py-3 text-left text-sm shadow-sm backdrop-blur transition hover:border-zinc-500 hover:bg-white sm:text-base"
        >
          {s.label}
        </button>
      ))}
    </div>
  );
}
