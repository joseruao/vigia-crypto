'use client';

import { createContext, useContext } from 'react';
import { useChatHistory } from './useChatHistory';

const ChatHistoryContext = createContext<ReturnType<typeof useChatHistory> | null>(null);

export function ChatHistoryProvider({ children }: { children: React.ReactNode }) {
  const value = useChatHistory();
  return <ChatHistoryContext.Provider value={value}>{children}</ChatHistoryContext.Provider>;
}

export function useChatHistoryContext() {
  const ctx = useContext(ChatHistoryContext);
  if (!ctx) throw new Error('useChatHistoryContext must be used within ChatHistoryProvider');
  return ctx;
}
