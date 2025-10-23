'use client';

import { useEffect, useState } from 'react';
import { useChatHistoryContext } from '@/lib/ChatHistoryProvider';
import { Trash2, Plus, Save, LogOut } from 'lucide-react';
import { supabase } from '@/lib/supabaseClient';
import { usePathname } from 'next/navigation';

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

export function Sidebar() {
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
  const [email, setEmail] = useState<string | null>(null);
  const pathname = usePathname();

  // Esconde sidebar na página de login
  if (pathname === '/login') {
    return null;
  }

  // carregar utilizador logado
  useEffect(() => {
    supabase.auth.getUser().then(({ data }) => {
      setEmail(data.user?.email ?? null);
    });
  }, []);

  async function logout() {
    await supabase.auth.signOut();
    window.location.href = '/login';
  }

  function startEdit(id: string, title: string) {
    setEditingId(id);
    setTempTitle(title);
  }

  function confirmEdit(id: string) {
    updateTitle(id, tempTitle.trim() || 'Sem título');
    setEditingId(null);
  }

  function exportConversations() {
    const blob = new Blob([JSON.stringify(conversations, null, 2)], {
      type: 'application/json',
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'conversas.json';
    a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <aside className="hidden md:flex w-64 flex-col border-r border-zinc-300 bg-white text-black">
      {/* ... (resto do código igual) ... */}
    </aside>
  );
}