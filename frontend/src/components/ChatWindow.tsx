'use client';

import { useEffect, useRef, useState } from 'react';
import { Suggestions } from '@/components/Suggestions';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { useChatHistoryContext } from '@/lib/ChatHistoryProvider';
import { CircleStop } from 'lucide-react';

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
  const listRef = useRef<HTMLDivElement>(null);
  const abortRef = useRef<AbortController | null>(null);
  const abortedRef = useRef(false);

  const API_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://127.0.0.1:8000';

  useEffect(() => {
    listRef.current?.scrollTo({ top: listRef.current.scrollHeight, behavior: 'smooth' });
  }, [active?.messages, loading]);

  async function sendMessage(text?: string) {
    const content = (text ?? input).trim();
    if (!content || loading) return;

    let id = activeId;
    if (!id) id = newConversation();

    // mensagem do utilizador
    addMessage({ role: 'user', content });
    setInput('');
    setLoading(true);
    setGotFirstChunk(false);

    try {
      abortedRef.current = false;
      const controller = new AbortController();
      abortRef.current = controller;

      const res = await fetch(`${API_URL}/chat/stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt: content }),
        signal: controller.signal,
      });

      const reader = res.body?.getReader();
      if (!reader) throw new Error('Sem stream');

      let buffer = '';
      // cria placeholder do assistente
      addMessage({ role: 'assistant', content: '' });

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        // ✅ não usamos trim() → preserva espaços
        const chunkStr = new TextDecoder().decode(value);
        if (!chunkStr) continue;

        buffer += chunkStr;
        if (!gotFirstChunk && buffer.length > 0) setGotFirstChunk(true);
        updateLastAssistantMessage(buffer);
      }
    } catch (e: any) {
      if (!abortedRef.current) {
        console.error(e);
        addMessage({ role: 'assistant', content: '⚠️ Erro no streaming' });
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
    <div className="flex flex-col w-full items-center">
      {/* Logo + sugestões antes da 1ª mensagem */}
      {!hasMessages && !loading && (
        <div className="flex flex-col items-center justify-center mb-10">
          <img src="/logo_full.png" alt="José Ruão.io" className="h-96 mb-12" />
          <Suggestions
            visible={!hasMessages}
            onSelect={(t) => {
              setInput(t);
              sendMessage(t);
            }}
          />
        </div>
      )}

      {/* Área de mensagens */}
      <div
        ref={listRef}
        className="flex-1 overflow-y-auto p-4 space-y-4 mb-4 w-full"
        style={{ maxHeight: '70vh' }}
      >
        {active?.messages.map((m, i) => (
          <div key={i} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div
              className={`max-w-[80%] rounded-2xl px-4 py-2 text-sm prose prose-invert ${
                m.role === 'user' ? 'bg-black text-white' : 'bg-zinc-100 text-black'
              }`}
            >
              <ReactMarkdown remarkPlugins={[remarkGfm]}>{m.content}</ReactMarkdown>
            </div>
          </div>
        ))}

        {/* indicador enquanto não veio o 1º chunk */}
        {loading && !gotFirstChunk && (
          <div className="flex justify-start">
            <div className="max-w-[80%] rounded-2xl px-4 py-2 text-sm bg-zinc-100 text-black">
              AI está a escrever…
            </div>
          </div>
        )}
      </div>

      {/* Input + Stop/Send */}
      <div className="flex items-center gap-2 border-t border-zinc-200 bg-white p-3 w-full">
        {loading ? (
          <button
            onClick={stopStreaming}
            className="p-2 rounded hover:bg-zinc-100"
            title="Parar geração"
          >
            <CircleStop className="h-5 w-5" />
          </button>
        ) : null}

        <textarea
          className="flex-1 resize-none bg-zinc-100 text-black rounded-lg px-3 py-2 outline-none"
          rows={1}
          placeholder="Escreve a tua mensagem..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={onKeyDown}
        />

        <button
          onClick={() => sendMessage()}
          disabled={loading || !input.trim()}
          className="p-2 text-black hover:text-emerald-500 disabled:opacity-50"
          title="Enviar"
        >
          <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 12h14M12 5l7 7-7 7" />
          </svg>
        </button>
      </div>
    </div>
  );
}
