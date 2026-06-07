import { useState, useEffect } from 'react';
import { getExpertMeta } from '../utils/experts';
import RoundTable from '../components/RoundTable';
import styles from './Council.module.css';

export default function Council({ stageData, status }) {
  const members = stageData?.council_members ?? [];
  const routing  = stageData?.routing ?? {};
  const isForming = status === 'council_formation';

  const [showPopup, setShowPopup] = useState(false);
  const [popupDone, setPopupDone] = useState(false);

  useEffect(() => {
    if (members.length > 0 && !popupDone && !showPopup) {
      setShowPopup(true);
      const t = setTimeout(() => {
        setShowPopup(false);
        setPopupDone(true);
      }, 2500);
      return () => clearTimeout(t);
    }
  }, [members, popupDone, showPopup]);

  return (
    <div className={styles.council}>
      <div className={styles.header}>
        <div className={`${styles.statusDot} ${isForming ? styles.pulsing : ''}`} />
        <h2 className={styles.title}>
          {isForming ? 'Assembling your expert council…' : 'Council Assembled'}
        </h2>
      </div>

      {(routing.industry || routing.domains?.length) && (
        <div className={`${styles.routingInfo} glass animate-fade-slide-up`}>
          {routing.industry && (
            <div className={styles.routingItem}>
              <span className={styles.routingKey}>Industry</span>
              <span className={`chip chip-indigo`}>{routing.industry}</span>
            </div>
          )}
          {routing.domains?.length > 0 && (
            <div className={styles.routingItem}>
              <span className={styles.routingKey}>Domains</span>
              <div className={styles.domainChips}>
                {routing.domains.map(d => (
                  <span key={d} className="chip chip-gold">{d}</span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {members.length === 0 && isForming && (
        <div className={`${styles.waiting} animate-fade-in`}>
          <div className="loading-dots"><span /><span /><span /></div>
          <p>Selecting experts for this decision…</p>
        </div>
      )}

      {/* Selected Experts Pop-up overlay */}
      {showPopup && (
        <div className={styles.popupOverlay}>
          <div className={`${styles.popupCard} glass-strong animate-scale-in`}>
            <div className={styles.popupIcon}>⚖️</div>
            <h3 className={styles.popupTitle}>Expert Council Selected</h3>
            <p className={styles.popupSubtitle}>Conjoining the following experts at the round table:</p>
            <div className={styles.popupGrid}>
              {members.map((name, i) => {
                const meta = getExpertMeta(name);
                return (
                  <div
                    key={name}
                    className={`${styles.popupItem} glass animate-fade-slide-up`}
                    style={{ animationDelay: `${i * 120}ms`, borderColor: meta.color }}
                  >
                    <span className={styles.popupExpertIcon}>{meta.icon}</span>
                    <span className={styles.popupExpertName}>{meta.label}</span>
                  </div>
                );
              })}
            </div>
            <div className={styles.popupFooter}>
              <div className="loading-dots"><span /><span /><span /></div>
              <span>Seating experts…</span>
            </div>
          </div>
        </div>
      )}

      {members.length > 0 && popupDone && (
        <div className={`${styles.tableWrap} glass animate-fade-slide-up`}>
          <RoundTable
            experts={members}
            stage="council"
            showJudge={true}
            judgeHighlighted={false}
          />
        </div>
      )}

      {members.length > 0 && isForming && popupDone && (
        <p className={styles.debateHint}>Experts are preparing their independent analyses…</p>
      )}
    </div>
  );
}
