// frontend/src/components/ChatWindow.tsx
'use client';

import { useEffect, useRef, useState } from 'react';
import { v4 as uuidv4 } from 'uuid';
import { Suggestions } from '@/components/Suggestions';
import { TradingViewChart } from '@/components/TradingViewChart';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { useChatHistoryContext } from '@/lib/ChatHistoryProvider';
import { CircleStop, Send } from 'lucide-react';

function extractCoinFromAnalysis(content: string): string | null {
  const match = content.match(/(?:##\s+🎯\s+|#\s+📊\s+)([A-Z0-9]+)\s+[—–-]/);
  if (match) return match[1];
  const match2 = content.match(/Analise tecnica de\s+([A-Z0-9]+)/i);
  if (match2) return match2[1];
  return null;
}

export function ChatWindow() {
  const {
    active,
    addMessage,
    updateLastAssistantMessage,
    activeId,
  } = useChatHistoryContext();

  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [gotFirstChunk, setGotFirstChunk] = useState(false);
  const [lang, setLang] = useState<'pt' | 'en'>('pt');

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  const abortRef = useRef<AbortController | null>(null);
  const abortedRef = useRef(false);

  useEffect(() => {
    const browserLang = navigator.language.toLowerCase();
    setLang(browserLang.startsWith('pt') ? 'pt' : 'en');
  }, []);

  // Em desenvolvimento, usa localhost se estiver em localhost
  const getApiUrl = () => {
    // Se estiver em localhost, sempre usa API local (ignora env var)
    if (typeof window !== 'undefined' && window.location.hostname === 'localhost') {
      return 'http://localhost:8000';
    }
    // Senão, usa env var ou produção
    return process.env.NEXT_PUBLIC_API_URL?.trim() || 'https://vigia-crypto-1.onrender.com';
  };
  
  const API_URL = getApiUrl();

  // Warm-up para evitar cold start do Render
  useEffect(() => {
    fetch(`${API_URL}/`).catch(() => {});
  }, [API_URL]);

  // Auto-scroll para a última mensagem
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [active?.messages, loading]);

  // Auto-resize do textarea
  useEffect(() => {
    if (inputRef.current) {
      inputRef.current.style.height = 'auto';
      inputRef.current.style.height = Math.min(inputRef.current.scrollHeight, 120) + 'px';
    }
  }, [input]);

  // Heurística para usar a API de alerts (prediction/holdings/etc.)
  // NÃO usar para análise de moedas (coin analysis)
  function shouldUseAlertsAPI(prompt: string) {
    const q = prompt.toLowerCase();
    // Only route to alerts/ask for explicit top100 keyword or very specific opportunity phrases
    // General "melhores oportunidades hoje" should go to chat/stream (backend handles top100 routing)
    const isTop100Question = q.includes('top100') || q.includes('top 100');
    const isListingQuestion =
      q.includes('listado') ||
      q.includes('listing') ||
      q.includes('listagem') ||
      q.includes('previsao de listing') ||
      q.includes('vão ser') ||
      q.includes('vao ser') ||
      q.includes('vai ser') ||
      q.includes('acumular') ||
      q.includes('accumulate') ||
      (q.includes('exchange') && q.includes('token')) ||
      (q.includes('achas') && (q.includes('token') || q.includes('listado')));
    const isBuyWatchlistQuestion =
      (q.includes('comprar') || q.includes('compra') || q.includes('aconselhas') || q.includes('recomendas') || q.includes('oportunidade')) &&
      (q.includes('moeda') || q.includes('moedas') || q.includes('crypto') || q.includes('cripto') || q.includes('token'));

    if (isTop100Question || isListingQuestion || isBuyWatchlistQuestion) {
      return true;
    }
    
    // Se for pedido de análise de moeda, usar chat/stream
    if (q.includes('analisa-me') || q.includes('analisa') || q.includes('análise')) {
      if (q.includes('moeda') || q.includes('coin') || q.includes('criptomoeda') || q.includes('cryptocurrency')) {
        return false; // Usar chat/stream para análise de moedas
      }
    }
    
    // Detectar perguntas sobre tokens/listings
    return (
      q.includes('listado') ||
      q.includes('listing') ||
      q.includes('vão ser') ||
      q.includes('vao ser') ||
      q.includes('vai ser') ||
      q.includes('exchange') ||
	      q.includes('prediction') ||
	      q.includes('previsao') ||
	      q.includes('predicao') ||
      q.includes('previsão') ||
      q.includes('predição') ||
      q.includes('holders') ||
      q.includes('holding') ||
      q.includes('wallet') ||
      q.includes('scoring') ||
      isTop100Question ||
      isBuyWatchlistQuestion ||
      isListingQuestion
    );
  }

  async function sendMessage(text?: string) {
    const content = (text ?? input).trim();
    if (!content || loading) return;

    const convId = activeId ?? uuidv4();
    const history = (active?.messages ?? []).slice(-8);

    addMessage({ role: 'user', content }, convId);
    setInput('');
    setLoading(true);
    setGotFirstChunk(false);

    try {
      abortedRef.current = false;
      const controller = new AbortController();
      abortRef.current = controller;

      const useAlerts = shouldUseAlertsAPI(content);
      const url = useAlerts
        ? `${API_URL}/alerts/ask`
        : `${API_URL}/chat/stream`;

      const res = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': useAlerts ? 'application/json' : 'text/plain',
        },
        body: JSON.stringify({ prompt: content, history }),
        signal: controller.signal,
      });

      if (!res.ok) {
        const textErr = await res.text().catch(() => '');
        throw new Error(`HTTP ${res.status} ${res.statusText} — ${textErr}`);
      }

      if (useAlerts) {
        const data = await res.json().catch(() => ({}));

        let answer = data?.answer;
        if (!answer && data?.error) answer = `Erro: ${data.error}`;
        if (!answer && Array.isArray(data?.items) && data.items.length > 0) {
          answer = `Encontrei ${data.items.length} resultado(s).`;
        }
        if (!answer) answer = '⚠️ Sem resposta do servidor. Verifica os logs do backend.';

        addMessage({
          role: 'assistant',
          content: answer,
        }, convId);
      } else {
        const reader = res.body?.getReader();
        if (!reader) throw new Error('Sem stream');

        addMessage({ role: 'assistant', content: '' }, convId);

        let acc = '';
        const decoder = new TextDecoder();

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          const chunkStr = decoder.decode(value, { stream: true });
          if (!chunkStr) continue;

          acc += chunkStr;
          if (!gotFirstChunk && acc.length > 0) setGotFirstChunk(true);
          updateLastAssistantMessage(acc, convId);
        }

        if (!acc.trim()) {
          updateLastAssistantMessage('⚠️ Sem resposta do servidor. Pode ser cold start do Render — tenta novamente em alguns segundos.', convId);
        }
      }
    } catch (e: unknown) {
      if (!abortedRef.current) {
        const msg = e instanceof Error ? e.message : '⚠️ Erro ao comunicar com a API';
        addMessage({ role: 'assistant', content: msg }, convId);
      }
    } finally {
      setLoading(false);
      abortRef.current = null;
      abortedRef.current = false;
      setGotFirstChunk(false);
      setTimeout(() => inputRef.current?.focus(), 0);
    }
  }

  function stopStreaming() {
    if (abortRef.current) {
      abortedRef.current = true;
      abortRef.current.abort();
    }
  }

  function onKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  }

  const hasMessages = (active?.messages.length ?? 0) > 0;
  const copy = lang === 'pt'
    ? {
        placeholder: 'Escreve a tua mensagem...',
        disclaimer: 'Pode cometer erros. Verifica informações importantes. Conteúdo informativo; não é aconselhamento financeiro.',
      }
    : {
        placeholder: 'Ask anything about crypto markets...',
        disclaimer: 'May make mistakes. Check important information. Informational only; not financial advice.',
      };

  return (
    <div className="flex h-screen min-h-screen flex-col bg-white supports-[height:100dvh]:h-[100dvh] supports-[min-height:100dvh]:min-h-[100dvh]">
      {/* Área das mensagens */}
      <div className="min-h-0 flex-1 overflow-y-auto overscroll-contain">
        {!hasMessages && !loading ? (
          <div className="relative min-h-[calc(100vh-104px)] overflow-hidden px-4 py-10 sm:py-14">
            <div className="relative mx-auto flex min-h-[calc(100vh-184px)] w-full max-w-3xl flex-col items-center justify-center text-center">
              <img src="/logo_full.png" alt="José Ruão.com" className="mb-8 h-48 w-auto max-w-[90vw] object-contain opacity-95 sm:h-72" />
            <div className="w-full max-w-2xl">
              <Suggestions
                visible={!hasMessages}
                onSelect={(t) => sendMessage(t)}
              />
            </div>
            </div>
          </div>
        ) : (
          <div className="px-3 py-4 sm:px-4 sm:py-6">
            <div className="max-w-3xl mx-auto space-y-4">
              {active?.messages.map((m, i) => (
                <div
                  key={i}
                  className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}
                >
                  <div className={`max-w-[92%] sm:max-w-[85%] ${m.role === 'user' ? '' : 'w-full'}`}>
                    <div
                      className={`rounded-2xl px-4 py-2.5 text-[0.92rem] leading-relaxed shadow-sm ${
                        m.role === 'user'
                          ? 'bg-blue-600 text-white'
                          : 'bg-gray-50 text-gray-800 border border-gray-200'
                      }`}
                    >
                      <ReactMarkdown remarkPlugins={[remarkGfm]}>
                        {m.content}
                      </ReactMarkdown>
                    </div>
                    {m.role === 'assistant' && (() => {
                      const coin = extractCoinFromAnalysis(m.content);
                      return coin ? <TradingViewChart coin={coin} /> : null;
                    })()}
                  </div>
                </div>
              ))}

              {loading && !gotFirstChunk && (
                <div className="flex justify-start">
                  <div className="max-w-[92%] rounded-2xl px-4 py-2.5 text-sm bg-gray-50 text-gray-600 border border-gray-200 sm:max-w-[85%]">
                    <span className="animate-pulse">● ● ●</span>
                  </div>
                </div>
              )}

              <div ref={messagesEndRef} />
            </div>
          </div>
        )}
      </div>

      {/* Input fixo — sticky no fundo, safe area para mobile */}
      <div
        className="sticky bottom-0 z-10 shrink-0 border-t border-gray-200 bg-white/95 backdrop-blur supports-[backdrop-filter]:bg-white/70"
        style={{ paddingBottom: 'env(safe-area-inset-bottom, 0px)' }}
      >
        <div className="max-w-5xl mx-auto p-3 sm:p-4">
          <div className="flex items-end gap-2 rounded-2xl border border-gray-200 bg-white px-3 py-2 shadow-sm transition-colors focus-within:border-blue-500">
            {loading && (
              <button
                onClick={stopStreaming}
                className="mb-1 rounded p-1 text-gray-500 hover:bg-gray-100"
                title="Parar geração"
              >
                <CircleStop className="h-5 w-5" />
              </button>
            )}

            <textarea
              ref={inputRef}
              className="max-h-32 flex-1 resize-none bg-transparent px-1 py-1.5 text-gray-900 outline-none placeholder:text-gray-400"
              rows={1}
              placeholder={copy.placeholder}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={onKeyDown}
              disabled={loading}
            />

            <button
              onClick={() => sendMessage()}
              disabled={!input.trim() || loading}
              className="mb-0.5 rounded-full p-2 text-white transition-colors bg-blue-600 hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed"
              title="Enviar mensagem"
            >
              <Send className="h-4 w-4" />
            </button>
          </div>

          <div className="text-[11px] text-gray-500 text-center mt-2">
            {copy.disclaimer}
          </div>
        </div>
      </div>
    </div>
  );
}
