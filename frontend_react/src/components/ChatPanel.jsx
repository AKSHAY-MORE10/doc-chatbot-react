import { useEffect, useRef, useState } from "react";
import MessageBubble from "./MessageBubble.jsx";
import Composer from "./Composer.jsx";
import { sendChat } from "../api.js";
import "../styles/chat.css";

const WELCOME = { role: "bot", content: "Upload a document, then ask a question about it." };

export default function ChatPanel({ apiKey, collection, chatHistory, addToHistory }) {
  const [messages, setMessages] = useState([WELCOME]);
  const [meta, setMeta] = useState("Ready");
  const [sending, setSending] = useState(false);
  const listRef = useRef(null);

  useEffect(() => {
    listRef.current?.lastElementChild?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function handleSend(question) {
    const col = collection.trim() || "default";
    setMessages((prev) => [...prev, { role: "user", content: question }]);
    addToHistory("user", question);
    setMessages((prev) => [...prev, { role: "bot", content: "", loading: true }]);
    setSending(true);
    setMeta("Thinking...");

    try {
      const data = await sendChat(question, col, chatHistory, apiKey);
      setMessages((prev) => [
        ...prev.slice(0, -1),
        {
          role: "bot",
          content: data.answer,
          sources: data.sources || [],
          webSources: data.web_sources || [],
        },
      ]);
      addToHistory("assistant", data.answer || "");
      setMeta(`Answered from ${col}`);
    } catch (error) {
      setMessages((prev) => [...prev.slice(0, -1), { role: "bot", content: error.message, error: true }]);
      setMeta("Request failed");
    } finally {
      setSending(false);
    }
  }

  return (
    <main className="chat">
      <header className="chat-header">
        <div>
          <h2>Ask your documents</h2>
          <p>Answers are rendered safely and API calls are routed through the backend.</p>
        </div>
        <div className="chat-meta">{meta}</div>
      </header>

      <div className="messages" ref={listRef}>
        {messages.map((m, i) => (
          <MessageBubble key={i} {...m} />
        ))}
      </div>

      <Composer onSend={handleSend} disabled={sending} />
    </main>
  );
}
