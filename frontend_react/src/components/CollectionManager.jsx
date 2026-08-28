import { useEffect, useState } from "react";
import { deleteCollection as deleteCollectionRequest, listCollections } from "../api.js";

export default function CollectionManager({ apiKey, collection, setCollection, setStatus, reloadSignal }) {
  const [collections, setCollections] = useState([]);
  const [selected, setSelected] = useState("");

  async function refresh() {
    try {
      const data = await listCollections(apiKey);
      const names = data.collections || [];
      setCollections(names);
      const next = names.includes(selected) ? selected : names[0] || "";
      setSelected(next);
      if (next) setCollection(next);
      setStatus(`Loaded ${names.length} collection(s).`);
    } catch (error) {
      setStatus(`Could not load collections: ${error.message}`);
    }
  }

  useEffect(() => {
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [reloadSignal]);

  async function handleDelete() {
    const name = selected || collection.trim();
    if (!name) return setStatus("Pick a collection first.");
    if (!window.confirm(`Delete collection "${name}"? This cannot be undone.`)) return;
    try {
      setStatus(`Deleting ${name}...`);
      await deleteCollectionRequest(name, apiKey);
      setStatus(`Deleted ${name}.`);
      refresh();
    } catch (error) {
      setStatus(`Delete failed: ${error.message}`);
    }
  }

  return (
    <div className="section">
      <label>Collections</label>
      <select
        size={6}
        value={selected}
        onChange={(e) => {
          setSelected(e.target.value);
          setCollection(e.target.value);
        }}
      >
        {collections.length ? (
          collections.map((name) => (
            <option key={name} value={name}>
              {name}
            </option>
          ))
        ) : (
          <option value="">No collections yet</option>
        )}
      </select>
      <div className="button-row">
        <button onClick={refresh}>Refresh</button>
        <button className="danger" onClick={handleDelete}>Delete</button>
      </div>
      <div className="hint">Delete requires the API key and removes the selected collection permanently.</div>
    </div>
  );
}
