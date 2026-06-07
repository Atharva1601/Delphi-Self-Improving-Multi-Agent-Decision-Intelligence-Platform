/**
 * ErrorView.jsx — Graceful error / failed state.
 */
import styles from './ErrorView.module.css';

export default function ErrorView({ error, onReset }) {
  return (
    <div className={styles.wrap}>
      <div className={`${styles.card} glass-strong animate-scale-in`}>
        <div className={styles.icon}>⚠</div>
        <h2 className={styles.title}>Pipeline Failed</h2>
        <p className={styles.message}>{error || 'An unexpected error occurred.'}</p>
        <button id="retry-btn" className="btn btn-ghost" onClick={onReset}>
          ← Try a new query
        </button>
      </div>
    </div>
  );
}
