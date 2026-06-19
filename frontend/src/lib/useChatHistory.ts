'use client';

import { useState, useEffect } from 'react';
import { v4 as uuidv4 } from 'uuid';

export type Message = { role: 'user' | 'assistant'; content: string };
export type Conversation = { 
  id: string; 
  title: string; 
  createdAt: number; 
  messages: Message[]; 
};

const STORAGE_KEY = 'chat_history';

type StoredConversation = Partial<Omit<Conversation, 'messages'>> & {
  messages?: Message[];
};

export function useChatHistory() {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeId, setActiveId] = useState<string | null>(null);

  // carregar do localStorage
  useEffect(() => {
    const raw = typeof window !== 'undefined' ? localStorage.getItem(STORAGE_KEY) : null;
    if (!raw) return;
    try {
      const parsed = JSON.parse(raw) as StoredConversation[];
      const migrated: Conversation[] = parsed.map((c) => ({
        id: c.id ?? uuidv4(),
        title: c.title ?? 'New conversation',
        createdAt: typeof c.createdAt === 'number' ? c.createdAt : Date.now(),
        messages: Array.isArray(c.messages) ? c.messages : [],
      }));
      setConversations(migrated);
      if (migrated.length > 0) setActiveId(migrated[0].id);
    } catch {
      console.error('Failed to load chat history');
    }
  }, []);

  // guardar no localStorage
  useEffect(() => {
    if (typeof window === 'undefined') return;
    localStorage.setItem(STORAGE_KEY, JSON.stringify(conversations));
  }, [conversations]);

  function newConversation(): string {
    const id = uuidv4();
    const conv: Conversation = { id, title: 'New conversation', createdAt: Date.now(), messages: [] };
    setConversations((prev) => [conv, ...prev]);
    setActiveId(id);
    return id;
  }

  function addMessage(msg: Message, targetId?: string) {
    const id = targetId ?? activeId ?? uuidv4();

    setConversations((prev) => {
      const exists = prev.some((c) => c.id === id);
      if (!exists) {
        const title = msg.role === 'user' ? msg.content.slice(0, 40) : 'New conversation';
        return [{ id, title, createdAt: Date.now(), messages: [msg] }, ...prev];
      }
      return prev.map((c) =>
        c.id === id
          ? {
              ...c,
              messages: [...c.messages, msg],
              title:
                msg.role === 'user' && c.messages.length === 0
                  ? msg.content.slice(0, 40)
                  : c.title,
            }
          : c
      );
    });
    setActiveId(id);
  }

  function updateLastAssistantMessage(content: string, targetId?: string) {
    const id = targetId ?? activeId;
    if (!id) return;
    setConversations((prev) =>
      prev.map((c) =>
        c.id === id
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
      if (activeId === id) setActiveId(next[0]?.id ?? null);
      return next;
    });
  }

  function clearAll() {
    setConversations([]);
    setActiveId(null);
    if (typeof window !== 'undefined') localStorage.removeItem(STORAGE_KEY);
  }

  function updateTitle(id: string, newTitle: string) {
    setConversations((prev) =>
      prev.map((c) => (c.id === id ? { ...c, title: newTitle } : c))
    );
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
    updateTitle,
  };
}
