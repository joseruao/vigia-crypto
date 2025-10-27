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

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  const abortRef = useRef<AbortController | null>(null);
  const abortedRef = useRef(false);

  const API_URL =
    (process.env.NEXT_PUBLIC_API_URL?.trim() as string) ||
    'https://vigia-crypto-1.onrender.com';

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
  function shouldUseAlertsAPI(prompt: string) {
    const q = prompt.toLowerCase();
    return (
      q.includes('token') ||
      q.includes('listado') ||
      q.includes('listing') ||
      q.includes('exchange') ||
      q.includes('prediction') ||
      q.includes('previsão') ||
      q.includes('predição') ||
      q.includes('holders') ||
      q.includes('holding') ||
      q.includes('wallet') ||
      q.includes('score') ||
      q.includes('scoring')
    );
  }

  async function sendMessage(text?: string) {
    const content = (text ?? input).trim();
    if (!content || loading) return;

    let id = activeId;
    if (!id) id = newConversation();

    addMessage({ role: 'user', content });
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
          // stream = text/plain; alerts = application/json
          'Accept': useAlerts ? 'application/json' : 'text/plain',
        },
        body: JSON.stringify({ prompt: content }),
        signal: controller.signal,
      });

      if (!res.ok) {
        const textErr = await res.text().catch(() => '');
        throw new Error(`HTTP ${res.status} ${res.statusText} — ${textErr}`);
      }

      if (useAlerts) {
        const data = await res.json().catch(() => ({}));
        addMessage({
          role: 'assistant',
          content: data?.answer ?? '⚠️ Sem resposta',
        });
      } else {
        const reader = res.body?.getReader();
        if (!reader) throw new Error('Sem stream');

        // cria a msg vazia do assistant que iremos preencher
        addMessage({ role: 'assistant', content: '' });

        let acc = '';
        const decoder = new TextDecoder();

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          const chunkStr = decoder.decode(value, { stream: true });
          if (!chunkStr) continue;

          acc += chunkStr;
          if (!gotFirstChunk && acc.length > 0) setGotFirstChunk(true);
          updateLastAssistantMessage(acc);
        }
      }
    } catch (e: any) {
      if (!abortedRef.current) {
        const msg = e?.message ?? '⚠️ Erro ao comunicar com a API';
        console.error(e);
        addMessage({ role: 'assistant', content: msg });
      }
    } finally {
      setLoading(false);
      abortRef.current = null;
      abortedRef.current = false;
      setGotFirstChunk(false);
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

  return (
    <div className="h-screen flex flex-col bg-white">
      {/* TOP BAR minimal */}
      <div className="border-b border-gray-200 bg-white/90 backdrop-blur supports-[backdrop-filter]:bg-white/60">
        <div className="max-w-5xl mx-auto px-4 py-3 flex items-center justify-between">
          <div className="text-sm font-medium text-gray-700">Vigia Crypto</div>
          <div className="text-xs text-gray-500">joseruao.com</div>
        </div>
      </div>

      {/* Área das mensagens */}
      <div className="flex-1 overflow-y-auto">
        {!hasMessages && !loading ? (
          <div className="h-full flex flex-col items-center justify-center px-4">
            <img src="/logo_full.png" alt="José Ruão.io" className="h-28 mb-6 opacity-90" />
            <div className="text-sm text-gray-600 mb-4">
              Que tokens achas que vão ser listados?
            </div>
            <div className="w-full max-w-2xl">
              <Suggestions
                visible={!hasMessages}
                onSelect={(t) => {
                  setInput(t);
                  setTimeout(() => sendMessage(t), 80);
                }}
              />
            </div>
          </div>
        ) : (
          <div className="px-4 py-6">
            <div className="max-w-3xl mx-auto space-y-4">
              {active?.messages.map((m, i) => (
                <div
                  key={i}
                  className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}
                >
                  <div
                    className={`max-w-[85%] rounded-2xl px-4 py-2.5 text-[0.92rem] leading-relaxed shadow-sm ${
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
                  <div className="max-w-[85%] rounded-2xl px-4 py-2.5 text-sm bg-gray-50 text-gray-600 border border-gray-200">
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
        <div className="max-w-5xl mx-auto p-4">
          <div className="relative flex items-end gap-2">
            {loading && (
              <button
                onClick={stopStreaming}
                className="absolute left-3 bottom-3 p-1 rounded hover:bg-gray-100 text-gray-500"
                title="Parar geração"
              >
                <CircleStop className="h-5 w-5" />
              </button>
            )}

            <textarea
              ref={inputRef}
              className={`flex-1 resize-none bg-gray-50 text-gray-900 rounded-2xl px-4 py-3 pr-12 outline-none border border-gray-200 focus:border-blue-500 transition-colors ${
                loading ? 'pl-10' : ''
              }`}
              rows={1}
              placeholder="Escreve a tua mensagem..."
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={onKeyDown}
              disabled={loading}
            />

            <button
              onClick={() => sendMessage()}
              disabled={loading || !input.trim()}
              className={`absolute right-2 bottom-2 p-2 rounded-full transition-colors ${
                input.trim() && !loading
                  ? 'bg-blue-600 text-white hover:bg-blue-700'
                  : 'bg-gray-300 text-gray-500 cursor-not-allowed'
              }`}
              title="Enviar mensagem"
            >
              <Send className="h-4 w-4" />
            </button>
          </div>

          <div className="text-[11px] text-gray-500 text-center mt-2">
            Vigia Crypto pode cometer erros. Verifica informações importantes.
          </div>
        </div>
      </div>
    </div>
  );
}
