const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';

export async function postChat(prompt: string) {
  const res = await fetch(`${API_URL}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ prompt }),
  });
  if (!res.ok) throw new Error('Erro no chat API');
  return res.json();
}

export async function getPredictions() {
  const res = await fetch(`${API_URL}/alerts/predictions`);
  if (!res.ok) throw new Error('Erro ao buscar predictions');
  return res.json();
}
