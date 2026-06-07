/**
 * Verdict.jsx — Final verdict screen.
 * Verdict badge, confidence ring, executive report, and full debate log.
 */
import { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import VerdictBadge from '../components/VerdictBadge';
import ConfidenceRing from '../components/ConfidenceRing';
import DebateCard from '../components/DebateCard';
import { getExpertMeta } from '../utils/experts';
import styles from './Verdict.module.css';

export default function Verdict({ caseData, stageData, onReset }) {
  const [debateOpen, setDebateOpen] = useState(false);
  const [telemetryOpen, setTelemetryOpen] = useState(false);

  const verdict     = caseData?.verdict;
  const confidence  = caseData?.confidence ?? 0;
  const report      = caseData?.executive_report ?? '';
  const query       = caseData?.query ?? '';
  const members     = stageData?.council_members ?? caseData?.council_members ?? [];
  const debate      = stageData?.debate;
  const consensus   = stageData?.consensus;
  const reputationUpdates = caseData?.full_result?.reputation_updates ?? stageData?.reputation_updates ?? [];

  return (
    <div className={styles.verdict}>
      {/* Verdict hero */}
      <div className={`${styles.hero} animate-fade-slide-up`}>
        <VerdictBadge verdict={verdict} />

        <div className={`${styles.ringWrap} animate-scale-in`} style={{ animationDelay: '300ms' }}>
          <ConfidenceRing confidence={confidence} />
        </div>
      </div>

      {/* Query recap */}
      <div className={`${styles.queryCard} glass animate-fade-slide-up`} style={{ animationDelay: '100ms' }}>
        <p className={styles.queryLabel}>Decision Query</p>
        <p className={styles.queryText}>{query}</p>
      </div>

      {/* Council members */}
      {members.length > 0 && (
        <div className={`${styles.councilRow} animate-fade-slide-up`} style={{ animationDelay: '150ms' }}>
          <p className={styles.sectionMeta}>Council</p>
          <div className={styles.memberChips}>
            {members.map(name => {
              const meta = getExpertMeta(name);
              return (
                <span key={name} className={styles.memberChip}>
                  {meta.icon} {name}
                </span>
              );
            })}
          </div>
        </div>
      )}

      {/* Executive report */}
      {report && (
        <div className={`${styles.reportCard} glass animate-fade-slide-up`} style={{ animationDelay: '200ms' }}>
          <h3 className={styles.reportTitle}>Executive Report</h3>
          <div className="markdown-body">
            <ReactMarkdown>{report}</ReactMarkdown>
          </div>
        </div>
      )}

      {/* Consensus reasoning */}
      {consensus?.reasoning && (
        <div className={`${styles.consensusCard} glass animate-fade-slide-up`} style={{ animationDelay: '250ms' }}>
          <h3 className={styles.reportTitle}>Consensus Reasoning</h3>
          <p className={styles.consensusText}>{consensus.reasoning}</p>
          {consensus.key_conditions?.length > 0 && (
            <div className={styles.conditionsList}>
              <p className={styles.conditionsLabel}>Key Conditions</p>
              {consensus.key_conditions.map((c, i) => (
                <div key={i} className={styles.condition}>
                  <span className={styles.conditionDot} />
                  <span>{c}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Full debate log toggle */}
      {debate && (
        <div className={`${styles.debateSection} animate-fade-slide-up`} style={{ animationDelay: '300ms' }}>
          <button
            id="toggle-debate-log"
            className={`${styles.toggleBtn} glass`}
            onClick={() => setDebateOpen(o => !o)}
          >
            <span>{debateOpen ? '▲' : '▼'}</span>
            {debateOpen ? 'Hide' : 'Show'} Full Debate Log
            <span className={styles.toggleCount}>
              {(debate.round1_analyses?.length ?? 0) +
               (debate.round2_challenges?.length ?? 0) +
               (debate.round3_rebuttals?.length ?? 0)} entries
            </span>
          </button>

          {debateOpen && (
            <div className={`${styles.debateLog} animate-fade-slide-up`}>
              {debate.round1_analyses?.map((a, i) => (
                <DebateCard key={`r1-${i}`} round={1} speakerName={a.expert_name} content={a.reasoning} animDelay={i * 60} />
              ))}
              {debate.round2_challenges?.map((c, i) => (
                <DebateCard key={`r2-${i}`} round={2} speakerName="The Judge" content={c.challenge} targetName={c.expert_name} animDelay={i * 60} />
              ))}
              {debate.round3_rebuttals?.map((r, i) => (
                <DebateCard key={`r3-${i}`} round={3} speakerName={r.expert_name} content={r.rebuttal} animDelay={i * 60} />
              ))}
            </div>
          )}
        </div>
      )}

      {/* Telemetry section */}
      {reputationUpdates && reputationUpdates.length > 0 && (
        <div className={`${styles.telemetrySection} animate-fade-slide-up`} style={{ animationDelay: '325ms' }}>
          <button
            id="toggle-telemetry-log"
            className={`${styles.toggleBtn} glass`}
            onClick={() => setTelemetryOpen(o => !o)}
          >
            <span>{telemetryOpen ? '▲' : '▼'}</span>
            ⚙️ System Telemetry & Reputation Engine Audit
            <span className={styles.toggleCount}>
              {reputationUpdates.length} agents
            </span>
          </button>

          {telemetryOpen && (
            <div className={`${styles.telemetryContainer} glass animate-fade-slide-up`}>
              <p className={styles.telemetryDisclaimer}>
                <strong>Internal Telemetry:</strong> This section displays real-time agent ratings, quality, calibration, and impact metrics. These are calculated by the Reputation Engine to dynamically adjust ELO-based reputations (bounds: 700 - 1300 ELO). In production, this data is kept internal/hidden from end-users.
              </p>

              <div className={styles.expertGrid}>
                {reputationUpdates.map((update, idx) => {
                  const meta = getExpertMeta(update.expert_name);
                  const isPositive = update.change_amount >= 0;
                  const formattedDelta = isPositive ? `+${update.change_amount}` : `${update.change_amount}`;
                  
                  return (
                    <div key={idx} className={styles.expertTelemetryCard} style={{ '--accent-color': meta.color }}>
                      <div className={styles.expertTelemetryHeader}>
                        <div className={styles.expertNameBlock}>
                          <span className={styles.expertIcon}>{meta.icon}</span>
                          <div>
                            <h4 className={styles.expertNameText}>{update.expert_name}</h4>
                            <span className={styles.expertRoleTag} style={{ borderColor: meta.color, color: meta.color }}>
                              {meta.label}
                            </span>
                          </div>
                        </div>
                        <div className={styles.eloScoreBlock}>
                          <div className={styles.eloRange}>
                            <span className={styles.eloLabel}>Rating</span>
                            <span className={styles.eloValue}>{update.reputation_after} ELO</span>
                          </div>
                          <span className={`${styles.eloDelta} ${isPositive ? styles.positive : styles.negative}`}>
                            {formattedDelta}
                          </span>
                        </div>
                      </div>

                      <div className={styles.metricsGrid}>
                        <div className={styles.metricItem}>
                          <div className={styles.metricHeader}>
                            <span className={styles.metricLabel}>Quality (50%)</span>
                            <span className={styles.metricValue}>{update.quality_score}</span>
                          </div>
                          <div className={styles.progressBarBg}>
                            <div className={styles.progressBarFill} style={{ width: `${update.quality_score}%`, backgroundColor: 'var(--color-indigo)' }} />
                          </div>
                        </div>

                        <div className={styles.metricItem}>
                          <div className={styles.metricHeader}>
                            <span className={styles.metricLabel}>Impact (30%)</span>
                            <span className={styles.metricValue}>{update.impact_score}</span>
                          </div>
                          <div className={styles.progressBarBg}>
                            <div className={styles.progressBarFill} style={{ width: `${update.impact_score}%`, backgroundColor: 'var(--color-amber)' }} />
                          </div>
                        </div>

                        <div className={styles.metricItem}>
                          <div className={styles.metricHeader}>
                            <span className={styles.metricLabel}>Calibration (20%)</span>
                            <span className={styles.metricValue}>{update.calibration_score}</span>
                          </div>
                          <div className={styles.progressBarBg}>
                            <div className={styles.progressBarFill} style={{ width: `${update.calibration_score}%`, backgroundColor: 'var(--color-green)' }} />
                          </div>
                        </div>
                      </div>

                      <div className={styles.contributionFooter}>
                        <span className={styles.contributionLabel}>Contribution Score</span>
                        <span className={styles.contributionValue} style={{ color: meta.color }}>
                          {update.contribution_score} / 100
                        </span>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      )}

      {/* CTA */}
      <div className={`${styles.cta} animate-fade-slide-up`} style={{ animationDelay: '350ms' }}>
        <button id="new-decision-btn" className="btn btn-primary" onClick={onReset}>
          ⚡ New Decision
        </button>
      </div>
    </div>
  );
}
