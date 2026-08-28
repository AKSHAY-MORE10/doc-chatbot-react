import { useRef, useState } from "react";
import { uploadFile as uploadFileRequest } from "../api.js";

export default function UploadZone({ apiKey, collection, setStatus, onUploaded }) {
  const inputRef = useRef(null);
  const [busy, setBusy] = useState(false);
  const [dragging, setDragging] = useState(false);

  async function handleFile(file) {
    if (!file) return;
    const col = collection.trim() || "default";
    setStatus(`Ingesting ${file.name} into ${col}...`);
    setBusy(true);
    try {
      const data = await uploadFileRequest(file, col, apiKey);
      setStatus(`Uploaded ${data.filename} and added ${data.chunks_added} chunks to ${data.collection}.`);
      onUploaded();
    } catch (error) {
      setStatus(`Error: ${error.message}`);
    } finally {
      setBusy(false);
      if (inputRef.current) inputRef.current.value = "";
    }
  }

  return (
    <div className="section">
      <label>Upload documents</label>
      <div
        className={`upload-area ${dragging ? "dragging" : ""}`}
        onClick={() => inputRef.current?.click()}
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragging(false);
          if (e.dataTransfer.files.length > 0) handleFile(e.dataTransfer.files[0]);
        }}
      >
        Drop a PDF or TXT here, or click to browse
      </div>
      <input
        ref={inputRef}
        type="file"
        accept=".pdf,.txt"
        style={{ display: "none" }}
        onChange={(e) => handleFile(e.target.files[0])}
      />
      <div className="button-row">
        <button className="primary" disabled={busy} onClick={() => inputRef.current?.click()}>
          {busy ? "Ingesting…" : "Upload & ingest"}
        </button>
      </div>
    </div>
  );
}
