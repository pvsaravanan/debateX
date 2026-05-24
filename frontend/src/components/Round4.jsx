import { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import './Round4.css';

const WarningIcon = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="critique-icon">
    <path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z" />
    <line x1="12" y1="9" x2="12" y2="13" />
    <line x1="12" y1="17" x2="12.01" y2="17" />
  </svg>
);

const TargetIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="12" cy="12" r="10" />
    <circle cx="12" cy="12" r="6" />
    <circle cx="12" cy="12" r="2" />
  </svg>
);

const ChevronIcon = ({ isOpen }) => (
  <svg 
    width="16" 
    height="16" 
    viewBox="0 0 24 24" 
    fill="none" 
    stroke="currentColor" 
    strokeWidth="2" 
    strokeLinecap="round" 
    strokeLinejoin="round"
    style={{ transform: isOpen ? 'rotate(180deg)' : 'rotate(0deg)', transition: 'transform 0.2s ease' }}
  >
    <polyline points="6 9 12 15 18 9" />
  </svg>
);

export default function Round4({ result, labelToModel }) {
  const [isAccordionOpen, setIsAccordionOpen] = useState(false);

  if (!result) {
    return null;
  }

  const challengerShort = result.model.split('/')[1] || result.model;
  const targetShort = result.target_model ? (result.target_model.split('/')[1] || result.target_model) : 'Target Model';

  return (
    <div className="stage round4">
      <h3 className="stage-title">Round 4: Challenger Critique</h3>
      <p className="stage-description">
        The lowest-ranked model was assigned as the <strong>Challenger</strong>. 
        Its sole objective is to aggressively stress-test and expose the weakest points or logical flaws in the leading model's answer.
      </p>

      <div className="critique-container">
        <div className="critique-header">
          <div className="challenger-info">
            <WarningIcon />
            <span className="challenger-label">CHALLENGER:</span>
            <span className="challenger-name">{challengerShort}</span>
          </div>
          <div className="target-info">
            <TargetIcon />
            <span className="target-label">TARGETING:</span>
            <span className="target-name">{targetShort}</span>
          </div>
        </div>

        <div className="critique-content markdown-content">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>
            {result.response}
          </ReactMarkdown>
        </div>
      </div>

      {result.target_response && (
        <div className="target-accordion">
          <button 
            className="accordion-header" 
            onClick={() => setIsAccordionOpen(!isAccordionOpen)}
          >
            <span className="accordion-title">
              <TargetIcon />
              View Leading Answer Under Attack ({targetShort})
            </span>
            <ChevronIcon isOpen={isAccordionOpen} />
          </button>
          
          {isAccordionOpen && (
            <div className="accordion-content">
              <div className="target-response-text markdown-content">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                  {result.target_response}
                </ReactMarkdown>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
