import { useState } from 'react';
import RoutingPanel from './RoutingPanel';
import ConfidenceHeatmap from './ConfidenceHeatmap';
import Stage1 from './Stage1';
import Stage2 from './Stage2';
import Round3 from './Round3';
import Round4 from './Round4';
import './DeliberationTrace.css';

// Streaming phases in order: [loading-flag key, live status label]
const PHASES = [
  ['routing',       'Classifying query & assembling the council'],
  ['metacognition', 'Probing model self-consistency'],
  ['round1',        'Council drafting initial answers'],
  ['round2',        'Anonymized peer review in progress'],
  ['round3',        'Models revising or defending their answers'],
  ['round4',        'Challenger attacking the leading answer'],
  ['round5',        'Chairman synthesizing the final answer'],
];

const CATEGORY_LABELS = {
  'technical/code':        'technical',
  'creative':              'creative',
  'factual/research':      'factual',
  'ethical/philosophical': 'ethical',
  'math/logic':            'math',
};

const ChevronIcon = ({ open }) => (
  <svg
    width="14" height="14" viewBox="0 0 24 24" fill="none"
    stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"
    style={{ transform: open ? 'rotate(180deg)' : 'rotate(0deg)', transition: 'transform 0.2s ease' }}
  >
    <polyline points="6 9 12 15 18 9" />
  </svg>
);

const CouncilIcon = () => (
  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
    <circle cx="9" cy="7" r="4" />
    <path d="M23 21v-2a4 4 0 0 0-3-3.87" />
    <path d="M16 3.13a4 4 0 0 1 0 7.75" />
  </svg>
);

export default function DeliberationTrace({ msg, routing, round3, round4, metacognition }) {
  const [open, setOpen] = useState(false);

  const activeIndex = PHASES.findIndex(([key]) => msg.loading?.[key]);
  const isStreaming = activeIndex !== -1;
  const activeLabel = isStreaming ? PHASES[activeIndex][1] : null;

  const hasAnyData = !!(routing || metacognition || msg.stage1 || msg.stage2 || round3 || round4);
  if (!isStreaming && !hasAnyData) return null;

  const councilSize = msg.stage1?.length || routing?.optimal_council?.length || 0;
  const category = CATEGORY_LABELS[routing?.category];
  const finished = !!msg.stage3;

  let summary;
  if (finished) {
    summary = `Deliberated with ${councilSize} models across 5 rounds${category ? ` · ${category} query` : ''}`;
  } else if (!isStreaming) {
    summary = 'Deliberation trace (incomplete)';
  }

  const progressPct = isStreaming
    ? Math.round((activeIndex / PHASES.length) * 100)
    : 100;

  return (
    <div className={`trace ${isStreaming ? 'trace--streaming' : ''}`}>
      <button
        className="trace-header"
        onClick={() => setOpen(!open)}
        aria-expanded={open}
      >
        <span className={`trace-icon ${isStreaming ? 'trace-icon--pulse' : ''}`}>
          <CouncilIcon />
        </span>
        {isStreaming ? (
          <span className="trace-label shimmer-text">{activeLabel}…</span>
        ) : (
          <span className="trace-label">{summary}</span>
        )}
        <span className="trace-toggle-hint">{open ? 'Hide' : isStreaming ? 'Watch live' : 'Inspect'}</span>
        <ChevronIcon open={open} />
      </button>

      {isStreaming && (
        <div className="trace-progress">
          <div className="trace-progress-fill" style={{ width: `${Math.max(progressPct, 6)}%` }} />
        </div>
      )}

      {open && (
        <div className="trace-body">
          {msg.loading?.routing && <div className="loading-stage">Classifying query and assembling the council…</div>}
          {routing && <RoutingPanel routing={routing} />}

          {msg.loading?.metacognition && <div className="loading-stage">Probing model self-consistency…</div>}
          {metacognition && <ConfidenceHeatmap data={metacognition} />}

          {msg.loading?.round1 && <div className="loading-stage">Round 1: Council drafting initial answers…</div>}
          {msg.stage1 && <Stage1 responses={msg.stage1} roleMap={routing?.role_map} />}

          {msg.loading?.round2 && <div className="loading-stage">Round 2: Anonymized peer review and ranking…</div>}
          {msg.stage2 && (
            <Stage2
              rankings={msg.stage2}
              labelToModel={msg.metadata?.label_to_model}
              aggregateRankings={msg.metadata?.aggregate_rankings}
            />
          )}

          {msg.loading?.round3 && <div className="loading-stage">Round 3: Models revising or defending their answers…</div>}
          {round3 && <Round3 results={round3} />}

          {msg.loading?.round4 && <div className="loading-stage">Round 4: Challenger identifying weak points…</div>}
          {round4 && <Round4 result={round4} labelToModel={msg.metadata?.label_to_model} roleMap={routing?.role_map} />}

          {msg.loading?.round5 && <div className="loading-stage">Round 5: Chairman synthesizing the final answer…</div>}
        </div>
      )}
    </div>
  );
}
