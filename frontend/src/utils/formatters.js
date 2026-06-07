/**
 * src/utils/formatters.js
 * Display formatting helpers.
 */

export function formatStatus(status) {
  const map = {
    idle:             'Idle',
    pending:          'Pending',
    routing:          'Routing Query',
    council_formation:'Council Formation',
    debate:           'Debate in Progress',
    judging:          'Judge Evaluating',
    consensus:        'Forming Consensus',
    completed:        'Completed',
    failed:           'Failed',
  };
  return map[status] ?? status;
}

export function formatVerdict(verdict) {
  const map = {
    approve:             'APPROVED',
    reject:              'REJECTED',
    conditional_approve: 'CONDITIONAL',
    inconclusive:        'INCONCLUSIVE',
  };
  return map[verdict] ?? verdict?.toUpperCase() ?? '—';
}

export function verdictColor(verdict) {
  const map = {
    approve:             'var(--color-green)',
    reject:              'var(--color-red)',
    conditional_approve: 'var(--color-amber)',
    inconclusive:        'var(--color-text-dim)',
  };
  return map[verdict] ?? 'var(--color-text-dim)';
}

export function verdictGlow(verdict) {
  const map = {
    approve:             'var(--shadow-glow-green)',
    reject:              'var(--shadow-glow-red)',
    conditional_approve: '0 0 20px rgba(251,191,36,0.4), 0 0 40px rgba(251,191,36,0.15)',
    inconclusive:        'none',
  };
  return map[verdict] ?? 'none';
}

export function formatConfidence(conf) {
  if (conf == null) return '—';
  return `${Math.round(conf)}%`;
}

export function truncate(text, max = 80) {
  if (!text) return '';
  return text.length > max ? text.slice(0, max) + '…' : text;
}

export function timeAgo(dateStr) {
  if (!dateStr) return '';
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1)  return 'just now';
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24)  return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}

/** Animate a numeric value from `from` to `to` over `duration` ms */
export function animateValue(setter, from, to, duration = 1000) {
  const start = performance.now();
  function step(now) {
    const elapsed = now - start;
    const progress = Math.min(elapsed / duration, 1);
    const eased = 1 - Math.pow(1 - progress, 3); // ease-out-cubic
    setter(from + (to - from) * eased);
    if (progress < 1) requestAnimationFrame(step);
  }
  requestAnimationFrame(step);
}
