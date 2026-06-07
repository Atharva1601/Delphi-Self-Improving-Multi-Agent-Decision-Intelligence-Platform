/**
 * Chamber.jsx — Decision Chamber: landing screen with query input.
 */
import { useState, useEffect, useRef } from 'react';
import { submitDecision, listDecisions } from '../api/client';
import { formatVerdict, verdictColor, truncate, timeAgo } from '../utils/formatters';
import styles from './Chamber.module.css';

const MAX_CHARS = 2000;

export default function Chamber({ onStart, onViewDashboard }) {
  const [query, setQuery]         = useState('');
  const [loading, setLoading]     = useState(false);
  const [error, setError]         = useState('');
  const [history, setHistory]     = useState([]);
  const canvasRef = useRef(null);

  // Load recent decisions
  useEffect(() => {
    listDecisions(6).then(setHistory).catch(() => {});
  }, []);

  // Ambient particle canvas
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    let animId;

    const resize = () => {
      canvas.width  = canvas.offsetWidth;
      canvas.height = canvas.offsetHeight;
    };
    resize();
    window.addEventListener('resize', resize);

    const particles = Array.from({ length: 60 }, () => ({
      x: Math.random() * canvas.width,
      y: Math.random() * canvas.height,
      r: Math.random() * 1.5 + 0.5,
      dx: (Math.random() - 0.5) * 0.3,
      dy: (Math.random() - 0.5) * 0.3,
      alpha: Math.random() * 0.5 + 0.1,
    }));

    const draw = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      particles.forEach(p => {
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(108, 99, 255, ${p.alpha})`;
        ctx.fill();
        p.x += p.dx;
        p.y += p.dy;
        if (p.x < 0 || p.x > canvas.width)  p.dx *= -1;
        if (p.y < 0 || p.y > canvas.height) p.dy *= -1;
      });
      animId = requestAnimationFrame(draw);
    };
    draw();

    return () => {
      cancelAnimationFrame(animId);
      window.removeEventListener('resize', resize);
    };
  }, []);

  const [mock, setMock] = useState(false);

  const handleSubmit = async () => {
    const trimmed = query.trim();
    if (trimmed.length < 10) { setError('Query must be at least 10 characters.'); return; }
    setError('');
    setLoading(true);
    try {
      const res = await submitDecision(trimmed, mock);
      onStart(res.case_id);
    } catch (e) {
      setError(e.message);
      setLoading(false);
    }
  };

  const handleKey = (e) => {
    if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) handleSubmit();
  };

  const handleDemoClick = (q) => {
    setQuery(q);
    setMock(true); // Auto-enable mock mode for presets to bypass rate limits
  };

  const DEMO_QUERIES = [
    'Should we launch a fully autonomous, AI-driven digital banking platform globally?',
    'Should we deploy AI-assisted diagnostics in our hospital emergency department?',
    'Should we expand into the Southeast Asian market within the next 12 months?',
  ];

  return (
    <div className={styles.chamber}>
      <canvas ref={canvasRef} className={styles.canvas} />

      <div className={styles.content}>
        {/* Header toolbar */}
        <div className={styles.header}>
          <button className={`${styles.dashboardBtn} glass`} onClick={onViewDashboard}>
            📊 System Dashboard
          </button>
        </div>

        {/* Hero */}
        <div className={`${styles.hero} animate-fade-slide-up`}>
          <div className={styles.logo}>
            <span className={styles.logoIcon}>⚖</span>
            <span className={styles.logoText}>DELPHI</span>
          </div>
          <h1 className={styles.tagline}>Multi-Agent Decision Intelligence</h1>
          <p className={styles.sub}>
            Expert councils debate. Judges evaluate. Consensus emerges.
          </p>
        </div>

        {/* Input panel */}
        <div className={`${styles.inputPanel} glass-strong animate-fade-slide-up`} style={{ animationDelay: '100ms' }}>
          <label className={styles.inputLabel} htmlFor="query-input">
            State your decision query
          </label>
          <textarea
            id="query-input"
            className={styles.textarea}
            placeholder="e.g. Should we launch a fully autonomous, AI-driven digital banking platform globally?"
            value={query}
            onChange={e => setQuery(e.target.value.slice(0, MAX_CHARS))}
            onKeyDown={handleKey}
            rows={4}
          />
          <div className={styles.inputFooter}>
            <span className={`${styles.charCount} ${query.length > MAX_CHARS * 0.9 ? styles.charCountWarn : ''}`}>
              {query.length} / {MAX_CHARS}
            </span>
            <span className={styles.hint}>⌘↵ to submit</span>
          </div>

          <div className={styles.toggleRow}>
            <label className={styles.checkboxLabel}>
              <input
                type="checkbox"
                id="mock-checkbox"
                className={styles.checkboxInput}
                checked={mock}
                onChange={e => setMock(e.target.checked)}
              />
              <span className={styles.checkboxText}>Run in Demo Mode (Simulated)</span>
            </label>
          </div>

          {error && <p className={styles.error}>{error}</p>}

          <button
            id="submit-btn"
            className={`btn btn-primary ${styles.submitBtn}`}
            onClick={handleSubmit}
            disabled={loading || query.trim().length < 10}
          >
            {loading ? (
              <>
                <span className={styles.spinner} />
                Assembling Council…
              </>
            ) : (
              <>
                <span>⚡</span> Convene the Council
              </>
            )}
          </button>
        </div>

        {/* Demo queries */}
        <div className={`${styles.demos} animate-fade-slide-up`} style={{ animationDelay: '200ms' }}>
          <p className={styles.demoLabel}>Try a demo scenario:</p>
          <div className={styles.demoChips}>
            {DEMO_QUERIES.map((q, i) => (
              <button
                key={i}
                id={`demo-query-${i}`}
                className={`${styles.demoChip} glass`}
                onClick={() => handleDemoClick(q)}
              >
                {truncate(q, 55)}
              </button>
            ))}
          </div>
        </div>

        {/* Recent decisions */}
        {history.length > 0 && (
          <div className={`${styles.history} animate-fade-slide-up`} style={{ animationDelay: '300ms' }}>
            <p className={styles.historyLabel}>Recent Decisions</p>
            <div className={styles.historyList}>
              {history.map(c => (
                <div key={c.case_id} className={`${styles.historyItem} glass`}>
                  <p className={styles.historyQuery}>{truncate(c.query, 60)}</p>
                  <div className={styles.historyMeta}>
                    {c.verdict && (
                      <span
                        className={styles.historyVerdict}
                        style={{ color: verdictColor(c.verdict) }}
                      >
                        {formatVerdict(c.verdict)}
                      </span>
                    )}
                    {!c.verdict && (
                      <span className={styles.historyStatus}>{c.status}</span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
