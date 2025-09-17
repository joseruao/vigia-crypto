'use client';

import { useChatHistory } from '@/lib/useChatHistory';
import { Trash2 } from 'lucide-react';

export function Sidebar() {
  const { conversations, activeId, newConversation, selectConversation, deleteConversation } = useChatHistory();

  return (
    <aside className="hidden md:flex w-64 flex-col border-r border-zinc-300 bg-white text-black">
      {/* Logo pequeno */}
      <div className="p-4">
        <img src="/logo_small.png" alt="JR" className="h-6 w-auto" />
      </div>

      {/* Botão novo chat */}
      <button
        onClick={newConversation}
        className="mx-3 mb-3 rounded-lg border border-black px-3 py-2 text-sm hover:bg-black hover:text-white"
      >
        + Novo Chat
      </button>

      {/* Lista de conversas */}
      <div className="flex-1 overflow-y-auto px-3 text-sm space-y-1">
        {conversations.map((c) => (
          <div
            key={c.id}
            className={`flex items-center justify-between rounded px-2 py-1 cursor-pointer ${
              c.id === activeId ? 'bg-zinc-200 font-semibold' : 'hover:bg-zinc-100'
            }`}
          >
            <span onClick={() => selectConversation(c.id)} className="flex-1 truncate">
              {c.title}
            </span>
            <button
              onClick={() => deleteConversation(c.id)}
              className="ml-2 p-1 text-zinc-500 hover:text-red-600"
              title="Apagar conversa"
            >
              <Trash2 size={14} />
            </button>
          </div>
        ))}
      </div>
    </aside>
  );
}
