import { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import './Round3.css';

export default function Round3({ results }) {
  const [activeTab, setActiveTab] = useState(0);

  if (!results || results.length === 0) {
    return null;
  }

  return (
    <div className="stage round3">
      <h3 className="stage-title">Round 3: Revise or Defend</h3>
      <p className="stage-description">
        Based on peer evaluations and aggregate rankings, each model was given the opportunity to either 
        <strong> Revise</strong> their response to address criticisms, or <strong>Defend</strong> their original reasoning.
      </p>

      <div className="tabs">
        {results.map((res, index) => {
          const modelShort = res.model.split('/')[1] || res.model;
          const decision = res.decision || 'REVISE';
          return (
            <button
              key={index}
              className={`tab ${activeTab === index ? 'active' : ''}`}
              onClick={() => setActiveTab(index)}
            >
              <span className="tab-model-name">{modelShort}</span>
              <span className={`decision-badge ${decision.toLowerCase()}`}>
                {decision}
              </span>
            </button>
          );
        })}
      </div>

      <div className="tab-content">
        <div className="model-header-row">
          <div className="model-name">{results[activeTab].model}</div>
          <div className={`status-pill ${results[activeTab].decision?.toLowerCase()}`}>
            Chose to {results[activeTab].decision === 'DEFEND' ? 'Defend original answer' : 'Revise answer'}
          </div>
        </div>
        <div className="response-text markdown-content">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>
            {results[activeTab].response}
          </ReactMarkdown>
        </div>
      </div>
    </div>
  );
}
