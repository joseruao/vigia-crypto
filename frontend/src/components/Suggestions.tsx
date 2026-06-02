'use client';

type Suggestion = {
  label: string;
  description: string;
  prompt: string;
};

type Props = { visible: boolean; onSelect: (text: string) => void };

const SUGGESTIONS: Record<'pt' | 'en', Suggestion[]> = {
  pt: [
    {
      label: 'O que este site faz?',
      description: 'Resumo simples das ferramentas e dados disponiveis.',
      prompt: 'O que fazes e como me podes ajudar?',
    },
    {
      label: 'Moedas interessantes hoje',
      description: 'Ranking tecnico do top100 com suporte, RSI e momentum.',
      prompt: 'Quais do top100 estao perto do suporte?',
    },
    {
      label: 'Possiveis listings',
      description: 'Tokens que exchanges acumulam antes de listar.',
      prompt: 'Que tokens as exchanges estao a acumular que ainda nao foram listados?',
    },
    {
      label: 'Holdings de exchanges',
      description: 'Maiores posicoes recentes em wallets monitorizadas.',
      prompt: 'Mostra holdings recentes',
    },
    {
      label: 'Analisar uma moeda',
      description: 'Entrada, alvo, stop, RSI e tendencia de uma crypto.',
      prompt: 'Analisa BTC',
    },
    {
      label: 'Mudancas desde ontem',
      description: 'O que subiu ou desceu no ranking tecnico diario.',
      prompt: 'O que mudou no top100 desde ontem?',
    },
  ],
  en: [
    {
      label: 'What does this site do?',
      description: 'A simple overview of the tools and data available.',
      prompt: 'What do you do and how can you help me?',
    },
    {
      label: 'Interesting coins today',
      description: 'Top100 technical ranking using support, RSI and momentum.',
      prompt: 'Which top 100 coins are near support?',
    },
    {
      label: 'Possible listings',
      description: 'Tokens exchanges may be accumulating before listing.',
      prompt: 'Which tokens are exchanges accumulating that are not yet listed?',
    },
    {
      label: 'Exchange holdings',
      description: 'Largest recent positions in monitored exchange wallets.',
      prompt: 'Show recent exchange wallet holdings',
    },
    {
      label: 'Analyze a coin',
      description: 'Entry, target, stop, RSI and trend for one crypto.',
      prompt: 'Analyze BTC',
    },
    {
      label: 'Changes since yesterday',
      description: 'What moved in the daily technical ranking.',
      prompt: 'What changed in the top100 since yesterday?',
    },
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
          className="min-h-24 rounded-xl border border-zinc-300 bg-white/85 px-4 py-3 text-left shadow-sm backdrop-blur transition hover:border-zinc-500 hover:bg-white"
        >
          <span className="block text-sm font-semibold text-zinc-900 sm:text-base">{s.label}</span>
          <span className="mt-1 block text-xs leading-snug text-zinc-500 sm:text-sm">{s.description}</span>
        </button>
      ))}
    </div>
  );
}
