'use client';

import { useState, useEffect } from 'react';

export type Message = { role: 'user' | 'assistant'; content: string };
export type Conversation = { id: string; title: string; messages: Message[] };

const STORAGE_KEY = 'chat_history';

export function useChatHistory() {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeId, setActiveId] = useState<string | null>(null);

  // carregar histórico do localStorage
  useEffect(() => {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) {
      try {
        const parsed: Conversation[] = JSON.parse(raw);
        setConversations(parsed);
        if (parsed.length > 0) setActiveId(parsed[0].id);
      } catch {
        console.error('Erro ao carregar histórico');
      }
    }
  }, []);

  // guardar sempre que mudar
  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(conversations));
  }, [conversations]);

  function newConversation() {
    const id = Date.now().toString();
    const conv: Conversation = { id, title: 'Nova conversa', messages: [] };
    setConversations([conv, ...conversations]);
    setActiveId(id);
  }

  function addMessage(msg: Message) {
    if (!activeId) return;
    setConversations((prev) =>
      prev.map((c) =>
        c.id === activeId
          ? {
              ...c,
              messages: [...c.messages, msg],
              title:
                c.messages.length === 0 && msg.role === 'user'
                  ? msg.content.slice(0, 20)
                  : c.title,
            }
          : c
      )
    );
  }

  function selectConversation(id: string) {
    setActiveId(id);
  }

  function deleteConversation(id: string) {
    setConversations((prev) => prev.filter((c) => c.id !== id));
    if (activeId === id) {
      setActiveId(null);
    }
  }

  const active = conversations.find((c) => c.id === activeId) ?? null;

  return {
    conversations,
    active,
    activeId,
    newConversation,
    addMessage,
    selectConversation,
    deleteConversation,
  };
}
