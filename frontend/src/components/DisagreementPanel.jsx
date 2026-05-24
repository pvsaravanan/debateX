import { useState } from 'react';
import './DisagreementPanel.css';

// ── Helpers ────────────────────────────────────────────────────────────────

function shortName(model) {
  if (!model) return '?';
  const parts = model.split('/');
  return parts[parts.length - 1] || model;
}

function stanceColor(stance) {
  switch ((stance || '').toUpperCase()) {
    case 'AGREE':    return 'agree';
    case 'PARTIAL':  return 'partial';
    case 'DISAGREE': return 'disagree';
    default:         return 'unknown';
  }
}

function scoreBar(score) {
  const pct = Math.round((score || 0) * 100);
  return (
    <div className="dp-score-bar-wrap">
      <div className="dp-score-bar-track">
        <div
          className={`dp-score-bar-fill ${pct >= 70 ? 'high' : pct >= 40 ? 'mid' : 'low'}`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="dp-score-label">{pct}%</span>
    </div>
  );
}

// ── Sub-components ──────────────────────────────────────────────────────────

function ConsensusZone({ points }) {
  if (!points || points.length === 0) return null;
  return (
    <div className="dp-zone dp-zone--consensus">
      <h4 className="dp-zone-title">
        <span className="dp-zone-badge badge--consensus">✓ CONSENSUS</span>
        All models agreed on these points
      </h4>
      <ul className="dp-consensus-list">
        {points.map((pt, i) => (
          <li key={i} className="dp-consensus-item">
            <span className="dp-check">✓</span>
            {pt}
          </li>
        ))}
      </ul>
    </div>
  );
}

function DisagreementZone({ zone, index }) {
  const [open, setOpen] = useState(false);

  return (
    <div className={`dp-zone dp-zone--disagree ${zone.human_decision_needed ? 'dp-zone--human' : ''}`}>
      <div className="dp-disagree-header" onClick={() => setOpen(!open)} role="button" tabIndex={0}
           onKeyDown={e => e.key === 'Enter' && setOpen(!open)}>
        <div className="dp-disagree-title-row">
          <span className="dp-zone-badge badge--disagree">⚡ DIVERGED</span>
          {zone.human_decision_needed && (
            <span className="dp-zone-badge badge--human">🧑 Human Input Needed</span>
          )}
          <span className="dp-disagree-claim">{zone.claim}</span>
        </div>
        <span className="dp-chevron">{open ? '▲' : '▼'}</span>
      </div>

      {open && (
        <div className="dp-disagree-body">
          {/* Per-model positions */}
          <div className="dp-positions">
            <h5 className="dp-sub-title">Model Positions</h5>
            {Object.entries(zone.model_positions || {}).map(([model, pos]) => (
              <div key={model} className="dp-position-row">
                <span className="dp-model-chip">{shortName(model)}</span>
                <span className="dp-position-text">{pos}</span>
              </div>
            ))}
          </div>

          {/* Divergence reason */}
          {zone.divergence_reason && (
            <div className="dp-reason">
              <span className="dp-reason-label">Why they diverged:</span>
              <span className="dp-reason-text">{zone.divergence_reason}</span>
            </div>
          )}

          {/* Confidence scores */}
          {zone.confidence_scores && zone.confidence_scores.length > 0 && (
            <div className="dp-scores">
              <h5 className="dp-sub-title">Confidence Map</h5>
              {zone.confidence_scores.map((cs, i) => (
                <div key={i} className="dp-score-row">
                  <span className="dp-model-chip">{shortName(cs.model)}</span>
                  <span className={`dp-stance-badge stance--${stanceColor(cs.stance)}`}>{cs.stance}</span>
                  {scoreBar(cs.score)}
                  {cs.reasoning && <span className="dp-score-reasoning">{cs.reasoning}</span>}
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ── Main Panel ──────────────────────────────────────────────────────────────

export default function DisagreementPanel({ disagreementMap }) {
  if (!disagreementMap) return null;

  const {
    consensus_points = [],
    disagreement_zones = [],
    overall_consensus_score = null,
    requires_human_review = false,
  } = disagreementMap;

  const pct = overall_consensus_score != null
    ? Math.round(overall_consensus_score * 100)
    : null;

  const hasContent = consensus_points.length > 0 || disagreement_zones.length > 0;
  if (!hasContent) return null;

  return (
    <div className="dp-panel">
      {/* Header */}
      <div className="dp-header">
        <div className="dp-header-left">
          <span className="dp-icon">⚖</span>
          <h3 className="dp-title">Disagreement Analysis</h3>
        </div>
        <div className="dp-header-right">
          {pct != null && (
            <div className="dp-consensus-score">
              <span className="dp-consensus-score-label">Council consensus</span>
              <div className="dp-consensus-score-bar">
                <div
                  className={`dp-consensus-score-fill ${pct >= 70 ? 'high' : pct >= 40 ? 'mid' : 'low'}`}
                  style={{ width: `${pct}%` }}
                />
              </div>
              <span className="dp-consensus-score-pct">{pct}%</span>
            </div>
          )}
          {requires_human_review && (
            <span className="dp-human-flag">🧑 Human review recommended</span>
          )}
        </div>
      </div>

      {/* Consensus zone */}
      <ConsensusZone points={consensus_points} />

      {/* Disagreement zones */}
      {disagreement_zones.length > 0 && (
        <div className="dp-section">
          <h4 className="dp-section-title">
            <span className="dp-zone-badge badge--disagree">⚡ DISAGREEMENTS</span>
            {disagreement_zones.length} divergent point{disagreement_zones.length !== 1 ? 's' : ''} detected
          </h4>
          {disagreement_zones.map((zone, i) => (
            <DisagreementZone key={i} zone={zone} index={i} />
          ))}
        </div>
      )}
    </div>
  );
}
