'use client';

type Props = { visible: boolean; onSelect: (text: string) => void };

// Apenas 2 sugestões por idioma
const SUGGESTIONS: Record<'pt' | 'en', string[]> = {
  pt: [
    'Que tokens achas que vão ser listados?',
    'Analise BTC',
  ],
  en: [
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
    <div className="w-full grid gap-2 sm:grid-cols-2 mb-4">
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
