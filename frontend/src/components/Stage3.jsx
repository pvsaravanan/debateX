import { useState, useEffect, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import './Stage3.css';

// Characters revealed per tick — fast enough to feel like streaming,
// slow enough to read along (~500 chars/sec).
const CHARS_PER_TICK = 6;
const TICK_MS = 12;

export default function Stage3({ finalResponse, animate = false, onStream }) {
  const text = finalResponse?.response || '';
  const [visibleChars, setVisibleChars] = useState(animate ? 0 : text.length);
  const onStreamRef = useRef(onStream);
  onStreamRef.current = onStream;

  useEffect(() => {
    if (!animate) {
      setVisibleChars(text.length);
      return;
    }
    const id = setInterval(() => {
      setVisibleChars((v) => {
        if (v >= text.length) {
          clearInterval(id);
          return v;
        }
        return Math.min(v + CHARS_PER_TICK, text.length);
      });
    }, TICK_MS);
    return () => clearInterval(id);
  }, [animate, text]);

  // Keep the viewport following the reveal (parent decides whether to scroll)
  useEffect(() => {
    if (visibleChars < text.length) onStreamRef.current?.();
  }, [visibleChars, text.length]);

  if (!finalResponse) {
    return null;
  }

  const isTyping = animate && visibleChars < text.length;
  const chairmanName = (finalResponse.model.split('/').pop() || finalResponse.model).replace(/:free$/, '');

  return (
    <div className="stage stage3">
      <div className="stage3-header">
        <h3 className="stage-title">Final Answer</h3>
        <span className="chairman-badge" title={finalResponse.model}>
          Chairman · {chairmanName}
        </span>
      </div>
      <div className="final-response">
        <div className={`final-text markdown-content ${isTyping ? 'is-typing' : ''}`}>
          <ReactMarkdown remarkPlugins={[remarkGfm]}>
            {isTyping ? text.slice(0, visibleChars) : text}
          </ReactMarkdown>
        </div>
      </div>
    </div>
  );
}
