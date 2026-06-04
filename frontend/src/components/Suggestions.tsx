'use client';

import {
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
      label: 'Start here',
      description: 'What this radar detects.',
      prompt: 'What do you do and how can you help me?',
      icon: CircleHelp,
      tone: 'text-zinc-700 bg-zinc-100',
    },
    {
      label: 'Top100 setups',
      description: 'Coins near support today.',
      prompt: 'Which top100 coins are near support?',
      icon: TrendingUp,
      tone: 'text-emerald-700 bg-emerald-50',
    },
    {
      label: 'Unlisted token radar',
      description: 'Tokens not listed on that exchange yet.',
      prompt: 'Which tokens are in exchange wallets but not listed yet?',
      icon: Radar,
      tone: 'text-blue-700 bg-blue-50',
    },
    {
      label: 'Analyze a coin',
      description: 'Entry, target, stop and RSI.',
      prompt: 'Analyze BTC',
      icon: CandlestickChart,
      tone: 'text-violet-700 bg-violet-50',
    },
    {
      label: 'Daily changes',
      description: 'What improved in the top100.',
      prompt: 'What changed in the top100 since yesterday?',
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
      label: 'Unlisted token radar',
      description: 'Tokens not listed on that exchange yet.',
      prompt: 'Which tokens are exchanges accumulating that are not yet listed?',
      icon: Radar,
      tone: 'text-blue-700 bg-blue-50',
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
    <div className="mb-4 grid w-full grid-cols-2 gap-2 sm:gap-3 lg:grid-cols-3">
      {items.map((s) => (
        <button
          key={s.prompt}
          onClick={() => onSelect(s.prompt)}
          className="group min-h-24 rounded-2xl border border-zinc-200 bg-white/90 px-3 py-3 text-left shadow-sm backdrop-blur transition hover:-translate-y-0.5 hover:border-zinc-300 hover:bg-white hover:shadow-md sm:min-h-28 sm:px-4 sm:py-4"
        >
          <span className={`mb-2 flex h-8 w-8 items-center justify-center rounded-xl sm:mb-3 ${s.tone}`}>
            <s.icon className="h-4 w-4" />
          </span>
          <span className="block text-[0.82rem] font-semibold leading-tight text-zinc-950 sm:text-base">{s.label}</span>
          <span className="mt-1 block text-[0.72rem] leading-snug text-zinc-500 sm:mt-1.5 sm:text-sm">{s.description}</span>
        </button>
      ))}
    </div>
  );
}
