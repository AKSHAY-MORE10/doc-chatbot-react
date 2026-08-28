import { useState } from "react";
import Sidebar from "./components/Sidebar.jsx";
import ChatPanel from "./components/ChatPanel.jsx";
import { useLocalStorageState, useSessionStorageState } from "./hooks/useStorageState.js";

export default function App() {
  const [apiKey, setApiKey] = useSessionStorageState("doc-chatbot-admin-key", "");
  const [chatHistory, setChatHistory] = useLocalStorageState("doc-chatbot-chat-history", []);
  const [collection, setCollection] = useState("default");
  const [status, setStatus] = useState("");

  function addToHistory(role, content) {
    setChatHistory((prev) => [...prev, { role, content }].slice(-20));
  }

  return (
    <div className="app">
      <Sidebar
        apiKey={apiKey}
        setApiKey={setApiKey}
        collection={collection}
        setCollection={setCollection}
        status={status}
        setStatus={setStatus}
      />
      <ChatPanel
        apiKey={apiKey}
        collection={collection}
        chatHistory={chatHistory}
        addToHistory={addToHistory}
      />
    </div>
  );
}
