// frontend/src/components/Sidebar.tsx
'use client';

import { useState } from 'react';
import { usePathname } from 'next/navigation';
import { Plus, Trash2, X } from 'lucide-react';
import { useChatHistoryContext } from '@/lib/ChatHistoryProvider';

type SidebarProps = {
  mobile?: boolean;
  onClose?: () => void;
};

function formatDate(ts: number) {
  try {
    return new Date(ts).toLocaleString(undefined, {
      day: '2-digit',
      month: '2-digit',
      year: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch {
    return '';
  }
}

export function Sidebar({ mobile = false, onClose }: SidebarProps) {
  const {
    conversations,
    activeId,
    newConversation,
    selectConversation,
    deleteConversation,
    clearAll,
    updateTitle,
  } = useChatHistoryContext();

  const [editingId, setEditingId] = useState<string | null>(null);
  const [tempTitle, setTempTitle] = useState('');
  const pathname = usePathname();

  if (pathname === '/login') return null;

  function handleNewConversation() {
    newConversation();
    onClose?.();
  }

  function handleSelectConversation(id: string) {
    selectConversation(id);
    onClose?.();
  }

  function startEdit(id: string, title: string) {
    setEditingId(id);
    setTempTitle(title);
  }

  function confirmEdit(id: string) {
    updateTitle(id, tempTitle.trim() || 'Sem título');
    setEditingId(null);
  }

  return (
    <aside className={`${mobile ? 'flex h-full w-80 max-w-[86vw]' : 'hidden w-64 md:flex'} flex-col border-r border-zinc-200 bg-white text-black`}>
      <div className="flex items-center justify-between border-b border-zinc-200 p-4">
        <button
          onClick={handleNewConversation}
          className="rounded-md focus:outline-none focus:ring-2 focus:ring-zinc-300"
          title="Voltar ao início"
          aria-label="Voltar ao início"
        >
          <img src="/logo_small.png" alt="JR" className="h-6 w-auto" />
        </button>
        {mobile ? (
          <button
            onClick={onClose}
            className="rounded-lg p-2 text-zinc-500 hover:bg-zinc-100 hover:text-zinc-900"
            title="Fechar menu"
            aria-label="Fechar menu"
          >
            <X size={18} />
          </button>
        ) : null}
      </div>

      <div className="mb-2 mt-3 px-3">
        <button
          onClick={handleNewConversation}
          className="flex w-full items-center justify-center gap-2 rounded-lg border border-zinc-300 px-3 py-2 text-sm font-medium transition hover:border-zinc-900 hover:bg-zinc-950 hover:text-white"
        >
          <Plus size={16} />
          <span>Novo chat</span>
        </button>
      </div>

      <div className="px-4 pb-2 text-[11px] uppercase tracking-wider text-zinc-500">
        Chats
      </div>

      <div className="flex-1 space-y-1 overflow-y-auto px-3 text-sm">
        {conversations.length === 0 ? (
          <div className="rounded-lg border border-dashed border-zinc-200 px-3 py-4 text-xs leading-relaxed text-zinc-500">
            Ainda sem conversas. Usa as sugestões no ecrã inicial ou escreve uma pergunta.
          </div>
        ) : null}

        {conversations.map((c) => (
          <div
            key={c.id}
            className={`group flex cursor-pointer items-center justify-between rounded-lg px-2 py-2 ${
              c.id === activeId ? 'bg-zinc-100 font-semibold' : 'hover:bg-zinc-100'
            }`}
            onClick={() => handleSelectConversation(c.id)}
          >
            <div className="min-w-0 flex-1">
              {editingId === c.id ? (
                <input
                  value={tempTitle}
                  onChange={(e) => setTempTitle(e.target.value)}
                  onBlur={() => confirmEdit(c.id)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') confirmEdit(c.id);
                    if (e.key === 'Escape') setEditingId(null);
                  }}
                  autoFocus
                  className="w-full rounded border px-1 text-sm"
                />
              ) : (
                <>
                  <div
                    className="truncate cursor-text"
                    onDoubleClick={() => startEdit(c.id, c.title)}
                  >
                    {c.title || 'Sem título'}
                  </div>
                  <div className="text-[11px] text-zinc-500">
                    {formatDate(c.createdAt)}
                  </div>
                </>
              )}
            </div>
            <button
              onClick={(e) => {
                e.stopPropagation();
                deleteConversation(c.id);
              }}
              className="ml-2 p-1 text-zinc-500 opacity-0 transition hover:text-red-600 group-hover:opacity-100"
              title="Apagar conversa"
            >
              <Trash2 size={14} />
            </button>
          </div>
        ))}
      </div>

      <div className="mt-2 border-t border-zinc-200 p-3">
        <button
          onClick={clearAll}
          className="w-full rounded-lg px-3 py-2 text-xs text-zinc-500 hover:bg-red-50 hover:text-red-600"
        >
          Limpar tudo
        </button>
      </div>

      <div className="border-t border-zinc-200 bg-zinc-50 p-4 text-center text-xs text-zinc-500">
        joseruao.com · crypto intel
      </div>
    </aside>
  );
}
