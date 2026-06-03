'use client';

import {
  Activity,
  CandlestickChart,
  CircleHelp,
  Radar,
  Search,
  TrendingUp,
} from 'lucide-react';
import type { LucideIcon } from 'lucide-react';

type Suggestion = {
  label: string;
  description: string;
  prompt: string;
  icon: LucideIcon;
  tone: string;
};

type Props = { visible: boolean; onSelect: (text: string) => void };

const SUGGESTIONS: Record<'pt' | 'en', Suggestion[]> = {
  pt: [
    {
      label: 'Começar aqui',
      description: 'O que o radar deteta e que perguntas podes fazer.',
      prompt: 'O que fazes e como me podes ajudar?',
      icon: CircleHelp,
      tone: 'text-zinc-700 bg-zinc-100',
    },
    {
      label: 'Top100 com melhor setup',
      description: 'Moedas perto de suporte, RSI útil e risco controlado.',
      prompt: 'Quais do top100 estao perto do suporte?',
      icon: TrendingUp,
      tone: 'text-emerald-700 bg-emerald-50',
    },
    {
      label: 'Possíveis listings',
      description: 'Sinais que aparecem em wallets de exchanges.',
      prompt: 'Que tokens as exchanges estao a acumular que ainda nao foram listados?',
      icon: Radar,
      tone: 'text-blue-700 bg-blue-50',
    },
    {
      label: 'Movimentos de wallets',
      description: 'Últimos holdings grandes detetados on-chain.',
      prompt: 'Mostra holdings recentes',
      icon: Activity,
      tone: 'text-amber-700 bg-amber-50',
    },
    {
      label: 'Analisar uma moeda',
      description: 'Entrada, alvo, stop, RSI e tendencia de uma crypto.',
      prompt: 'Analisa BTC',
      icon: CandlestickChart,
      tone: 'text-violet-700 bg-violet-50',
    },
    {
      label: 'O que mudou hoje',
      description: 'Maiores alterações no ranking técnico top100.',
      prompt: 'O que mudou no top100 desde ontem?',
      icon: Search,
      tone: 'text-sky-700 bg-sky-50',
    },
  ],
  en: [
    {
      label: 'Start here',
      description: 'What this radar detects and which questions to ask.',
      prompt: 'What do you do and how can you help me?',
      icon: CircleHelp,
      tone: 'text-zinc-700 bg-zinc-100',
    },
    {
      label: 'Best top100 setups',
      description: 'Coins near support with useful RSI and controlled risk.',
      prompt: 'Which top 100 coins are near support?',
      icon: TrendingUp,
      tone: 'text-emerald-700 bg-emerald-50',
    },
    {
      label: 'Possible listings',
      description: 'Signals appearing in monitored exchange wallets.',
      prompt: 'Which tokens are exchanges accumulating that are not yet listed?',
      icon: Radar,
      tone: 'text-blue-700 bg-blue-50',
    },
    {
      label: 'Wallet movements',
      description: 'Latest large on-chain exchange-wallet holdings.',
      prompt: 'Show recent exchange wallet holdings',
      icon: Activity,
      tone: 'text-amber-700 bg-amber-50',
    },
    {
      label: 'Analyze a coin',
      description: 'Entry, target, stop, RSI and trend for one crypto.',
      prompt: 'Analyze BTC',
      icon: CandlestickChart,
      tone: 'text-violet-700 bg-violet-50',
    },
    {
      label: 'What changed today',
      description: 'Largest moves in the top100 technical ranking.',
      prompt: 'What changed in the top100 since yesterday?',
      icon: Search,
      tone: 'text-sky-700 bg-sky-50',
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
    <div className="mb-4 grid w-full gap-3 sm:grid-cols-2 lg:grid-cols-3">
      {items.map((s) => (
        <button
          key={s.prompt}
          onClick={() => onSelect(s.prompt)}
          className="group min-h-28 rounded-2xl border border-zinc-200 bg-white/90 px-4 py-4 text-left shadow-sm backdrop-blur transition hover:-translate-y-0.5 hover:border-zinc-300 hover:bg-white hover:shadow-md"
        >
          <span className={`mb-3 flex h-8 w-8 items-center justify-center rounded-xl ${s.tone}`}>
            <s.icon className="h-4 w-4" />
          </span>
          <span className="block text-sm font-semibold text-zinc-950 sm:text-base">{s.label}</span>
          <span className="mt-1.5 block text-xs leading-snug text-zinc-500 sm:text-sm">{s.description}</span>
        </button>
      ))}
    </div>
  );
}
