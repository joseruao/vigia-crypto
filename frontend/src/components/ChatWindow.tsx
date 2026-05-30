// frontend/src/components/ChatWindow.tsx
'use client';

import { useEffect, useRef, useState } from 'react';
import { Suggestions } from '@/components/Suggestions';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { useChatHistoryContext } from '@/lib/ChatHistoryProvider';
import { CircleStop, Send } from 'lucide-react';

export function ChatWindow() {
  const {
    active,
    addMessage,
    updateLastAssistantMessage,
    newConversation,
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
    const isTop100Question = q.includes('top100') || q.includes('top 100');
    const isListingQuestion =
      q.includes('listado') ||
      q.includes('listing') ||
      q.includes('vÃ£o ser') ||
      q.includes('vão ser') ||
      q.includes('vao ser') ||
      q.includes('vai ser') ||
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
      q.includes('token') ||
      q.includes('listado') ||
      q.includes('listing') ||
      q.includes('vão ser') ||
      q.includes('vao ser') ||
      q.includes('vai ser') ||
      q.includes('exchange') ||
      q.includes('prediction') ||
      q.includes('previsão') ||
      q.includes('predição') ||
      q.includes('holders') ||
      q.includes('holding') ||
      q.includes('wallet') ||
      q.includes('score') ||
      q.includes('scoring') ||
      isTop100Question ||
      isBuyWatchlistQuestion ||
      isListingQuestion
    );
  }

  async function sendMessage(text?: string) {
    const content = (text ?? input).trim();
    if (!content || loading) return;

    let id = activeId;
    if (!id) id = newConversation();
    const history = (active?.messages ?? []).slice(-8);

    addMessage({ role: 'user', content }, id);
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

      console.log('📤 Fazendo fetch para:', url);
      console.log('📤 Payload:', { prompt: content });
      console.log('📤 useAlerts:', useAlerts);
      
      const res = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          // stream = text/plain; alerts = application/json
          'Accept': useAlerts ? 'application/json' : 'text/plain',
        },
        body: JSON.stringify({ prompt: content, history }),
        signal: controller.signal,
      });
      
      console.log('📥 Resposta recebida:', res.status, res.statusText);

      if (!res.ok) {
        const textErr = await res.text().catch(() => '');
        throw new Error(`HTTP ${res.status} ${res.statusText} — ${textErr}`);
      }

      if (useAlerts) {
        const data = await res.json().catch((e) => {
          console.error('❌ Erro ao parsear JSON:', e);
          return {};
        });
        
        console.log('📥 Resposta completa recebida:', data);
        console.log('📥 data.answer:', data?.answer);
        console.log('📥 data.error:', data?.error);
        console.log('📥 data.ok:', data?.ok);
        console.log('📥 data.debug:', data?.debug);
        
        // Tenta várias formas de obter a resposta
        let answer = data?.answer;
        if (!answer && data?.error) {
          answer = `Erro: ${data.error}`;
        }
        if (!answer && data?.items && Array.isArray(data.items) && data.items.length > 0) {
          // Se não há answer mas há items, formata manualmente
          answer = `Encontrei ${data.items.length} resultado(s).`;
        }
        if (!answer) {
          // Mostra informações de debug se disponíveis
          const debugInfo = data?.debug;
          if (debugInfo) {
            answer = `⚠️ Sem resposta do servidor.\n\n📊 Debug:\n- URL existe: ${debugInfo.url_exists} (${debugInfo.url_length} chars)\n- KEY existe: ${debugInfo.key_exists} (${debugInfo.key_length} chars)\n- supa.ok(): ${debugInfo.supa_ok}\n- has_get_url: ${debugInfo.has_get_url}\n- has_get_key: ${debugInfo.has_get_key}`;
          } else {
            answer = '⚠️ Sem resposta do servidor. Verifica os logs do backend.';
          }
        }
        
        console.log('📤 Resposta final a mostrar:', answer);
        addMessage({
          role: 'assistant',
          content: answer,
        }, id);
      } else {
        const reader = res.body?.getReader();
        if (!reader) throw new Error('Sem stream');

        // cria a msg vazia do assistant que iremos preencher
        addMessage({ role: 'assistant', content: '' }, id);

        let acc = '';
        const decoder = new TextDecoder();

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          const chunkStr = decoder.decode(value, { stream: true });
          if (!chunkStr) continue;

          acc += chunkStr;
          if (!gotFirstChunk && acc.length > 0) setGotFirstChunk(true);
          updateLastAssistantMessage(acc, id);
        }

        // Se o stream terminou sem conteúdo, mostrar mensagem de fallback
        if (!acc.trim()) {
          updateLastAssistantMessage('⚠️ Sem resposta do servidor. Pode ser cold start do Render — tenta novamente em alguns segundos.');
        }
      }
    } catch (e: unknown) {
      if (!abortedRef.current) {
        const msg = e instanceof Error ? e.message : '⚠️ Erro ao comunicar com a API';
        console.error(e);
        addMessage({ role: 'assistant', content: msg }, id);
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
    <div className="min-h-screen flex flex-col bg-white">
      {/* Área das mensagens */}
      <div className="flex-1 overflow-y-auto">
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
                  <div
                    className={`max-w-[92%] rounded-2xl px-4 py-2.5 text-[0.92rem] leading-relaxed shadow-sm sm:max-w-[85%] ${
                      m.role === 'user'
                        ? 'bg-blue-600 text-white'
                        : 'bg-gray-50 text-gray-800 border border-gray-200'
                    }`}
                  >
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>
                      {m.content}
                    </ReactMarkdown>
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

      {/* Input fixo */}
      <div className="border-t border-gray-200 bg-white/95 backdrop-blur supports-[backdrop-filter]:bg-white/70">
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

            {input.trim() && !loading ? (
              <button
                onClick={() => sendMessage()}
                className="mb-0.5 rounded-full bg-blue-600 p-2 text-white transition-colors hover:bg-blue-700"
                title="Enviar mensagem"
              >
                <Send className="h-4 w-4" />
              </button>
            ) : null}
          </div>

          <div className="text-[11px] text-gray-500 text-center mt-2">
            {copy.disclaimer}
          </div>
        </div>
      </div>
    </div>
  );
}
