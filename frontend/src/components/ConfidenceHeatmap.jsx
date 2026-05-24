import { useState } from 'react';
import './ConfidenceHeatmap.css';

// ── Helpers ───────────────────────────────────────────────────────────────

function shortName(model) {
  if (!model) return '?';
  // e.g. "groq/llama-3.3-70b-versatile" → "llama-3.3-70b-versatile"
  //      "deepseek/deepseek-v4-flash:free" → "deepseek-v4-flash"
  const parts = model.split('/');
  return (parts[parts.length - 1] || model).replace(/:free$/, '');
}

function tierClass(tier) {
  switch ((tier || '').toUpperCase()) {
    case 'HIGH':   return 'tier--high';
    case 'MEDIUM': return 'tier--medium';
    case 'LOW':    return 'tier--low';
    default:       return 'tier--unknown';
  }
}

function confidenceColor(score) {
  // 0 → red, 0.5 → amber, 1 → green  (CSS hue: 0 → 120)
  const hue = Math.round(score * 120);
  return `hsl(${hue}, 80%, 55%)`;
}

function SimBadge({ label, value }) {
  const pct = Math.round((value || 0) * 100);
  return (
    <span className="chm-sim-badge" title={`Cosine similarity: ${pct}%`}>
      <span className="chm-sim-label">{label}</span>
      <span className="chm-sim-val">{pct}%</span>
    </span>
  );
}

// ── Model row ─────────────────────────────────────────────────────────────

function ModelRow({ mcs }) {
  const [expanded, setExpanded] = useState(false);
  const pct = Math.round((mcs.confidence || 0) * 100);
  const barColor = confidenceColor(mcs.confidence || 0);

  return (
    <div className={`chm-row ${expanded ? 'chm-row--expanded' : ''}`}>
      {/* Main info row */}
      <div
        className="chm-row-main"
        onClick={() => setExpanded(!expanded)}
        role="button"
        tabIndex={0}
        onKeyDown={e => e.key === 'Enter' && setExpanded(!expanded)}
        aria-expanded={expanded}
      >
        {/* Model name */}
        <span className="chm-model-name" title={mcs.model}>{shortName(mcs.model)}</span>

        {/* Tier badge */}
        <span className={`chm-tier-badge ${tierClass(mcs.tier)}`}>{mcs.tier || '?'}</span>

        {/* Confidence bar */}
        <div className="chm-bar-wrap">
          <div className="chm-bar-track">
            <div
              className="chm-bar-fill"
              style={{ width: `${pct}%`, background: barColor }}
            />
          </div>
          <span className="chm-bar-pct" style={{ color: barColor }}>{pct}%</span>
        </div>

        {/* Expand arrow */}
        <span className="chm-chevron">{expanded ? '▲' : '▼'}</span>
      </div>

      {/* Expanded probe detail */}
      {expanded && (
        <div className="chm-detail">
          {/* Pairwise similarities */}
          <div className="chm-sims">
            <SimBadge label="T0.3↔T0.7" value={mcs.sim_01} />
            <SimBadge label="T0.3↔T1.0" value={mcs.sim_02} />
            <SimBadge label="T0.7↔T1.0" value={mcs.sim_12} />
            <span className="chm-sim-avg">
              avg cosine: <strong>{Math.round((mcs.avg_similarity || 0) * 100)}%</strong>
            </span>
          </div>

          {/* Temperature probes */}
          {mcs.probes && mcs.probes.length > 0 && (
            <div className="chm-probes">
              {mcs.probes.map((probe, i) => (
                <div key={i} className="chm-probe-card">
                  <span className="chm-probe-temp">T={probe.temperature}</span>
                  <p className="chm-probe-text">
                    {probe.response
                      ? (probe.response.length > 280
                          ? probe.response.slice(0, 280) + '…'
                          : probe.response)
                      : <em className="chm-probe-empty">No response</em>
                    }
                  </p>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ── Main component ────────────────────────────────────────────────────────

export default function ConfidenceHeatmap({ data }) {
  if (!data || !data.scores || Object.keys(data.scores).length === 0) return null;

  const scores = Object.values(data.scores);
  // Sort by confidence descending
  scores.sort((a, b) => (b.confidence || 0) - (a.confidence || 0));

  const avgConf = scores.reduce((s, m) => s + (m.confidence || 0), 0) / scores.length;
  const highCount   = scores.filter(m => m.tier === 'HIGH').length;
  const mediumCount = scores.filter(m => m.tier === 'MEDIUM').length;
  const lowCount    = scores.filter(m => m.tier === 'LOW').length;

  return (
    <div className="chm-panel">
      {/* Header */}
      <div className="chm-header">
        <div className="chm-header-left">
          <span className="chm-icon">🧠</span>
          <h3 className="chm-title">Pre-flight Metacognition</h3>
          <span className="chm-subtitle">
            Each model sampled 3× at T=0.3 / 0.7 / 1.0 — consistency → confidence
          </span>
        </div>
        <div className="chm-header-stats">
          <div className="chm-stat">
            <span className="chm-stat-val" style={{ color: confidenceColor(avgConf) }}>
              {Math.round(avgConf * 100)}%
            </span>
            <span className="chm-stat-label">avg confidence</span>
          </div>
          <div className="chm-tier-pills">
            {highCount   > 0 && <span className="chm-tier-badge tier--high">{highCount} HIGH</span>}
            {mediumCount > 0 && <span className="chm-tier-badge tier--medium">{mediumCount} MED</span>}
            {lowCount    > 0 && <span className="chm-tier-badge tier--low">{lowCount} LOW</span>}
          </div>
        </div>
      </div>

      {/* Model rows */}
      <div className="chm-rows">
        {scores.map((mcs) => (
          <ModelRow key={mcs.model} mcs={mcs} />
        ))}
      </div>

      {/* Footer note */}
      <p className="chm-footer">
        High-confidence scores indicate strong self-consistency across temperatures.
        The Chairman weights these scores when synthesising the final answer.
      </p>
    </div>
  );
}
