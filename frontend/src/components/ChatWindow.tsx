import { useEffect, useRef, useState } from 'react';
import { Suggestions } from '@/components/Suggestions';
import { useChatHistory } from '@/lib/useChatHistory';

export function ChatWindow() {
  const { active, addMessage } = useChatHistory();
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const listRef = useRef<HTMLDivElement>(null);

  const API_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://127.0.0.1:8000';

  useEffect(() => {
    listRef.current?.scrollTo({ top: listRef.current.scrollHeight, behavior: 'smooth' });
  }, [active?.messages, loading]);

  async function sendMessage(text?: string) {
    const content = (text ?? input).trim();
    if (!content || loading) return;

    addMessage({ role: 'user', content });
    setInput('');
    setLoading(true);

    try {
      const res = await fetch(`${API_URL}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt: content }),
      });
      const data = await res.json();
      addMessage({ role: 'assistant', content: data?.answer ?? '(sem resposta)' });
    } catch {
      addMessage({ role: 'assistant', content: '⚠️ Erro ao ligar ao backend' });
    } finally {
      setLoading(false);
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
      {!hasMessages && (
        <div className="flex flex-col items-center justify-center mb-10">
          <img src="/logo_full.png" alt="José Ruão.io" className="h-64 mb-8" />
          <Suggestions visible={!hasMessages} onSelect={(t) => sendMessage(t)} />
        </div>
      )}

      <div ref={listRef} className="flex-1 overflow-y-auto p-4 space-y-4 mb-4 w-full" style={{ maxHeight: '70vh' }}>
        {active?.messages.map((m, i) => (
          <div key={i} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div className={`max-w-[80%] rounded-2xl px-4 py-2 text-sm
              ${m.role === 'user' ? 'bg-black text-white' : 'bg-zinc-100 text-black'}`}>
              {m.content}
            </div>
          </div>
        ))}
        {loading && <div className="text-zinc-400 italic">AI está a escrever…</div>}
      </div>

      <div className="flex items-center border-t border-zinc-200 bg-white p-3 w-full">
        <textarea
          className="flex-1 resize-none bg-transparent text-black outline-none px-2"
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
        >
          ➤
        </button>
      </div>
    </div>
  );
}
