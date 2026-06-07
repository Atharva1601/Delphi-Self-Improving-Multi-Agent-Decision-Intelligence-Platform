import { useState, useEffect } from 'react';
import DebateCard from '../components/DebateCard';
import RoundTable from '../components/RoundTable';
import styles from './Debate.module.css';

const TABS = [
  { id: 'r1', label: '① Analysis',   round: 1 },
  { id: 'r2', label: '② Challenges', round: 2 },
  { id: 'r3', label: '③ Defense',    round: 3 },
];

export default function Debate({ stageData, status }) {
  const [activeTab, setActiveTab] = useState('r1');
  const [activeIndex, setActiveIndex] = useState(0);
  const debate = stageData?.debate;
  const isDebating = status === 'debate';

  const round1 = debate?.round1_analyses    ?? [];
  const round2 = debate?.round2_challenges  ?? [];
  const round3 = debate?.round3_rebuttals   ?? [];

  const [showBanner, setShowBanner] = useState(false);
  const [bannerDone, setBannerDone] = useState(false);

  // Trigger "Debate Started" banner popup
  useEffect(() => {
    if (isDebating && !bannerDone) {
      setShowBanner(true);
      const t = setTimeout(() => {
        setShowBanner(false);
        setBannerDone(true);
      }, 2200);
      return () => clearTimeout(t);
    }
  }, [isDebating, bannerDone]);

  // Reset active card index when tab changes
  useEffect(() => {
    setActiveIndex(0);
  }, [activeTab]);

  const experts = stageData?.council_members ?? [];

  const cards = {
    r1: round1.map(a => ({ speaker: a.expert_name,  content: a.reasoning, round: 1 })),
    r2: round2.map(c => ({ speaker: 'The Judge',     content: c.challenge, round: 2, target: c.expert_name })),
    r3: round3.map(r => ({ speaker: r.expert_name,   content: r.rebuttal,  round: 3 })),
  };

  const hasData = round1.length > 0;
  const activeCard = cards[activeTab]?.[activeIndex];

  // Auto-cycle through cards dynamically so the user sees the debate flow
  useEffect(() => {
    if (!hasData || showBanner) return;
    const currentCards = cards[activeTab] || [];
    if (currentCards.length === 0) return;

    const interval = setInterval(() => {
      setActiveIndex(prev => {
        if (prev < currentCards.length - 1) {
          return prev + 1;
        } else {
          // If we reached the end of the round, advance to next tab
          setActiveTab(currTab => {
            if (currTab === 'r1') return 'r2';
            if (currTab === 'r2') return 'r3';
            return 'r1';
          });
          return 0;
        }
      });
    }, 2500); // 2.5s per speaking agent

    return () => clearInterval(interval);
  }, [hasData, activeTab, round1.length, round2.length, round3.length, showBanner]);

  // Thinking state animations
  const [waitingIndex, setWaitingIndex] = useState(0);
  useEffect(() => {
    if (hasData || !isDebating) return;
    const interval = setInterval(() => {
      setWaitingIndex(prev => (prev + 1) % (experts.length || 4));
    }, 2000);
    return () => clearInterval(interval);
  }, [hasData, isDebating, experts.length]);

  const getThinkingText = (expertName) => {
    const lower = expertName.toLowerCase();
    if (lower.includes('technical') || lower.includes('architect')) {
      return "Analyzing technical integration feasibility and API latency boundaries...";
    }
    if (lower.includes('legal') || lower.includes('compliance')) {
      return "Evaluating regulatory compliance posture and liability exposure guidelines...";
    }
    if (lower.includes('security') || lower.includes('cyber')) {
      return "Auditing cybersecurity threat vectors and data privacy safeguards...";
    }
    if (lower.includes('operations') || lower.includes('process')) {
      return "Auditing operational capacity and workflow disruption constraints...";
    }
    if (lower.includes('finance') || lower.includes('economic')) {
      return "Modeling CapEx requirements, runway impact, and ROI projections...";
    }
    if (lower.includes('product') || lower.includes('strategy')) {
      return "Evaluating competitive positioning, user adoption friction, and roadmap fit...";
    }
    if (lower.includes('business') || lower.includes('market')) {
      return "Evaluating market sizing, competitor strength, and revenue potential...";
    }
    return "Deliberating and compiling initial analysis for the council...";
  };

  // Dynamic parameters for the RoundTable
  let activeSpeaker = null;
  let activeText = null;
  let challenges = [];
  let judgeHighlighted = false;

  if (hasData) {
    if (activeCard) {
      activeSpeaker = activeCard.speaker;
      activeText = activeCard.content;
      if (activeTab === 'r2') {
        judgeHighlighted = true;
        challenges = [{
          expert_name: 'The Judge',
          targeted_expert: activeCard.target
        }];
      }
    }
  } else {
    // Waiting/deliberating state: keep agents silent (no text/speech bubbles)
    activeSpeaker = null;
    activeText = null;
  }

  return (
    <div className={styles.debate}>
      <div className={styles.header}>
        <div className={`${styles.statusDot} ${isDebating ? styles.pulsing : ''}`} />
        <h2 className={styles.title}>
          {isDebating ? 'Debate in Progress…' : 'Debate Complete'}
        </h2>
      </div>

      {/* Debate Started banner popup overlay */}
      {showBanner && (
        <div className={styles.bannerOverlay}>
          <div className={`${styles.bannerCard} glass-strong animate-scale-in`}>
            <div className={styles.bannerSubtitle}>STAGE 3</div>
            <h1 className={styles.bannerTitle}>Adversarial Debate Started</h1>
            <p className={styles.bannerHint}>Experts challenge proposals and defend domain priorities</p>
          </div>
        </div>
      )}

      {/* Always render RoundTable if experts list has loaded */}
      {experts.length > 0 && (
        <div className={`${styles.tableWrap} glass animate-fade-slide-up`}>
          <RoundTable
            experts={experts}
            activeSpeaker={activeSpeaker}
            activeText={activeText}
            challenges={challenges}
            activeChallengeIndex={0}
            showJudge={true}
            judgeHighlighted={judgeHighlighted}
            stage="debate"
          />
        </div>
      )}

      {!hasData && isDebating && (
        <div className={`${styles.waiting} animate-fade-in`}>
          <div className="loading-dots"><span /><span /><span /></div>
          <p>Expert council is deliberating independently…</p>
          <p className={styles.subWait}>3 rounds · parallel analysis · adversarial challenges</p>
        </div>
      )}

    </div>
  );
}

