import { useState, useEffect, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import Stage1 from './Stage1';
import Stage2 from './Stage2';
import Round3 from './Round3';
import Round4 from './Round4';
import Stage3 from './Stage3';
import './ChatInterface.css';

const BattleIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M14.5 17.5 3 6V3h3l11.5 11.5" />
    <path d="m13 19 6 3 3-6-3-6-6 3" />
    <path d="M8 16 3 21" />
    <path d="m18 8 3-3" />
  </svg>
);



const SendIcon = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="m5 12 7-7 7 7" />
    <path d="M12 19V5" />
  </svg>
);

export default function ChatInterface({
  conversation,
  onSendMessage,
  isLoading,
}) {
  const [input, setInput] = useState('');
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [conversation]);

  // Reset input when switching conversations
  useEffect(() => {
    setInput('');
  }, [conversation?.id]);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (input.trim() && !isLoading) {
      onSendMessage(input);
      setInput('');
    }
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
      <div className={`main-content ${isInitialState ? 'centered' : ''}`}>
        {isInitialState ? (
          <div className="hero-section">
            <h2 className="logo-text">debateX</h2>
            <h1 className="hero-headline">
              Experience the <span className="highlight">frontier</span>
            </h1>
          </div>
        ) : (
          <div className="messages-container">
            {conversation.messages.map((msg, index) => {
              const round3 = msg.round3 || (msg.rounds?.find(r => r.type === 'revise_or_defend')?.data);
              const round4 = msg.round4 || (msg.rounds?.find(r => r.type === 'challenger')?.data);
              return (
                <div key={index} className={`message-group ${msg.role}`}>
                  <div className="message-content">
                    {msg.role === 'user' ? (
                      <div className="user-bubble">{msg.content}</div>
                    ) : (
                      <div className="assistant-stages">
                        {msg.loading?.stage1 && <div className="loading-stage">Round 1: Gathering initial answers...</div>}
                        {msg.stage1 && <Stage1 responses={msg.stage1} />}
                        
                        {msg.loading?.stage2 && <div className="loading-stage">Round 2: Evaluating and ranking answers...</div>}
                        {msg.stage2 && (
                          <Stage2
                            rankings={msg.stage2}
                            labelToModel={msg.metadata?.label_to_model}
                            aggregateRankings={msg.metadata?.aggregate_rankings}
                          />
                        )}
                        
                        {msg.loading?.round3 && <div className="loading-stage">Round 3: Models revising or defending their answers...</div>}
                        {round3 && <Round3 results={round3} />}
                        
                        {msg.loading?.round4 && <div className="loading-stage">Round 4: Challenger identifying weak points...</div>}
                        {round4 && <Round4 result={round4} labelToModel={msg.metadata?.label_to_model} />}

                        {msg.loading?.stage3 && <div className="loading-stage">Stage 3: Generating final answer...</div>}
                        {msg.stage3 && <Stage3 finalResponse={msg.stage3} />}

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
            {isLoading && <div className="loading-global">Thinking...</div>}
            <div ref={messagesEndRef} />
          </div>
        )}
      </div>

      <div className="input-container">
        <form className="input-box" onSubmit={handleSubmit}>
          <textarea
            className="message-input"
            placeholder="How can I help you today?"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={isLoading}
            rows={1}
          />
          <div className="input-footer">
            <button 
              type="submit" 
              className={`send-btn ${input.trim() ? 'active' : ''}`}
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
