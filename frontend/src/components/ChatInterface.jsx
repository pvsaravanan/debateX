import { useState, useEffect, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import Stage1 from './Stage1';
import Stage2 from './Stage2';
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
            {conversation.messages.map((msg, index) => (
              <div key={index} className={`message-group ${msg.role}`}>
                <div className="message-content">
                  {msg.role === 'user' ? (
                    <div className="user-bubble">{msg.content}</div>
                  ) : (
                    <div className="assistant-stages">
                      {msg.loading?.stage1 && <div className="loading-stage">Gathering consensus...</div>}
                      {msg.stage1 && <Stage1 responses={msg.stage1} />}
                      {msg.stage2 && (
                        <Stage2
                          rankings={msg.stage2}
                          labelToModel={msg.metadata?.label_to_model}
                          aggregateRankings={msg.metadata?.aggregate_rankings}
                        />
                      )}
                      {msg.stage3 && <Stage3 finalResponse={msg.stage3} />}
                      
                      {msg.error && (
                        <div className="error-panel">
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
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </div>
            ))}
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
