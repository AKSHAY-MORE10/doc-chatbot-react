import { useState } from "react";

// Backend sends sources as plain labels like "manual.pdf (p. 4, Chapter 2 > Setup)".
// Parse that back into parts for a nicer card; fall back to the raw string if the
// shape doesn't match (e.g. sources indexed before page/section metadata existed).
function parseSource(label) {
  const match = label.match(/^(.*?)\s\((.*)\)$/);
  if (!match) return { name: label, detail: null };
  return { name: match[1], detail: match[2] };
}

export default function SourceCitations({ sources = [], webSources = [] }) {
  const [openIndex, setOpenIndex] = useState(null);

  if (!sources.length && !webSources.length) return null;

  return (
    <div className="citations">
      {sources.length > 0 && (
        <div className="citations-row">
          <span className="citations-label">Sources</span>
          <div className="citation-marks">
            {sources.map((label, i) => {
              const { name, detail } = parseSource(label);
              const isOpen = openIndex === i;
              return (
                <span key={i} className="citation-wrap">
                  <button
                    type="button"
                    className="citation-mark"
                    onClick={() => setOpenIndex(isOpen ? null : i)}
                    aria-expanded={isOpen}
                  >
                    {i + 1}
                  </button>
                  {isOpen && (
                    <div className="citation-card" role="tooltip">
                      <div className="citation-card-name">{name}</div>
                      {detail && <div className="citation-card-detail">{detail}</div>}
                    </div>
                  )}
                </span>
              );
            })}
          </div>
        </div>
      )}

      {webSources.length > 0 && (
        <div className="citations-row">
          <span className="citations-label">Web</span>
          <div className="citation-marks">
            {webSources.map((url) => (
              <a key={url} className="chip" href={url} target="_blank" rel="noreferrer noopener">
                {url}
              </a>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
