export interface Message {
  role: 'user' | 'assistant';
  content: string;
}

export interface Session {
  id: string;
  title: string;
  messages: Message[];
}

export interface Prediction {
  token: string;
  exchange: string;
  certeza?: number;
}
