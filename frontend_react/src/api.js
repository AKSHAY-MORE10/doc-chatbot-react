const API = window.location.origin;

export function authHeaders(apiKey) {
  return apiKey ? { "X-API-Key": apiKey } : {};
}

export async function apiFetch(path, apiKey, options = {}) {
  const response = await fetch(`${API}${path}`, {
    ...options,
    headers: {
      ...(options.headers || {}),
      ...authHeaders(apiKey),
    },
  });

  let data = {};
  try {
    data = await response.json();
  } catch {
    data = {};
  }

  if (!response.ok) {
    throw new Error(data.detail || data.message || `Request failed with ${response.status}`);
  }
  return data;
}

export async function uploadFile(file, collection, apiKey) {
  const fd = new FormData();
  fd.append("file", file);
  fd.append("collection", collection);
  return apiFetch("/ingest", apiKey, { method: "POST", body: fd });
}

export async function sendChat(question, collection, history, apiKey) {
  return apiFetch("/chat", apiKey, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, collection, history }),
  });
}

export async function listCollections(apiKey) {
  return apiFetch("/collections", apiKey);
}

export async function deleteCollection(name, apiKey) {
  return apiFetch(`/collection/${encodeURIComponent(name)}`, apiKey, { method: "DELETE" });
}

export async function getLlmSettings(apiKey) {
  return apiFetch("/settings/llm", apiKey);
}

export async function saveLlmSettings(payload, apiKey) {
  return apiFetch("/settings/llm", apiKey, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}
