/**
 * RoundTable.jsx
 * Circular round-table conference component.
 * Distributes experts radially, positions the Judge at the head,
 * and draws animated SVG path arrows to visualize debates & challenges.
 */
import { useMemo } from 'react';
import { getExpertMeta } from '../utils/experts';
import styles from './RoundTable.module.css';

export default function RoundTable({
  experts = [],
  activeSpeaker = null,
  activeText = null,
  challenges = [],
  activeChallengeIndex = null,
  showJudge = true,
  judgeHighlighted = false,
  stage = 'debate', // 'council' | 'debate' | 'judging'
}) {
  const tableCenter = { x: 50, y: 58 };
  const tableRadius = 30; // % radius of the round table

  // Compute expert polar coordinates mathematically for a horseshoe horseshoe arc
  const expertPositions = useMemo(() => {
    const N = experts.length;
    if (N === 0) return [];

    // Distribute experts in a clockwise sweep along the horseshoe sides and bottom,
    // leaving the top gap (where the Judge's table sits) empty.
    const startAngle = Math.PI * 1.1; // top-left (approx 10 o'clock)
    const endAngle = -Math.PI * 0.1;  // top-right (approx 2 o'clock)

    return experts.map((name, index) => {
      const angle = N === 1
        ? Math.PI / 2
        : startAngle - (index * (startAngle - endAngle)) / (N - 1);

      const x = tableCenter.x + tableRadius * Math.cos(angle);
      const y = tableCenter.y + tableRadius * Math.sin(angle);
      const meta = getExpertMeta(name);

      return {
        name,
        meta,
        x,
        y,
        angle,
      };
    });
  }, [experts, tableCenter.x, tableCenter.y, tableRadius]);

  // Map expert names to their coordinate position for fast lookup
  const positionsMap = useMemo(() => {
    const map = {};
    expertPositions.forEach((pos) => {
      map[pos.name.toLowerCase()] = pos;
    });
    map['the judge'] = { x: 50, y: 12 };
    return map;
  }, [expertPositions]);

  // Identify challenge lines to draw
  const activeChallenges = useMemo(() => {
    if (stage !== 'debate' || challenges.length === 0) return [];
    
    // If activeChallengeIndex is specified, draw only that one; otherwise draw all
    if (activeChallengeIndex !== null && activeChallengeIndex >= 0 && activeChallengeIndex < challenges.length) {
      return [challenges[activeChallengeIndex]];
    }
    return challenges;
  }, [challenges, activeChallengeIndex, stage]);

  const isJudgeSpeaking = activeSpeaker && activeSpeaker.toLowerCase() === 'the judge';
  const isClerkSpeaking = activeSpeaker && activeSpeaker.toLowerCase() === 'the clerk';

  return (
    <div className={styles.container}>
      {/* Central Round Table Disk */}
      <div
        className={`${styles.tableDisk} glass`}
        style={{
          width: `${tableRadius * 2}%`,
          height: `${tableRadius * 2}%`,
          left: `${tableCenter.x}%`,
          top: `${tableCenter.y}%`,
        }}
      >
        <div className={styles.tableInnerRing} />
        {stage === 'debate' && activeSpeaker && (
          <div className={styles.chamberPulse} />
        )}
      </div>

      {/* Holographic Processing Core (Subtle pulse without spinning dashed rings) */}
      {(stage === 'debate' || stage === 'judging') && (
        <div
          className={styles.hologramCore}
          style={{
            left: `${tableCenter.x}%`,
            top: `${tableCenter.y}%`,
          }}
        >
          <div className={styles.hologramPulse} />
        </div>
      )}

      {/* SVG Canvas for drawing challenges and relationships */}
      <svg className={styles.svgCanvas} viewBox="0 0 100 100" preserveAspectRatio="none">
        <defs>
          <linearGradient id="neonGlow" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#F5C842" stopOpacity="0.8" />
            <stop offset="100%" stopColor="#F87171" stopOpacity="0.8" />
          </linearGradient>
          {/* Arrow marker for challenges */}
          <marker
            id="arrow"
            viewBox="0 0 10 10"
            refX="22" // Offset so the arrow points at the edge of the expert node
            refY="5"
            markerWidth="5"
            markerHeight="5"
            orient="auto-start-reverse"
          >
            <path d="M 0 0 L 10 5 L 0 10 z" fill="#FBBF24" />
          </marker>
        </defs>

        {/* Draw active challenge connections */}
        {activeChallenges.map((ch, idx) => {
          const challenger = positionsMap[ch.expert_name?.toLowerCase()];
          const target = positionsMap[ch.targeted_expert?.toLowerCase() || ch.targeted_assumption?.toLowerCase() || ''];
          
          // Fallback if target is a generic string rather than matching an expert name
          const finalTarget = target || Object.values(positionsMap)[(idx + 1) % Object.keys(positionsMap).length];

          if (!challenger || !finalTarget) return null;

          // Q 50 58 bends the quadratic Bezier line toward the center of the table
          const pathD = `M ${challenger.x} ${challenger.y} Q ${tableCenter.x} ${tableCenter.y} ${finalTarget.x} ${finalTarget.y}`;

          return (
            <path
              key={idx}
              d={pathD}
              className={styles.challengePath}
              markerEnd="url(#arrow)"
            />
          );
        })}
      </svg>

      {/* Render Judge at the head of the chamber */}
      {showJudge && (
        <div
          className={`${styles.judgeNode} glass ${
            judgeHighlighted || stage === 'judging' ? styles.judgeActive : ''
          } ${isJudgeSpeaking ? styles.speaking : ''}`}
          style={{ left: '50%', top: '12%' }}
        >
          {isJudgeSpeaking && (
            <div
              className={styles.speakingAura}
              style={{ backgroundColor: 'var(--color-gold)' }}
            />
          )}
          <div className={styles.avatar}>🧑‍⚖️</div>
          <div className={styles.nodeLabel}>The Judge</div>

          {/* Thought Cloud for Judge */}
          {((isJudgeSpeaking && activeText) || (stage === 'judging' && activeText)) && (
            <div
              className={`${styles.speechBubble} ${styles.bubbleBelow}`}
              style={{ borderColor: 'var(--color-gold)', color: 'var(--color-gold)' }}
            >
              <div className={styles.speechText}>
                {activeText.length > 65 ? activeText.slice(0, 65) + '…' : activeText}
              </div>
              <div className={styles.speechPointer} />
            </div>
          )}
        </div>
      )}

      {/* Render Clerk beside Judge on the top right */}
      {showJudge && (
        <div
          className={`${styles.clerkNode} glass ${
            isClerkSpeaking ? styles.clerkActive : ''
          } ${isClerkSpeaking ? styles.speaking : ''}`}
          style={{ left: '71%', top: '15%' }}
        >
          {isClerkSpeaking && (
            <div
              className={styles.speakingAura}
              style={{ backgroundColor: '#0d9488' }}
            />
          )}
          <div className={styles.avatar}>📜</div>
          <div className={styles.nodeLabel}>The Clerk</div>

          {/* Thought Cloud for Clerk */}
          {isClerkSpeaking && activeText && (
            <div
              className={`${styles.speechBubble} ${styles.bubbleBelow}`}
              style={{ borderColor: '#0d9488', color: '#0d9488' }}
            >
              <div className={styles.speechText}>
                {activeText.length > 65 ? activeText.slice(0, 65) + '…' : activeText}
              </div>
              <div className={styles.speechPointer} />
            </div>
          )}
        </div>
      )}

      {/* Render distributed Expert Nodes */}
      {expertPositions.map((pos, idx) => {
        const isSpeaking = activeSpeaker && pos.name.toLowerCase() === activeSpeaker.toLowerCase();
        
        return (
          <div
            key={pos.name}
            className={`${styles.expertNode} glass ${
              isSpeaking ? styles.speaking : ''
            } animate-fade-in`}
            style={{
              left: `${pos.x}%`,
              top: `${pos.y}%`,
              borderColor: pos.meta.color,
              animationDelay: `${idx * 150}ms`,
            }}
          >
            {/* Pulsing indicator aura */}
            {isSpeaking && (
              <div
                className={styles.speakingAura}
                style={{ backgroundColor: pos.meta.color }}
              />
            )}
            
            <div className={styles.avatar}>{pos.meta.icon}</div>
            
            <div className={styles.nodeLabel}>
              <span className={styles.nodeName}>{pos.meta.label}</span>
              {stage === 'council' && (
                <span className={styles.readyIndicator}>✓</span>
              )}
            </div>

            {/* Thought Cloud Speech Bubble */}
            {isSpeaking && activeText && (
              <div
                className={`${styles.speechBubble} ${pos.y < 50 ? styles.bubbleBelow : styles.bubbleAbove}`}
                style={{ borderColor: pos.meta.color, color: pos.meta.color }}
              >
                <div className={styles.speechText}>
                  {activeText.length > 65 ? activeText.slice(0, 65) + '…' : activeText}
                </div>
                <div className={styles.speechPointer} />
              </div>
            )}
            
            {/* Tooltip on hover */}
            <div className={styles.tooltip}>
              <strong>{pos.name}</strong>
              <div style={{ color: pos.meta.color, fontSize: '0.8rem', marginTop: '2px' }}>
                Domain: {pos.meta.label}
              </div>
            </div>
          </div>
        );
      })}

      {/* Empty State / Joining placeholders (only in council mode) */}
      {stage === 'council' && experts.length < 4 && (
        <div className={styles.emptyTableOverlay}>
          <div className="loading-dots">
            <span />
            <span />
            <span />
          </div>
        </div>
      )}
    </div>
  );
}
