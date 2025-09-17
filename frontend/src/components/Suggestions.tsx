'use client';

type Props = { visible: boolean; onSelect: (text: string) => void };

const SUGGESTIONS: Record<'pt' | 'en', string[]> = {
  pt: [
    'Que tokens achas que vão ser listados?',
    'Quais são os sinais de listing na Binance esta semana?',
  ],
  en: [
    'Which tokens look close to a major exchange listing?',
    'What are the listing signals for Binance this week?',
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
    <div className="w-full grid gap-2 sm:grid-cols-2 mb-4">
      {items.map((s, i) => (
        <button
          key={i}
          onClick={() => onSelect(s)}
          className="rounded-2xl border border-zinc-800 px-4 py-3 text-left hover:bg-zinc-900/50"
        >
          {s}
        </button>
      ))}
    </div>
  );
}
