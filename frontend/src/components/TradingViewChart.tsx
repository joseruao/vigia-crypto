'use client';

import { useEffect, useRef } from 'react';

const SYMBOL_MAP: Record<string, string> = {
  BTC: 'BINANCE:BTCUSDT',
  ETH: 'BINANCE:ETHUSDT',
  SOL: 'BINANCE:SOLUSDT',
  BNB: 'BINANCE:BNBUSDT',
  XRP: 'BINANCE:XRPUSDT',
  ADA: 'BINANCE:ADAUSDT',
  AVAX: 'BINANCE:AVAXUSDT',
  DOGE: 'BINANCE:DOGEUSDT',
  DOT: 'BINANCE:DOTUSDT',
  LINK: 'BINANCE:LINKUSDT',
  MATIC: 'BINANCE:MATICUSDT',
  LTC: 'BINANCE:LTCUSDT',
  BCH: 'BINANCE:BCHUSDT',
  NEAR: 'BINANCE:NEARUSDT',
  APT: 'BINANCE:APTUSDT',
  ARB: 'BINANCE:ARBUSDT',
  OP: 'BINANCE:OPUSDT',
  SUI: 'BINANCE:SUIUSDT',
  ATOM: 'BINANCE:ATOMUSDT',
  UNI: 'BINANCE:UNIUSDT',
  AAVE: 'BINANCE:AAVEUSDT',
  PEPE: 'BINANCE:PEPEUSDT',
  SHIB: 'BINANCE:SHIBUSDT',
  WIF: 'BINANCE:WIFUSDT',
  BONK: 'BINANCE:BONKUSDT',
  FIL: 'BINANCE:FILUSDT',
  WLD: 'BINANCE:WLDUSDT',
  FET: 'BINANCE:FETUSDT',
  INJ: 'BINANCE:INJUSDT',
  TIA: 'BINANCE:TIAUSDT',
  JUP: 'BINANCE:JUPUSDT',
  HYPE: 'HYPERLIQUID:HYPEUSDC',
};

function resolveSymbol(coin: string): string {
  const upper = coin.toUpperCase();
  return SYMBOL_MAP[upper] ?? `BINANCE:${upper}USDT`;
}

type Props = { coin: string };

export function TradingViewChart({ coin }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const widgetRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!containerRef.current) return;

    // Clean up previous widget
    containerRef.current.innerHTML = '';

    const widget = document.createElement('div');
    widget.className = 'tradingview-widget-container__widget';
    widgetRef.current = widget;
    containerRef.current.appendChild(widget);

    const script = document.createElement('script');
    script.src = 'https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js';
    script.async = true;
    script.innerHTML = JSON.stringify({
      autosize: true,
      symbol: resolveSymbol(coin),
      interval: 'D',
      timezone: 'Etc/UTC',
      theme: 'light',
      style: '1',
      locale: 'pt',
      allow_symbol_change: false,
      calendar: false,
      support_host: 'https://www.tradingview.com',
      hide_top_toolbar: false,
      hide_legend: false,
      save_image: false,
      studies: ['RSI@tv-basicstudies', 'MACD@tv-basicstudies'],
    });

    containerRef.current.appendChild(script);

    return () => {
      if (containerRef.current) containerRef.current.innerHTML = '';
    };
  }, [coin]);

  return (
    <div className="mt-3 rounded-xl overflow-hidden border border-gray-200 shadow-sm">
      <div className="flex items-center justify-between px-3 py-2 bg-gray-50 border-b border-gray-200">
        <span className="text-xs font-medium text-gray-600">
          {coin} · Gráfico diário (TradingView)
        </span>
        <a
          href={`https://www.tradingview.com/chart/?symbol=${resolveSymbol(coin)}`}
          target="_blank"
          rel="noopener noreferrer"
          className="text-xs text-blue-500 hover:underline"
        >
          Abrir completo ↗
        </a>
      </div>
      <div
        ref={containerRef}
        className="tradingview-widget-container"
        style={{ height: '400px', width: '100%' }}
      />
    </div>
  );
}
