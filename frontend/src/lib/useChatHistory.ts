'use client';

import { useState, useEffect } from 'react';
import { v4 as uuidv4 } from 'uuid';

export type Message = { role: 'user' | 'assistant'; content: string };
export type Conversation = { id: string; title: string; createdAt: number; messages: Message[] };

const STORAGE_KEY = 'chat_history';

export function useChatHistory() {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeId, setActiveId] = useState<string | null>(null);

  // carregar do localStorage (com migração p/ createdAt se faltar)
  useEffect(() => {
    const raw = typeof window !== 'undefined' ? localStorage.getItem(STORAGE_KEY) : null;
    if (!raw) return;

    try {
      const parsed = JSON.parse(raw) as any[];
      const migrated: Conversation[] = parsed.map((c) => ({
        id: c.id ?? uuidv4(),
        title: c.title ?? 'Nova conversa',
        createdAt: typeof c.createdAt === 'number' ? c.createdAt : Date.now(),
        messages: Array.isArray(c.messages) ? c.messages : [],
      }));
      setConversations(migrated);
      if (migrated.length > 0) setActiveId(migrated[0].id);
    } catch {
      console.error('Erro ao carregar histórico');
    }
  }, []);

  // guardar sempre que mudar
  useEffect(() => {
    if (typeof window === 'undefined') return;
    localStorage.setItem(STORAGE_KEY, JSON.stringify(conversations));
  }, [conversations]);

  function newConversation(): string {
    const id = uuidv4();
    const conv: Conversation = { id, title: 'Nova conversa', createdAt: Date.now(), messages: [] };
    setConversations((prev) => [conv, ...prev]);
    setActiveId(id);
    return id;
  }

  function addMessage(msg: Message) {
    let id = activeId;
    if (!id) id = newConversation();

    setConversations((prev) =>
      prev.map((c) =>
        c.id === id
          ? {
              ...c,
              messages: [...c.messages, msg],
              // 1ª mensagem do user define o título
              title: msg.role === 'user' && c.messages.length === 0
                ? msg.content.slice(0, 40)
                : c.title,
            }
          : c
      )
    );

    setActiveId(id);
  }

  function updateLastAssistantMessage(content: string) {
    if (!activeId) return;
    setConversations((prev) =>
      prev.map((c) =>
        c.id === activeId
          ? {
              ...c,
              messages: c.messages.map((m, i) =>
                i === c.messages.length - 1 && m.role === 'assistant'
                  ? { ...m, content }
                  : m
              ),
            }
          : c
      )
    );
  }

  function selectConversation(id: string) {
    setActiveId(id);
  }

  function deleteConversation(id: string) {
    setConversations((prev) => {
      const next = prev.filter((c) => c.id !== id);
      // se apagaste a ativa, seleciona a próxima (se existir)
      if (activeId === id) setActiveId(next[0]?.id ?? null);
      return next;
    });
  }

  function clearAll() {
    setConversations([]);
    setActiveId(null);
    if (typeof window !== 'undefined') {
      localStorage.removeItem(STORAGE_KEY);
    }
  }

  const active = conversations.find((c) => c.id === activeId) ?? null;

  return {
    conversations,
    active,
    activeId,
    newConversation,
    addMessage,
    updateLastAssistantMessage,
    selectConversation,
    deleteConversation,
    clearAll,
  };
}
