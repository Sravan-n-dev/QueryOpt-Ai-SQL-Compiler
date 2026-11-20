const API_BASE = "";

export async function compileQuery(query, mode) {
  const res = await fetch(`${API_BASE}/api/compile`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query, mode }),
  });
  return res.json();
}

export async function fetchStats() {
  const res = await fetch(`${API_BASE}/api/stats`);
  return res.json();
}

export async function fetchSchema() {
  const res = await fetch(`${API_BASE}/api/schema`);
  return res.json();
}

export async function getGeminiConfig() {
  const res = await fetch(`${API_BASE}/api/config/gemini`);
  return res.json();
}

export async function setGeminiConfig(apiKey, model, test = true) {
  const res = await fetch(`${API_BASE}/api/config/gemini`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ api_key: apiKey, model, test }),
  });
  return res.json();
}
