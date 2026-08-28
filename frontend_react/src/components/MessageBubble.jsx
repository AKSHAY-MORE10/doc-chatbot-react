import { useMemo } from "react";
import { marked } from "marked";
import DOMPurify from "dompurify";
import SourceCitations from "./SourceCitations.jsx";

marked.setOptions({ breaks: true, gfm: true });

export default function MessageBubble({ role, content, loading, error, sources, webSources }) {
  const html = useMemo(() => {
    if (role !== "bot" || loading || error) return null;
    return DOMPurify.sanitize(marked.parse(content || ""), { USE_PROFILES: { html: true } });
  }, [role, content, loading, error]);

  return (
    <div className={`msg ${role}`}>
      {loading ? (
        <span className="spinner" aria-label="Thinking" />
      ) : error ? (
        <span>
          <strong>Error: </strong>
          {content}
        </span>
      ) : role === "bot" ? (
        <div dangerouslySetInnerHTML={{ __html: html }} />
      ) : (
        content
      )}
      {!loading && !error && <SourceCitations sources={sources} webSources={webSources} />}
    </div>
  );
}
