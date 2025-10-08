import { Session } from './types';

const STORAGE_KEY = 'chat_history';

/** Lê todas as sessões guardadas em localStorage. */
export function loadSessions(): Session[] {
  try {
    const raw = typeof window !== 'undefined' ? localStorage.getItem(STORAGE_KEY) : null;
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? (parsed as Session[]) : [];
  } catch {
    return [];
  }
}

/** Grava todas as sessões no localStorage. */
export function saveSessions(sessions: Session[]) {
  try {
    if (typeof window === 'undefined') return;
    localStorage.setItem(STORAGE_KEY, JSON.stringify(sessions));
  } catch (e) {
    console.error('Falha ao gravar chat_history:', e);
  }
}

/** Apaga o histórico completo. */
export function clearSessions() {
  try {
    if (typeof window === 'undefined') return;
    localStorage.removeItem(STORAGE_KEY);
  } catch (e) {
    console.error('Falha ao limpar chat_history:', e);
  }
}
