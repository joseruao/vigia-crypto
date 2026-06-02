'use client';

type Props = { visible: boolean; onSelect: (text: string) => void };

const SUGGESTIONS: Record<'pt' | 'en', { label: string; prompt: string }[]> = {
  pt: [
    { label: 'Perto do suporte', prompt: 'Quais do top100 estao perto do suporte?' },
    { label: 'RSI mais baixo', prompt: 'Quais do top100 tem RSI mais baixo?' },
    { label: 'Potenciais listings', prompt: 'Que tokens as exchanges estao a acumular que ainda nao foram listados?' },
    { label: 'Holdings recentes', prompt: 'Mostra holdings recentes' },
    { label: 'Analisa BTC', prompt: 'Analisa BTC' },
    { label: 'O que mudou hoje?', prompt: 'O que mudou no top100 desde ontem?' },
    { label: 'Como funciona?', prompt: 'O que fazes e como me podes ajudar?' },
  ],
  en: [
    { label: 'Near support', prompt: 'Which top 100 coins are near support?' },
    { label: 'Lowest RSI', prompt: 'Which top 100 coins have the lowest RSI?' },
    { label: 'Potential listings', prompt: 'Which tokens are exchanges accumulating that are not yet listed?' },
    { label: 'Recent holdings', prompt: 'Show recent exchange wallet holdings' },
    { label: 'Analyze BTC', prompt: 'Analyze BTC' },
    { label: 'What changed today?', prompt: 'What changed in the top100 since yesterday?' },
    { label: 'How it works', prompt: 'What do you do and how can you help me?' },
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
      {items.map((s) => (
        <button
          key={s.prompt}
          onClick={() => onSelect(s.prompt)}
          className="rounded-xl border border-zinc-300 bg-white/85 px-4 py-3 text-left text-sm shadow-sm backdrop-blur transition hover:border-zinc-500 hover:bg-white sm:text-base"
        >
          {s.label}
        </button>
      ))}
    </div>
  );
}
