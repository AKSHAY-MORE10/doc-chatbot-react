import { useEffect, useState } from "react";
import { getLlmSettings, saveLlmSettings } from "../api.js";

const DEFAULTS = {
  ollama: { model: "qwen2.5:7b", embed_model: "nomic-embed-text", api_base_url: "https://api.x.ai/v1" },
  groq: { model: "groq-2-latest", embed_model: "nomic-embed-text", api_base_url: "https://api.x.ai/v1" },
  gemini: {
    model: "gemini-2.0-flash",
    embed_model: "text-embedding-004",
    api_base_url: "https://generativelanguage.googleapis.com/v1beta",
  },
};

export default function ModelSettings({ apiKey, setStatus }) {
  const [provider, setProvider] = useState("ollama");
  const [model, setModel] = useState("");
  const [embedModel, setEmbedModel] = useState("");
  const [ollamaBaseUrl, setOllamaBaseUrl] = useState("");
  const [llmApiKey, setLlmApiKey] = useState("");
  const [apiBaseUrl, setApiBaseUrl] = useState("");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    (async () => {
      try {
        const data = await getLlmSettings(apiKey);
        setProvider(data.provider || "ollama");
        setModel(data.model || "");
        setEmbedModel(data.embed_model || "");
        setOllamaBaseUrl(data.ollama_base_url || "");
        setApiBaseUrl(data.api_base_url || "");
        setStatus(
          data.api_key_saved
            ? "Loaded model settings from .env."
            : "Loaded model settings. No API key saved yet."
        );
      } catch (error) {
        setStatus(`Model settings not loaded: ${error.message}`);
      }
    })();
    // Load once on mount, same as the vanilla app's loadModelSettings() call.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function handleSave() {
    const defaults = DEFAULTS[provider];
    const payload = {
      provider,
      model: model.trim() || defaults.model,
      embed_model: embedModel.trim() || defaults.embed_model,
      api_key: llmApiKey.trim(),
      ollama_base_url: ollamaBaseUrl.trim() || "http://localhost:11434",
      api_base_url: apiBaseUrl.trim() || defaults.api_base_url,
      gemini_base_url: "https://generativelanguage.googleapis.com/v1beta",
    };

    setSaving(true);
    setStatus("Saving model settings to .env...");
    try {
      const data = await saveLlmSettings(payload, apiKey);
      setProvider(data.provider || "ollama");
      setModel(data.model || "");
      setEmbedModel(data.embed_model || "");
      setOllamaBaseUrl(data.ollama_base_url || "");
      setApiBaseUrl(data.api_base_url || "");
      setLlmApiKey("");
      setStatus(`Saved ${data.provider} settings to .env.`);
    } catch (error) {
      setStatus(`Could not save model settings: ${error.message}`);
    } finally {
      setSaving(false);
    }
  }

  const isApiProvider = provider !== "ollama";

  return (
    <div className="section">
      <label>Model settings</label>
      <div className="split-row">
        <select value={provider} onChange={(e) => setProvider(e.target.value)}>
          <option value="ollama">Self-hosted / Ollama</option>
          <option value="groq">Groq</option>
          <option value="gemini">Gemini</option>
        </select>
        <input
          type="text"
          placeholder="Model name"
          value={model}
          onChange={(e) => setModel(e.target.value)}
        />
      </div>

      <label htmlFor="embed-model">Embedding model</label>
      <input
        id="embed-model"
        type="text"
        placeholder="Embedding model"
        value={embedModel}
        onChange={(e) => setEmbedModel(e.target.value)}
      />

      <div className={`field-group ${isApiProvider ? "hidden" : ""}`}>
        <label htmlFor="ollama-base-url">Ollama base URL</label>
        <input
          id="ollama-base-url"
          type="text"
          placeholder="http://localhost:11434"
          value={ollamaBaseUrl}
          onChange={(e) => setOllamaBaseUrl(e.target.value)}
        />
      </div>

      <div className={`field-group ${isApiProvider ? "" : "hidden"}`}>
        <label htmlFor="llm-api-key">API key</label>
        <input
          id="llm-api-key"
          type="password"
          placeholder="Paste API key"
          value={llmApiKey}
          onChange={(e) => setLlmApiKey(e.target.value)}
        />
        <label htmlFor="api-base-url">API base URL</label>
        <input
          id="api-base-url"
          type="text"
          placeholder="https://api.x.ai/v1"
          value={apiBaseUrl}
          onChange={(e) => setApiBaseUrl(e.target.value)}
        />
      </div>

      <div className="button-row">
        <button className="primary" onClick={handleSave} disabled={saving}>
          Save model settings
        </button>
      </div>
      <div className="hint">Saving writes the selected provider, model, and API key into the server .env file.</div>
    </div>
  );
}
