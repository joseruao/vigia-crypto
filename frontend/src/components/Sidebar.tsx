// frontend/src/components/Sidebar.tsx
'use client'

import { useState } from 'react'
import { useChatHistoryContext } from '@/lib/ChatHistoryProvider'
import { Trash2, Plus } from 'lucide-react'
import { usePathname } from 'next/navigation'

function formatDate(ts: number) {
  try {
    return new Date(ts).toLocaleString(undefined, {
      day: '2-digit',
      month: '2-digit',
      year: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    })
  } catch {
    return ''
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
    updateTitle,
  } = useChatHistoryContext()

  const [editingId, setEditingId] = useState<string | null>(null)
  const [tempTitle, setTempTitle] = useState('')
  const pathname = usePathname()

  // oculta sidebar em /login
  if (pathname === '/login') return null

  function startEdit(id: string, title: string) {
    setEditingId(id)
    setTempTitle(title)
  }

  function confirmEdit(id: string) {
    updateTitle(id, tempTitle.trim() || 'Sem título')
    setEditingId(null)
  }

  return (
    <aside className="hidden md:flex w-64 flex-col border-r border-zinc-200 bg-white text-black">
      {/* logo topo */}
      <div className="p-4 border-b border-zinc-200">
        <img src="/logo_small.png" alt="JR" className="h-6 w-auto" />
      </div>

      {/* botão novo chat */}
      <div className="px-3 mt-3 mb-2">
        <button
          onClick={newConversation}
          className="w-full flex items-center justify-center gap-2 rounded-lg border border-zinc-300 px-3 py-2 text-sm font-medium hover:border-zinc-900 hover:bg-zinc-950 hover:text-white transition"
        >
          <Plus size={16} />
          <span>Novo chat</span>
        </button>
      </div>

      <div className="px-4 pb-2 text-[11px] uppercase tracking-wider text-zinc-500">
        Chats
      </div>

      {/* lista de conversas */}
      <div className="flex-1 overflow-y-auto px-3 text-sm space-y-1">
        {conversations.map((c) => (
          <div
            key={c.id}
            className={`group flex items-center justify-between rounded-lg px-2 py-2 cursor-pointer ${
              c.id === activeId
                ? 'bg-zinc-100 font-semibold'
                : 'hover:bg-zinc-100'
            }`}
            onClick={() => selectConversation(c.id)}
          >
            <div className="min-w-0 flex-1">
              {editingId === c.id ? (
                <input
                  value={tempTitle}
                  onChange={(e) => setTempTitle(e.target.value)}
                  onBlur={() => confirmEdit(c.id)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') confirmEdit(c.id)
                    if (e.key === 'Escape') setEditingId(null)
                  }}
                  autoFocus
                  className="w-full text-sm border rounded px-1"
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
                e.stopPropagation()
                deleteConversation(c.id)
              }}
              className="ml-2 p-1 text-zinc-500 hover:text-red-600 opacity-0 group-hover:opacity-100 transition"
              title="Apagar conversa"
            >
              <Trash2 size={14} />
            </button>
          </div>
        ))}
      </div>

      <div className="p-3 mt-2 border-t border-zinc-200">
        <button
          onClick={clearAll}
          className="w-full rounded-lg px-3 py-2 text-xs text-zinc-500 hover:bg-red-50 hover:text-red-600"
        >
          Limpar tudo
        </button>
      </div>

      <div className="border-t border-zinc-200 p-4 text-center text-xs text-zinc-500 bg-zinc-50">
        Vigia Crypto · beta
      </div>
    </aside>
  )
}
