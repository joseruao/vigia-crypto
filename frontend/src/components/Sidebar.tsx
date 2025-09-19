'use client';

import { useChatHistoryContext } from '@/lib/ChatHistoryProvider';
import { Trash2, Plus } from 'lucide-react';

function formatTime(ts: number) {
  try {
    return new Date(ts).toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' });
  } catch {
    return '';
  }
}

export function Sidebar() {
  const {
    conversations,
    activeId,
    newConversation,
    selectConversation,
    deleteConversation,
    clearAll,
  } = useChatHistoryContext();

  return (
    <aside className="hidden md:flex w-64 flex-col border-r border-zinc-300 bg-white text-black">
      {/* logo topo */}
      <div className="p-4">
        <img src="/logo_small.png" alt="JR" className="h-6 w-auto" />
      </div>

      {/* botão novo chat */}
      <div className="px-3 mb-2">
        <button
          onClick={newConversation}
          className="w-full flex items-center justify-center gap-2 rounded-lg border border-black px-3 py-2 text-sm hover:bg-black hover:text-white"
        >
          <Plus size={16} />
          <span>Novo chat</span>
        </button>
      </div>

      {/* label section */}
      <div className="px-4 pb-2 text-[11px] uppercase tracking-wider text-zinc-500">
        Chats
      </div>

      {/* lista */}
      <div className="flex-1 overflow-y-auto px-3 text-sm space-y-1">
        {conversations.map((c) => (
          <div
            key={c.id}
            className={`group flex items-center justify-between rounded px-2 py-1 cursor-pointer ${
              c.id === activeId ? 'bg-zinc-200 font-semibold' : 'hover:bg-zinc-100'
            }`}
            onClick={() => selectConversation(c.id)}
            title={c.messages[0]?.content ?? 'Conversa'}
          >
            <div className="min-w-0 flex-1">
              <div className="truncate">{c.title || 'Sem título'}</div>
              <div className="text-[11px] text-zinc-500">{formatTime(c.createdAt)}</div>
            </div>
            <button
              onClick={(e) => {
                e.stopPropagation();
                deleteConversation(c.id);
              }}
              className="ml-2 p-1 text-zinc-500 hover:text-red-600 opacity-0 group-hover:opacity-100 transition"
              title="Apagar conversa"
            >
              <Trash2 size={14} />
            </button>
          </div>
        ))}
      </div>

      {/* limpar tudo */}
      <div className="p-3 mt-2 border-t border-zinc-200">
        <button
          onClick={clearAll}
          className="w-full text-xs text-red-600 hover:underline"
          title="Remove todas as conversas do dispositivo"
        >
          Limpar tudo
        </button>
      </div>
    </aside>
  );
}
