import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import './Stage3.css';

export default function Stage3({ finalResponse }) {
  if (!finalResponse) {
    return null;
  }

  return (
    <div className="stage stage3">
      <h3 className="stage-title">Round 5: Chairman Synthesis</h3>
      <div className="final-response">
        <div className="moderator-label">
          Chairman: {(finalResponse.model.split('/').pop() || finalResponse.model).replace(/:free$/, '')}
        </div>
        <div className="final-text markdown-content">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>{finalResponse.response}</ReactMarkdown>
        </div>
      </div>
    </div>
  );
}
