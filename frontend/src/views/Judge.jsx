import { useEffect, useState } from 'react';
import { animateValue } from '../utils/formatters';
import { getExpertMeta } from '../utils/experts';
import RoundTable from '../components/RoundTable';
import styles from './Judge.module.css';

function ScoreBar({ label, value, maxValue = 10, color = 'var(--color-indigo)', delay = 0 }) {
  const [width, setWidth] = useState(0);
  const [displayed, setDisplayed] = useState(0);
  const pct = (value / maxValue) * 100;

  useEffect(() => {
    const t = setTimeout(() => {
      setWidth(pct);
      animateValue(setDisplayed, 0, value, 900);
    }, delay);
    return () => clearTimeout(t);
  }, [value, pct, delay]);

  return (
    <div className={styles.barRow}>
      <div className={styles.barLabel}>
        <span>{label}</span>
        <span className={styles.barValue} style={{ color }}>{displayed.toFixed(1)}</span>
      </div>
      <div className={styles.barTrack}>
        <div
          className={styles.barFill}
          style={{ width: `${width}%`, background: color, transition: `width 0.9s var(--ease-out-expo) ${delay}ms` }}
        />
      </div>
    </div>
  );
}

export default function Judge({ stageData, status }) {
  const rubric = stageData?.judge_rubric;
  const isJudging = status === 'judging';

  const expertScores = rubric?.expert_scores ?? [];
  const experts = expertScores.map(e => e.expert_name);

  const [hoverExpert, setHoverExpert] = useState(null);
  const [cycleStep, setCycleStep] = useState(0);

  // Cycle general judge commentary when not hovering over an expert
  useEffect(() => {
    if (!rubric) return;
    const interval = setInterval(() => {
      setCycleStep(prev => (prev + 1) % 3);
    }, 4500);
    return () => clearInterval(interval);
  }, [rubric]);

  let judgeComment = "Let us evaluate the council's debate performance.";
  if (rubric) {
    if (hoverExpert) {
      const scoreObj = expertScores.find(e => e.expert_name === hoverExpert);
      if (scoreObj && scoreObj.feedback) {
        judgeComment = `Regarding ${hoverExpert}: "${scoreObj.feedback}"`;
      }
    } else {
      if (cycleStep === 0) {
        judgeComment = `Auditing evidence quality (avg ${rubric.avg_evidence_quality?.toFixed(1) ?? '8.0'}/10) and logical consistency.`;
      } else if (cycleStep === 1 && rubric.strongest_argument) {
        judgeComment = `Strongest Point: "${rubric.strongest_argument}"`;
      } else if (cycleStep === 2 && rubric.weakest_argument) {
        judgeComment = `Weakest Point: "${rubric.weakest_argument}"`;
      }
    }
  }

  const METRICS = rubric ? [
    { label: 'Evidence Quality',    value: rubric.avg_evidence_quality   ?? 0, color: 'var(--color-indigo)' },
    { label: 'Logical Consistency', value: rubric.avg_logic_score        ?? 0, color: 'var(--color-gold)' },
    { label: 'Argument Depth',      value: rubric.avg_consistency_score  ?? 0, color: 'var(--color-green)' },
    { label: 'Rebuttal Quality',    value: rubric.avg_rebuttal_quality   ?? 0, color: '#F472B6' },
  ] : [];

  const overallScore = rubric?.overall_quality_score ?? rubric?.overall_score ?? null;

  return (
    <div className={styles.judge}>
      <div className={styles.header}>
        <div className={`${styles.statusDot} ${isJudging ? styles.pulsing : ''}`} />
        <h2 className={styles.title}>
          {isJudging ? 'The Judge is Evaluating…' : 'Evaluation Complete'}
        </h2>
      </div>

      {!rubric && isJudging && (
        <div className={`${styles.waiting} animate-fade-in`}>
          <div className="loading-dots"><span /><span /><span /></div>
          <p>Scoring evidence, logic, and rebuttal quality…</p>
        </div>
      )}

      {rubric && (
        <>
          <div className={`${styles.roundTableWrap} glass animate-fade-slide-up`}>
            <RoundTable
              experts={experts}
              activeSpeaker="The Judge"
              activeText={judgeComment}
              stage="judging"
              showJudge={true}
              judgeHighlighted={true}
            />
          </div>

          {/* Overall score */}
          {overallScore != null && (
            <div className={`${styles.overallCard} glass-strong animate-scale-in`}>
              <p className={styles.overallLabel}>Overall Quality Score</p>
              <OverallCounter value={overallScore} />
            </div>
          )}

          {/* Rubric bars */}
          <div className={`${styles.rubricCard} glass animate-fade-slide-up`}>
            <h3 className={styles.sectionTitle}>Rubric Breakdown</h3>
            <div className={styles.bars}>
              {METRICS.map((m, i) => (
                <ScoreBar key={m.label} {...m} delay={i * 150} />
              ))}
            </div>
          </div>

          {/* Per-expert table */}
          {expertScores.length > 0 && (
            <div className={`${styles.tableCard} glass animate-fade-slide-up`} style={{ animationDelay: '200ms' }}>
              <h3 className={styles.sectionTitle}>Per-Expert Scores (Hover for Judge's feedback)</h3>
              <div className={styles.tableWrap}>
                <table className={styles.table}>
                  <thead>
                    <tr>
                      <th>Expert</th>
                      <th>Evidence</th>
                      <th>Logic</th>
                      <th>Depth</th>
                      <th>Rebuttal</th>
                    </tr>
                  </thead>
                  <tbody>
                    {expertScores.map(e => {
                      const meta = getExpertMeta(e.expert_name);
                      return (
                        <tr
                          key={e.expert_name}
                          onMouseEnter={() => setHoverExpert(e.expert_name)}
                          onMouseLeave={() => setHoverExpert(null)}
                          className={styles.tableRowHover}
                        >
                          <td>
                            <div className={styles.expertCell}>
                              <span style={{ fontSize: '1rem' }}>{meta.icon}</span>
                              <span className={styles.expertName}>{e.expert_name}</span>
                            </div>
                          </td>
                          <td><ScoreCell value={e.evidence_quality} /></td>
                          <td><ScoreCell value={e.logic_score} /></td>
                          <td><ScoreCell value={e.consistency_score} /></td>
                          <td><ScoreCell value={e.rebuttal_quality} /></td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}

function OverallCounter({ value }) {
  const [displayed, setDisplayed] = useState(0);
  useEffect(() => { animateValue(setDisplayed, 0, value, 1200); }, [value]);

  const color = displayed >= 7 ? 'var(--color-green)' : displayed >= 4 ? 'var(--color-gold)' : 'var(--color-red)';

  return (
    <div className={styles.overallValue} style={{ color }}>
      {displayed.toFixed(1)}
      <span className={styles.overallMax}> / 10</span>
    </div>
  );
}

function ScoreCell({ value }) {
  if (value == null) return <span style={{ color: 'var(--color-text-muted)' }}>—</span>;
  const color =
    value >= 7 ? 'var(--color-green)' :
    value >= 4 ? 'var(--color-gold)'  :
                 'var(--color-red)';
  return <span className={styles.scoreCell} style={{ color }}>{Number(value).toFixed(1)}</span>;
}
