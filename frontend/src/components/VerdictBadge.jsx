/**
 * VerdictBadge — large colored verdict with glow effect.
 */
import { formatVerdict, verdictColor, verdictGlow } from '../utils/formatters';
import styles from './VerdictBadge.module.css';

export default function VerdictBadge({ verdict }) {
  const label = formatVerdict(verdict);
  const color = verdictColor(verdict);
  const glow  = verdictGlow(verdict);

  return (
    <div
      className={`${styles.badge} animate-scale-in`}
      style={{ '--verdict-color': color, '--verdict-glow': glow }}
    >
      <div className={styles.glow} />
      <span className={styles.label}>{label}</span>
    </div>
  );
}
