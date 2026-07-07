import './RoutingPanel.css';

// ── Helpers ────────────────────────────────────────────────────────────────

function shortName(model) {
  if (!model) return '?';
  const parts = model.split('/');
  return (parts[parts.length - 1] || model).replace(/:free$/, '');
}

function isFree(model) {
  return (model || '').endsWith(':free');
}

const CATEGORY_META = {
  'technical/code':        { icon: '⌨', label: 'Technical / Code' },
  'creative':              { icon: '✎', label: 'Creative' },
  'factual/research':      { icon: '🔍', label: 'Factual / Research' },
  'ethical/philosophical': { icon: '⚖', label: 'Ethical / Philosophical' },
  'math/logic':            { icon: '∑', label: 'Math / Logic' },
};

const ROLE_CLASS = {
  'Reasoner':         'role--reasoner',
  "Devil's Advocate": 'role--advocate',
  'Fact-Checker':     'role--factchecker',
  'Steelmanner':      'role--steelmanner',
  'Chairman':         'role--chairman',
};

function formatCost(cost) {
  if (cost == null) return null;
  if (cost === 0) return 'FREE';
  if (cost < 0.01) return `~$${cost.toFixed(4)}`;
  return `~$${cost.toFixed(2)}`;
}

// ── Main component ─────────────────────────────────────────────────────────

export default function RoutingPanel({ routing }) {
  if (!routing) return null;

  const {
    category,
    optimal_council = [],
    chairman,
    role_map = {},
    estimated_cost_usd = null,
    fact_checker_web_access = false,
  } = routing;

  const meta = CATEGORY_META[category] || { icon: '❓', label: category || 'Unknown' };
  const cost = formatCost(estimated_cost_usd);
  const chairmanInCouncil = optimal_council.includes(chairman);

  return (
    <div className="stage routing-stage">
      <h3 className="stage-title">Query Routing</h3>
      <p className="stage-description">
        The query was classified and an optimal council was assembled, with adversarial
        personas assigned per member and the deliberation cost estimated up front.
      </p>

      <div className="rp-card">
        {/* Header row: category + cost */}
        <div className="rp-header">
          <span className="rp-category-badge">
            <span className="rp-category-icon">{meta.icon}</span>
            {meta.label}
          </span>
          {fact_checker_web_access && (
            <span className="rp-flag" title="Fact-Checker verification emphasis is active for this query type">
              Fact-check emphasis
            </span>
          )}
          {cost && (
            <span className="rp-cost" title="Predicted cost of the full 5-round deliberation">
              <span className="rp-cost-label">est. cost</span>
              <span className={`rp-cost-value ${cost === 'FREE' ? 'rp-cost--free' : ''}`}>{cost}</span>
            </span>
          )}
        </div>

        {/* Council members */}
        <div className="rp-list">
          {optimal_council.map((model) => (
            <div key={model} className="rp-row" title={model}>
              <span className={`rp-role-pill ${ROLE_CLASS[role_map[model]] || 'role--reasoner'}`}>
                {role_map[model] || 'Council'}
              </span>
              <span className="rp-model">{shortName(model)}</span>
              <span className="rp-row-right">
                {isFree(model) && <span className="rp-free-tag">free</span>}
                {model === chairman && <span className="rp-chair-tag">chairman</span>}
              </span>
            </div>
          ))}

          {chairman && !chairmanInCouncil && (
            <div className="rp-row rp-row--chairman" title={chairman}>
              <span className="rp-role-pill role--chairman">Chairman</span>
              <span className="rp-model">{shortName(chairman)}</span>
              <span className="rp-row-right">
                {isFree(chairman) && <span className="rp-free-tag">free</span>}
                <span className="rp-chair-note">synthesizes Round 5</span>
              </span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
