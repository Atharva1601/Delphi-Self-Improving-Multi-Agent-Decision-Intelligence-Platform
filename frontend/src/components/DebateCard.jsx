/**
 * DebateCard — a single argument card in the Debate Arena.
 * Shows speaker, round badge, and the argument text.
 */
import { getExpertMeta } from '../utils/experts';
import styles from './DebateCard.module.css';

const ROUND_LABELS = {
  1: { label: 'Analysis',  color: 'var(--color-indigo)' },
  2: { label: 'Challenge', color: 'var(--color-red)' },
  3: { label: 'Defense',   color: 'var(--color-gold)' },
};

export default function DebateCard({ round, speakerName, content, targetName, animDelay = 0 }) {
  const meta = getExpertMeta(speakerName);
  const roundInfo = ROUND_LABELS[round] ?? ROUND_LABELS[1];

  return (
    <div
      className={`${styles.card} glass animate-fade-slide-up`}
      style={{ animationDelay: `${animDelay}ms` }}
    >
      <div className={styles.header}>
        <div className={styles.speaker}>
          <span className={styles.icon} style={{ background: `${meta.color}22` }}>{meta.icon}</span>
          <div>
            <p className={styles.name}>{speakerName}</p>
            {targetName && round === 2 && (
              <p className={styles.target}>↳ challenging {targetName}</p>
            )}
          </div>
        </div>
        <span
          className={styles.roundBadge}
          style={{ color: roundInfo.color, borderColor: `${roundInfo.color}44`, background: `${roundInfo.color}14` }}
        >
          R{round} · {roundInfo.label}
        </span>
      </div>
      <p className={styles.content}>{content}</p>
    </div>
  );
}
