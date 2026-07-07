import { useState, useEffect, useRef, useCallback } from 'react';
import Stage3 from './Stage3';
import DeliberationTrace from './DeliberationTrace';
import DisagreementPanel from './DisagreementPanel';
import './ChatInterface.css';

const SendIcon = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="m5 12 7-7 7 7" />
    <path d="M12 19V5" />
  </svg>
);

const SUGGESTIONS = [
  { icon: '⚖️', text: 'Is it ever ethical to lie to protect someone?' },
  { icon: '🧠', text: 'Will AGI arrive before 2030? Argue both sides.' },
  { icon: '🔬', text: 'Is nuclear the best path to clean energy?' },
  { icon: '💻', text: 'Monolith or microservices for a new startup?' },
];

export default function ChatInterface({
  conversation,
  onSendMessage,
  isLoading,
}) {
  const [input, setInput] = useState('');
  const messagesEndRef = useRef(null);
  const scrollAreaRef = useRef(null);
  const textareaRef = useRef(null);

  const isNearBottom = () => {
    const el = scrollAreaRef.current;
    if (!el) return true;
    return el.scrollHeight - el.scrollTop - el.clientHeight < 120;
  };

  const scrollToBottom = useCallback((behavior = 'smooth') => {
    messagesEndRef.current?.scrollIntoView({ behavior });
  }, []);

  // Follow the stream only while the reader is already at the bottom,
  // so scrolling up to inspect earlier rounds isn't fought by autoscroll.
  const followStream = useCallback(() => {
    if (isNearBottom()) scrollToBottom('auto');
  }, [scrollToBottom]);

  useEffect(() => {
    scrollToBottom();
  }, [conversation, scrollToBottom]);

  // Reset input when switching conversations
  useEffect(() => {
    setInput('');
  }, [conversation?.id]);

  // Auto-grow the textarea with its content, capped at ~6 lines
  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = 'auto';
    el.style.height = `${Math.min(el.scrollHeight, 200)}px`;
  }, [input]);

  const submitMessage = (text) => {
    if (text.trim() && !isLoading) {
      onSendMessage(text);
      setInput('');
    }
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    submitMessage(input);
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  const isInitialState = !conversation || conversation.messages.length === 0;

  return (
    <div className="chat-interface">
      <div className={`main-content ${isInitialState ? 'centered' : ''}`} ref={scrollAreaRef}>
        {isInitialState ? (
          <div className="hero-section">
            <h2 className="logo-text">debateX</h2>
            <h1 className="hero-headline">
              Experience the <span className="highlight">frontier</span>
            </h1>
            <p className="hero-subtitle">
              One question. A council of AIs debates it across 5 rounds — then a Chairman delivers the verdict.
            </p>
            <div className="suggestion-chips">
              {SUGGESTIONS.map((s) => (
                <button
                  key={s.text}
                  className="suggestion-chip"
                  onClick={() => submitMessage(s.text)}
                  disabled={isLoading}
                >
                  <span className="chip-icon">{s.icon}</span>
                  {s.text}
                </button>
              ))}
            </div>
          </div>
        ) : (
          <div className="messages-container">
            {conversation.messages.map((msg, index) => {
              const routing = msg.routing || msg.metadata?.routing;
              const round3 = msg.round3 || (msg.rounds?.find(r => r.type === 'revise_or_defend')?.data);
              const round4 = msg.round4 || (msg.rounds?.find(r => r.type === 'challenger')?.data);
              const disagreementMap = msg.disagreement_map || msg.metadata?.disagreement_map;
              const metacognition = msg.metacognition || msg.metadata?.metacognition;
              // Messages created during this session carry a `loading` object;
              // messages rehydrated from storage don't — only live ones animate.
              const isLive = !!msg.loading;
              return (
                <div key={index} className={`message-group ${msg.role}`}>
                  <div className="message-content">
                    {msg.role === 'user' ? (
                      <div className="user-bubble">{msg.content}</div>
                    ) : (
                      <div className="assistant-stages">
                        <DeliberationTrace
                          msg={msg}
                          routing={routing}
                          round3={round3}
                          round4={round4}
                          metacognition={metacognition}
                        />

                        {msg.stage3 && (
                          <Stage3
                            finalResponse={msg.stage3}
                            animate={isLive}
                            onStream={followStream}
                          />
                        )}

                        {disagreementMap && (
                          <DisagreementPanel disagreementMap={disagreementMap} />
                        )}

                        {msg.error && (
                          <div className="error-panel">
                            {(() => {
                              const isGroqError = msg.error.toLowerCase().includes('groq') || msg.error.includes('gsk_');
                              if (isGroqError) {
                                return (
                                  <>
                                    <div className="error-header">
                                      <span className="error-badge groq-error">GROQ API ERROR</span>
                                      <span className="error-code">Groq Exception</span>
                                    </div>
                                    <p className="error-text">{msg.error}</p>
                                    <div className="error-action-box">
                                      <span className="action-title">How to Resolve:</span>
                                      <ol className="action-list">
                                        <li>Make sure you have added your Groq API Key to <code>.env</code> as <code>GROQ_API_KEY=your_key_here</code>.</li>
                                        <li>Verify if you have hit the **Requests Per Minute (RPM)** or **Tokens Per Minute (TPM)** limits on Groq's developer platform.</li>
                                        <li>Check the status of Groq service on the Groq Developer Console.</li>
                                      </ol>
                                    </div>
                                  </>
                                );
                              } else {
                                return (
                                  <>
                                    <div className="error-header">
                                      <span className="error-badge">LIMIT EXCEEDED</span>
                                      <span className="error-code">OpenRouter 429</span>
                                    </div>
                                    <p className="error-text">{msg.error}</p>
                                    {msg.error.includes("free-models-per-day") && (
                                      <div className="error-action-box">
                                        <span className="action-title">How to Resolve:</span>
                                        <ol className="action-list">
                                          <li>Add <strong>$10 in credits</strong> to your OpenRouter account to unlock 1,000 requests/day.</li>
                                          <li>Configure a paid API key with credits in your <code>.env</code> file.</li>
                                          <li>Wait for the daily limit to reset at midnight UTC.</li>
                                        </ol>
                                      </div>
                                    )}
                                  </>
                                );
                              }
                            })()}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
            <div ref={messagesEndRef} />
          </div>
        )}
      </div>

      <div className="input-container">
        <form className="input-box" onSubmit={handleSubmit}>
          <textarea
            ref={textareaRef}
            className="message-input"
            placeholder={isLoading ? 'The council is deliberating…' : 'Ask anything worth debating…'}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            rows={1}
          />
          <div className="input-footer">
            <button
              type="submit"
              className={`send-btn ${input.trim() && !isLoading ? 'active' : ''}`}
              disabled={!input.trim() || isLoading}
            >
              <SendIcon />
            </button>
          </div>
        </form>
        <p className="disclaimer">
          AI can make mistakes. Please check important information.
        </p>
      </div>
    </div>
  );
}
