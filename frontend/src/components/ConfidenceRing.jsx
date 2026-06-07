/**
 * ConfidenceRing — animated SVG ring filling to the confidence percentage.
 */
import { useEffect, useRef, useState } from 'react';
import { animateValue } from '../utils/formatters';
import styles from './ConfidenceRing.module.css';

const SIZE    = 160;
const STROKE  = 10;
const RADIUS  = (SIZE - STROKE) / 2;
const CIRCUM  = 2 * Math.PI * RADIUS;

export default function ConfidenceRing({ confidence = 0 }) {
  const [displayed, setDisplayed] = useState(0);

  useEffect(() => {
    if (confidence > 0) {
      animateValue(setDisplayed, 0, confidence, 1200);
    }
  }, [confidence]);

  const offset = CIRCUM - (displayed / 100) * CIRCUM;

  const color =
    displayed >= 70 ? 'var(--color-green)' :
    displayed >= 40 ? 'var(--color-gold)'  :
                      'var(--color-red)';

  return (
    <div className={styles.wrap}>
      <svg width={SIZE} height={SIZE} className={styles.svg}>
        {/* Background track */}
        <circle
          cx={SIZE / 2} cy={SIZE / 2} r={RADIUS}
          fill="none"
          stroke="rgba(255,255,255,0.06)"
          strokeWidth={STROKE}
        />
        {/* Filled arc */}
        <circle
          cx={SIZE / 2} cy={SIZE / 2} r={RADIUS}
          fill="none"
          stroke={color}
          strokeWidth={STROKE}
          strokeLinecap="round"
          strokeDasharray={CIRCUM}
          strokeDashoffset={offset}
          transform={`rotate(-90 ${SIZE/2} ${SIZE/2})`}
          style={{
            filter: `drop-shadow(0 0 8px ${color})`,
            transition: 'stroke 0.3s',
          }}
        />
      </svg>
      <div className={styles.label}>
        <span className={styles.number} style={{ color }}>{Math.round(displayed)}</span>
        <span className={styles.pct}>%</span>
        <span className={styles.sub}>confidence</span>
      </div>
    </div>
  );
}
