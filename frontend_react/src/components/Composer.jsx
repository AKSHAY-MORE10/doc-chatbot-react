import { useState } from "react";

export default function Composer({ onSend, disabled }) {
  const [value, setValue] = useState("");

  function submit() {
    const q = value.trim();
    if (!q) return;
    setValue("");
    onSend(q);
  }

  return (
    <div className="composer">
      <div className="composer-row">
        <input
          type="text"
          placeholder="Ask a question..."
          autoComplete="off"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") submit();
          }}
        />
        <button className="primary" onClick={submit} disabled={disabled}>
          Send
        </button>
      </div>
    </div>
  );
}
