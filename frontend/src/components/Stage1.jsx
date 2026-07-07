import { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import './Stage1.css';

export default function Stage1({ responses, roleMap }) {
  const [activeTab, setActiveTab] = useState(0);

  if (!responses || responses.length === 0) {
    return null;
  }

  const activeModel = responses[activeTab].model;
  const activeRole = roleMap?.[activeModel];

  return (
    <div className="stage stage1">
      <h3 className="stage-title">Round 1: Initial Answers</h3>

      <div className="tabs">
        {responses.map((resp, index) => (
          <button
            key={index}
            className={`tab ${activeTab === index ? 'active' : ''}`}
            onClick={() => setActiveTab(index)}
          >
            {(resp.model.split('/').pop() || resp.model).replace(/:free$/, '')}
          </button>
        ))}
      </div>

      <div className="tab-content">
        <div className="model-name">
          {activeModel}
          {activeRole && <span className="model-role-badge"> · {activeRole}</span>}
        </div>
        <div className="response-text markdown-content">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>{responses[activeTab].response}</ReactMarkdown>
        </div>
      </div>
    </div>
  );
}
