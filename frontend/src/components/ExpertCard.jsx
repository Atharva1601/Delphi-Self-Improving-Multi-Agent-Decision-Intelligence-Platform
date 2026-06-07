/**
 * ExpertCard — displays an expert avatar, name, domain chip, and status badge.
 * Used in Council Formation view with stagger animation.
 */
import { useEffect, useState } from 'react';
import { getExpertMeta } from '../utils/experts';
import styles from './ExpertCard.module.css';

export default function ExpertCard({ name, delay = 0, showReady = false }) {
  const [visible, setVisible] = useState(false);
  const [ready, setReady]     = useState(false);
  const meta = getExpertMeta(name);

  useEffect(() => {
    const t1 = setTimeout(() => setVisible(true), delay);
    const t2 = setTimeout(() => setReady(true), delay + 900);
    return () => { clearTimeout(t1); clearTimeout(t2); };
  }, [delay]);

  if (!visible) return <div className={styles.placeholder} />;

  return (
    <div className={`${styles.card} glass animate-fade-slide-up`}>
      <div className={styles.avatar} style={{ background: `${meta.color}22`, borderColor: `${meta.color}44` }}>
        <span className={styles.icon}>{meta.icon}</span>
      </div>
      <div className={styles.info}>
        <p className={styles.name}>{name}</p>
        <span className={styles.domain} style={{ color: meta.color }}>{meta.label}</span>
      </div>
      <div className={`${styles.badge} ${ready || showReady ? styles.badgeReady : styles.badgeJoining}`}>
        {ready || showReady ? '✓ Ready' : (
          <span className="loading-dots">
            <span /><span /><span />
          </span>
        )}
      </div>
    </div>
  );
}
