'use client';

type Props = { visible: boolean; onSelect: (text: string) => void };

const SUGGESTIONS: Record<'pt' | 'en', { label: string; prompt: string }[]> = {
  pt: [
    { label: '🔥 Melhores oportunidades hoje', prompt: 'Quais do top100 estao perto do suporte?' },
    { label: '📉 O que está barato agora?', prompt: 'Quais do top100 tem RSI mais baixo?' },
    { label: '🏦 Potenciais listings nas exchanges', prompt: 'Que tokens as exchanges estao a acumular que ainda nao foram listados?' },
    { label: '📈 Analisa BTC', prompt: 'Analisa BTC' },
    { label: '📊 O que mudou hoje?', prompt: 'O que mudou no top100 hoje?' },
    { label: '🔥 Melhor compra confirmada', prompt: 'Qual a melhor compra confirmada agora no top100?' },
    { label: '💡 O que é isto e como funciona?', prompt: 'O que fazes e como me podes ajudar?' },
  ],
  en: [
    { label: '🔥 Best opportunities today', prompt: 'Which top 100 coins are near support?' },
    { label: '📉 What is cheap right now?', prompt: 'Which top 100 coins have the lowest RSI?' },
    { label: '🏦 Potential exchange listings', prompt: 'Which tokens are exchanges accumulating that are not yet listed?' },
    { label: '📈 Analyze BTC', prompt: 'Analyze BTC' },
    { label: '📊 What changed today?', prompt: 'What changed in the top100 today?' },
    { label: '🔥 Best confirmed buy', prompt: 'What is the best confirmed buy in the top100 now?' },
    { label: '💡 What is this and how does it work?', prompt: 'What do you do and how can you help me?' },
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
