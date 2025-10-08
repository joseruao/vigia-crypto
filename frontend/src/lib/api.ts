const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

export async function getPredictions() {
  try {
    const res = await fetch(`${API_BASE}/alerts/predictions`);
    if (!res.ok) throw new Error(`Erro HTTP: ${res.status}`);
    return res.json();
  } catch (err) {
    console.error("Erro a buscar predictions:", err);
    return [];
  }
}
