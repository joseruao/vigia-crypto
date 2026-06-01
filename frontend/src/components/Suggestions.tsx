'use client';

type Props = { visible: boolean; onSelect: (text: string) => void };

const SUGGESTIONS: Record<'pt' | 'en', { label: string; prompt: string }[]> = {
  pt: [
    { label: '📊 Top100 perto do suporte', prompt: 'Quais do top100 estao perto do suporte?' },
    { label: '🛡️ Top100 menor risco', prompt: 'Quais do top100 tem menos risco?' },
    { label: '🔍 RSI mais baixo agora', prompt: 'Quais do top100 tem RSI mais baixo?' },
    { label: '🏦 Tokens com listing previsto', prompt: 'Que tokens achas que vao ser listados em breve?' },
    { label: '📈 Analisa BTC', prompt: 'Analisa BTC' },
    { label: '🔎 Analisa SOL', prompt: 'Analisa SOL' },
  ],
  en: [
    { label: '📊 Top100 near support', prompt: 'Which top 100 coins are near support?' },
    { label: '🛡️ Top100 lower risk', prompt: 'Which top 100 coins have lower risk?' },
    { label: '🔍 Lowest RSI now', prompt: 'Which top 100 coins have the lowest RSI?' },
    { label: '🏦 Upcoming listings', prompt: 'Which tokens look close to a major exchange listing?' },
    { label: '📈 Analyze BTC', prompt: 'Analyze BTC' },
    { label: '🔎 Analyze SOL', prompt: 'Analyze SOL' },
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
