'use client';

type Props = { visible: boolean; onSelect: (text: string) => void };

const SUGGESTIONS: Record<'pt' | 'en', string[]> = {
  pt: [
    'Que moedas me aconselhas a analisar hoje do top100?',
    'Quais do top100 estao perto do suporte?',
    'Quais do top100 tem menos risco?',
    'Que tokens achas que vao ser listados?',
    'Analise BTC',
  ],
  en: [
    'Which top 100 coins should I analyze today?',
    'Which top 100 coins are near support?',
    'Which top 100 coins have lower risk?',
    'Which tokens look close to a major exchange listing?',
    'Analyze BTC',
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
          onClick={() => onSelect(s)}
          className="rounded-xl border border-zinc-300 bg-white/85 px-4 py-3 text-left text-sm shadow-sm backdrop-blur transition hover:border-zinc-500 hover:bg-white sm:text-base"
        >
          {s}
        </button>
      ))}
    </div>
  );
}
