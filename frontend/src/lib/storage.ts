import type { Message, Session } from './types';

const STORAGE_KEY = 'chat_sessions';

export function loadSessions(): Session[] {
  if (typeof window === 'undefined') return [];
  const raw = localStorage.getItem(STORAGE_KEY);
  return raw ? JSON.parse(raw) : [];
}

export function saveSessions(sessions: Session[]) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(sessions));
}

export function listSessions(): Session[] {
  return loadSessions();
}

export function createSessionTitle(messages: Message[]): string {
  if (!messages.length) return 'Nova conversa';
  const firstMsg = messages.find((m) => m.role === 'user');
  return firstMsg ? firstMsg.content.slice(0, 30) : 'Conversa';
}

export function saveMessage(message: Message) {
  const id = getCurrentSessionId();
  if (!id) return;
  const sessions = loadSessions();
  const session = sessions.find((s) => s.id === id);
  if (!session) return;
  session.messages.push(message);
  saveSessions(sessions);
}

export function loadSession(id: string): Session | undefined {
  return loadSessions().find((s) => s.id === id);
}

export function startSession(): string {
  const sessions = loadSessions();
  const id = Date.now().toString();
  sessions.push({ id, title: 'Nova conversa', messages: [] });
  saveSessions(sessions);
  setCurrentSessionId(id);
  return id;
}

export function getCurrentSessionId(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem('current_session');
}

export function setCurrentSessionId(id: string) {
  if (typeof window === 'undefined') return;
  localStorage.setItem('current_session', id);
}
