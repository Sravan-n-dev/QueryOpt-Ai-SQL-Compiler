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

export async function getAzureOpenAIConfig() {
  const res = await fetch(`${API_BASE}/api/config/azure-openai`);
  return res.json();
}

export async function setAzureOpenAIConfig(endpoint, apiKey, deployment, test = true) {
  const res = await fetch(`${API_BASE}/api/config/azure-openai`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ endpoint, api_key: apiKey, deployment, test }),
  });
  return res.json();
}

export async function clearAzureOpenAIConfig() {
  const res = await fetch(`${API_BASE}/api/config/azure-openai`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ clear: true }),
  });
  return res.json();
}
