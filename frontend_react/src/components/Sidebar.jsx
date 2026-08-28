import { useState } from "react";
import ModelSettings from "./ModelSettings.jsx";
import UploadZone from "./UploadZone.jsx";
import CollectionManager from "./CollectionManager.jsx";
import "../styles/controls.css";
import "../styles/sidebar.css";

export default function Sidebar({ apiKey, setApiKey, collection, setCollection, status, setStatus }) {
  const [reloadSignal, setReloadSignal] = useState(0);

  return (
    <aside className="sidebar">
      <div className="brand">
        <h1>Doc Chatbot</h1>
        <p>Upload documents, query them with RAG, and switch between Ollama, Groq, or Gemini.</p>
      </div>

      <ModelSettings apiKey={apiKey} setStatus={setStatus} />

      <div className="section">
        <label htmlFor="collection">Collection / namespace</label>
        <input
          id="collection"
          type="text"
          value={collection}
          placeholder="e.g. product-handbook"
          onChange={(e) => setCollection(e.target.value)}
        />
      </div>

      <div className="section">
        <label htmlFor="api-key">Admin API key</label>
        <input
          id="api-key"
          type="password"
          placeholder="Required for ingest/delete"
          value={apiKey}
          onChange={(e) => setApiKey(e.target.value)}
        />
        <div className="hint">Stored locally in this browser session only.</div>
      </div>

      <UploadZone
        apiKey={apiKey}
        collection={collection}
        setStatus={setStatus}
        onUploaded={() => setReloadSignal((n) => n + 1)}
      />

      <CollectionManager
        apiKey={apiKey}
        collection={collection}
        setCollection={setCollection}
        setStatus={setStatus}
        reloadSignal={reloadSignal}
      />

      <div className="status">{status}</div>
    </aside>
  );
}
