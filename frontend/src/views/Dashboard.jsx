import { useState, useEffect } from 'react';
import { getLeaderboard, getMemoryBank, getTimeline, getExpertDetail } from '../api/client';
import SvgTimelineChart from '../components/SvgTimelineChart';
import styles from './Dashboard.module.css';

export default function Dashboard({ onBack }) {
  const [activeTab, setActiveTab] = useState('leaderboard'); // 'leaderboard' | 'memory-bank' | 'timeline' | 'expert-detail'
  const [leaderboard, setLeaderboard] = useState([]);
  const [memoryBank, setMemoryBank] = useState({ reflections: [], success_patterns: [] });
  const [timeline, setTimeline] = useState([]);
  const [selectedExpertId, setSelectedExpertId] = useState(null);
  const [expertDetail, setExpertDetail] = useState(null);
  
  const [loading, setLoading] = useState(true);
  const [detailLoading, setDetailLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [bankSubTab, setBankSubTab] = useState('reflections'); // 'reflections' | 'success-patterns'

  // Load initial global dashboard data
  useEffect(() => {
    setLoading(true);
    Promise.all([getLeaderboard(), getMemoryBank(), getTimeline()])
      .then(([lb, mb, tl]) => {
        setLeaderboard(lb);
        setMemoryBank(mb);
        setTimeline(tl);
        if (lb.length > 0) {
          setSelectedExpertId(lb[0].id);
        }
      })
      .catch((err) => console.error("Error loading dashboard data:", err))
      .finally(() => setLoading(false));
  }, []);

  // Load detailed analytics for selected expert
  useEffect(() => {
    if (!selectedExpertId) return;
    setDetailLoading(true);
    getExpertDetail(selectedExpertId)
      .then(setExpertDetail)
      .catch((err) => console.error("Error loading expert detail:", err))
      .finally(() => setDetailLoading(false));
  }, [selectedExpertId]);

  // Derived stats
  const totalCasesCount = leaderboard.length > 0 ? Math.max(...leaderboard.map(e => e.case_count)) : 0;
  const avgCouncilElo = leaderboard.length > 0 ? Math.round(leaderboard.reduce((acc, e) => acc + e.reputation_score, 0) / leaderboard.length) : 1000;
  const numReflections = memoryBank.reflections.length;
  const numSuccessPatterns = memoryBank.success_patterns.length;
  
  // Calculate experts in recovery mode (average score < 70.0 over past cases, but let's approximate based on ELO or count actual recovery entries)
  // Let's check how many experts have avg_contribution < 70 in the leaderboard
  const expertsInRecoveryCount = leaderboard.filter(e => e.avg_contribution !== null && e.avg_contribution < 70.0).length;

  const handleExpertSelectFromLeaderboard = (id) => {
    setSelectedExpertId(id);
    setActiveTab('expert-detail');
  };

  // Filter memory bank search query
  const filteredReflections = memoryBank.reflections.filter(r => 
    r.expert_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    r.domain.toLowerCase().includes(searchQuery.toLowerCase()) ||
    r.failure_type.toLowerCase().includes(searchQuery.toLowerCase()) ||
    r.lesson.toLowerCase().includes(searchQuery.toLowerCase()) ||
    r.case_query.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const filteredSuccessPatterns = memoryBank.success_patterns.filter(s => 
    s.expert_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    s.domain.toLowerCase().includes(searchQuery.toLowerCase()) ||
    s.success_pattern.toLowerCase().includes(searchQuery.toLowerCase()) ||
    s.case_query.toLowerCase().includes(searchQuery.toLowerCase())
  );

  if (loading) {
    return (
      <div className={styles.loadingScreen}>
        <div className={styles.spinner} />
        <p>Loading Delphi Observability Metrics…</p>
      </div>
    );
  }

  return (
    <div className={styles.dashboard}>
      {/* Header Toolbar */}
      <header className={styles.header}>
        <div className={styles.brand} onClick={onBack}>
          <span className={styles.backArrow}>←</span>
          <span className={styles.logoIcon}>⚖</span>
          <span className={styles.logoText}>DELPHI</span>
          <span className={styles.badge}>Observability Hub</span>
        </div>
        <button className={`btn btn-secondary ${styles.backBtn}`} onClick={onBack}>
          Return to Decision Chamber
        </button>
      </header>

      {/* Summary Analytics Strip */}
      <section className={styles.statsStrip}>
        <div className={`${styles.statCard} glass`}>
          <span className={styles.statLabel}>Total Case Cycles</span>
          <span className={styles.statVal}>{totalCasesCount}</span>
        </div>
        <div className={`${styles.statCard} glass`}>
          <span className={styles.statLabel}>Average Council ELO</span>
          <span className={styles.statVal}>{avgCouncilElo}</span>
        </div>
        <div className={`${styles.statCard} glass`}>
          <span className={styles.statLabel}>Failure Reflections</span>
          <span className={styles.statVal} style={{ color: 'var(--color-text)' }}>{numReflections}</span>
        </div>
        <div className={`${styles.statCard} glass`}>
          <span className={styles.statLabel}>Success Patterns</span>
          <span className={styles.statVal} style={{ color: 'var(--color-indigo)' }}>{numSuccessPatterns}</span>
        </div>
        <div className={`${styles.statCard} glass`}>
          <span className={styles.statLabel}>Active Recovery Mode</span>
          <span className={styles.statVal} style={{ color: expertsInRecoveryCount > 0 ? 'var(--color-red)' : 'var(--color-green)' }}>
            {expertsInRecoveryCount}
          </span>
        </div>
      </section>

      {/* Navigation Tabs */}
      <nav className={styles.tabs}>
        <button 
          className={`${styles.tab} ${activeTab === 'leaderboard' ? styles.tabActive : ''}`} 
          onClick={() => setActiveTab('leaderboard')}
        >
          🏆 Council Leaderboard
        </button>
        <button 
          className={`${styles.tab} ${activeTab === 'memory-bank' ? styles.tabActive : ''}`} 
          onClick={() => setActiveTab('memory-bank')}
        >
          📜 Memory Lessons Bank
        </button>
        <button 
          className={`${styles.tab} ${activeTab === 'timeline' ? styles.tabActive : ''}`} 
          onClick={() => setActiveTab('timeline')}
        >
          📈 ELO Timeline Feed
        </button>
        <button 
          className={`${styles.tab} ${activeTab === 'expert-detail' ? styles.tabActive : ''}`} 
          onClick={() => setActiveTab('expert-detail')}
        >
          👤 Expert Detailed Analytics
        </button>
      </nav>

      {/* Active Tab Panel */}
      <main className={styles.panel}>
        
        {/* LEADERBOARD TAB */}
        {activeTab === 'leaderboard' && (
          <div className={`${styles.card} glass-strong animate-fade-slide-up`}>
            <div className={styles.cardHeader}>
              <h2 className={styles.cardTitle}>Expert Council Standings</h2>
              <span className={styles.cardSub}>Sorted by current ELO-inspired reputation rating.</span>
            </div>
            <div className={styles.tableWrapper}>
              <table className={styles.table}>
                <thead>
                  <tr>
                    <th>Rank</th>
                    <th>Expert Agent</th>
                    <th>Domain</th>
                    <th>Current Rating</th>
                    <th>Last Delta</th>
                    <th>Participations</th>
                    <th>Avg Contribution</th>
                    <th>Status</th>
                    <th>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {leaderboard.map((expert, index) => {
                    const isPositive = expert.elo_delta_last_case > 0;
                    const isNegative = expert.elo_delta_last_case < 0;
                    const isRecovery = expert.avg_contribution !== null && expert.avg_contribution < 70.0;
                    
                    return (
                      <tr key={expert.id} className={styles.tableRow}>
                        <td className={styles.rankCol}>
                          {index === 0 ? '🥇' : index === 1 ? '🥈' : index === 2 ? '🥉' : `${index + 1}`}
                        </td>
                        <td className={styles.nameCol}>
                          <strong>{expert.name}</strong>
                          <p className={styles.descriptionText}>{expert.description}</p>
                        </td>
                        <td>
                          <span className={styles.domainTag}>{expert.domain}</span>
                        </td>
                        <td className={styles.eloText}>{expert.reputation_score.toFixed(1)} ELO</td>
                        <td className={isPositive ? styles.positiveDelta : isNegative ? styles.negativeDelta : styles.neutralDelta}>
                          {expert.elo_delta_last_case !== null ? (
                            <>
                              {isPositive ? '+' : ''}
                              {expert.elo_delta_last_case.toFixed(2)}
                            </>
                          ) : '—'}
                        </td>
                        <td className={styles.casesCol}>{expert.case_count} cases</td>
                        <td className={styles.scoreCol}>
                          {expert.avg_contribution !== null ? (
                            <span className={isRecovery ? styles.recoveryText : ''}>
                              {expert.avg_contribution.toFixed(1)}%
                            </span>
                          ) : '—'}
                        </td>
                        <td>
                          {isRecovery ? (
                            <span className={styles.statusBadgeRecovery}>Recovery</span>
                          ) : (
                            <span className={styles.statusBadgeActive}>Optimal</span>
                          )}
                        </td>
                        <td>
                          <button 
                            className={styles.rowActionBtn}
                            onClick={() => handleExpertSelectFromLeaderboard(expert.id)}
                          >
                            Analyze →
                          </button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* MEMORY BANK TAB */}
        {activeTab === 'memory-bank' && (
          <div className={`${styles.card} glass-strong animate-fade-slide-up`}>
            <div className={styles.bankHeader}>
              <div className={styles.bankToggles}>
                <button 
                  className={`${styles.bankToggle} ${bankSubTab === 'reflections' ? styles.bankToggleActive : ''}`}
                  onClick={() => setBankSubTab('reflections')}
                >
                  Failure Pitfalls & Lessons ({filteredReflections.length})
                </button>
                <button 
                  className={`${styles.bankToggle} ${bankSubTab === 'success-patterns' ? styles.bankToggleActive : ''}`}
                  onClick={() => setBankSubTab('success-patterns')}
                >
                  Success Patterns ({filteredSuccessPatterns.length})
                </button>
              </div>
              <input
                type="text"
                placeholder="Search lessons, expert names, or case queries..."
                className={styles.searchInput}
                value={searchQuery}
                onChange={e => setSearchQuery(e.target.value)}
              />
            </div>

            {/* List render */}
            <div className={styles.bankList}>
              {bankSubTab === 'reflections' ? (
                filteredReflections.length > 0 ? (
                  filteredReflections.map(ref => (
                    <div key={ref.id} className={`${styles.bankItem} glass`}>
                      <div className={styles.bankItemMeta}>
                        <span className={styles.itemExpert}>{ref.expert_name}</span>
                        <span className={styles.itemDomain}>{ref.domain}</span>
                        <span className={styles.itemType}>{ref.failure_type}</span>
                        <span className={styles.itemDate}>{new Date(ref.created_at).toLocaleDateString()}</span>
                      </div>
                      <div className={styles.bankItemQuery}>
                        <strong>Query:</strong> {ref.case_query}
                      </div>
                      <div className={styles.bankItemContent}>
                        <strong>Lesson Learned:</strong> {ref.lesson}
                      </div>
                    </div>
                  ))
                ) : (
                  <p className={styles.emptyText}>No matching failure reflections found.</p>
                )
              ) : (
                filteredSuccessPatterns.length > 0 ? (
                  filteredSuccessPatterns.map(sp => (
                    <div key={sp.id} className={`${styles.bankItem} glass`}>
                      <div className={styles.bankItemMeta}>
                        <span className={styles.itemExpert}>{sp.expert_name}</span>
                        <span className={styles.itemDomain} style={{ backgroundColor: 'rgba(108, 99, 255, 0.15)' }}>{sp.domain}</span>
                        <span className={styles.itemDate}>{new Date(sp.created_at).toLocaleDateString()}</span>
                      </div>
                      <div className={styles.bankItemQuery}>
                        <strong>Query:</strong> {sp.case_query}
                      </div>
                      <div className={styles.bankItemContent} style={{ borderLeftColor: 'var(--color-indigo)' }}>
                        <strong>Success Pattern:</strong> {sp.success_pattern}
                      </div>
                    </div>
                  ))
                ) : (
                  <p className={styles.emptyText}>No matching success patterns found.</p>
                )
              )}
            </div>
          </div>
        )}

        {/* ELO TIMELINE FEED TAB */}
        {activeTab === 'timeline' && (
          <div className={`${styles.card} glass-strong animate-fade-slide-up`}>
            <div className={styles.cardHeader}>
              <h2 className={styles.cardTitle}>ELO Score Adjustments Timeline</h2>
              <span className={styles.cardSub}>Audit feed of ELO-inspired reputation shifts across recent cases.</span>
            </div>
            <div className={styles.timelineList}>
              {timeline.length > 0 ? (
                timeline.map((item) => {
                  const isPositive = item.change_amount > 0;
                  const isNegative = item.change_amount < 0;
                  return (
                    <div key={item.id} className={`${styles.timelineItem} glass`}>
                      <div className={styles.timelineDeltaBox} style={{
                        borderColor: isPositive ? 'var(--color-green)' : isNegative ? 'var(--color-red)' : '#fff'
                      }}>
                        <span className={isPositive ? styles.timelinePlus : isNegative ? styles.timelineMinus : ''}>
                          {isPositive ? '+' : ''}{item.change_amount.toFixed(2)}
                        </span>
                      </div>
                      <div className={styles.timelineItemContent}>
                        <div className={styles.timelineRow}>
                          <strong className={styles.timelineName}>{item.expert_name}</strong>
                          <span className={styles.timelineDomain}>{item.domain}</span>
                          <span className={styles.timelineTime}>{new Date(item.created_at).toLocaleString()}</span>
                        </div>
                        <p className={styles.timelineQuery}>Case Query: "{item.case_query}"</p>
                        <div className={styles.timelinePath}>
                          <span>ELO Before: {item.reputation_before.toFixed(1)}</span>
                          <span className={styles.timelinePathArrow}>→</span>
                          <strong>ELO After: {item.reputation_after.toFixed(1)}</strong>
                        </div>
                      </div>
                    </div>
                  );
                })
              ) : (
                <p className={styles.emptyText}>No reputation history updates logged yet.</p>
              )}
            </div>
          </div>
        )}

        {/* EXPERT DETAILED ANALYTICS TAB */}
        {activeTab === 'expert-detail' && (
          <div className={styles.detailContainer}>
            {/* Left sidebar: Expert selector */}
            <div className={`${styles.detailSidebar} glass-strong`}>
              <h3 className={styles.sidebarTitle}>Select Expert</h3>
              <div className={styles.sidebarList}>
                {leaderboard.map(e => (
                  <button 
                    key={e.id}
                    className={`${styles.sidebarItem} ${selectedExpertId === e.id ? styles.sidebarItemActive : ''}`}
                    onClick={() => setSelectedExpertId(e.id)}
                  >
                    <span>{e.name}</span>
                    <span className={styles.sidebarElo}>{e.reputation_score.toFixed(0)}</span>
                  </button>
                ))}
              </div>
            </div>

            {/* Right workspace: Detailed Analytics */}
            <div className={styles.detailWorkspace}>
              {detailLoading ? (
                <div className={styles.detailLoader}>
                  <div className={styles.spinner} />
                  <p>Fetching detailed expert metrics…</p>
                </div>
              ) : expertDetail ? (
                <div className={styles.workspaceGrid}>
                  {/* Expert Profile & Current ELO */}
                  <div className={`${styles.profileCard} glass`}>
                    <div className={styles.profileRow}>
                      <div>
                        <h2 className={styles.profileName}>{expertDetail.name}</h2>
                        <span className={styles.profileDomain}>{expertDetail.domain}</span>
                      </div>
                      <div className={styles.profileEloContainer}>
                        <span className={styles.profileEloLabel}>ELO RATING</span>
                        <span className={styles.profileEloVal}>{expertDetail.reputation_score.toFixed(1)}</span>
                      </div>
                    </div>
                    <p className={styles.profileDesc}>{expertDetail.description}</p>
                    
                    {/* Performance Averages */}
                    <div className={styles.profileScores}>
                      <div className={styles.scoreBubble}>
                        <span className={styles.scoreVal}>{expertDetail.avg_quality_score ?? '—'}%</span>
                        <span className={styles.scoreLabel}>Quality</span>
                      </div>
                      <div className={styles.scoreBubble}>
                        <span className={styles.scoreVal}>{expertDetail.avg_impact_score ?? '—'}%</span>
                        <span className={styles.scoreLabel}>Impact</span>
                      </div>
                      <div className={styles.scoreBubble}>
                        <span className={styles.scoreVal}>{expertDetail.avg_calibration_score ?? '—'}%</span>
                        <span className={styles.scoreLabel}>Calibration</span>
                      </div>
                      <div className={styles.scoreBubble}>
                        <span className={styles.scoreVal} style={{ color: 'var(--color-indigo)', fontWeight: 'bold' }}>
                          {expertDetail.avg_contribution_score ?? '—'}%
                        </span>
                        <span className={styles.scoreLabel}>Contribution</span>
                      </div>
                    </div>
                  </div>

                  {/* Failure Type Distribution Card */}
                  <div className={`${styles.failureCard} glass`}>
                    <h3 className={styles.cardHeaderSmall}>Failure Reflections Breakdown</h3>
                    <div className={styles.failureDistributionList}>
                      {Object.keys(expertDetail.failure_distribution).length > 0 ? (
                        Object.entries(expertDetail.failure_distribution).map(([type, count]) => {
                          const totalFailures = Object.values(expertDetail.failure_distribution).reduce((a, b) => a + b, 0);
                          const percentage = (count / totalFailures) * 100;
                          return (
                            <div key={type} className={styles.distRow}>
                              <div className={styles.distLabels}>
                                <span className={styles.distType}>{type}</span>
                                <span className={styles.distCount}>{count} occurrences</span>
                              </div>
                              <div className={styles.distBarBg}>
                                <div 
                                  className={styles.distBarFill} 
                                  style={{ width: `${percentage}%` }}
                                />
                              </div>
                            </div>
                          );
                        })
                      ) : (
                        <div className={styles.distEmpty}>
                          🎉 No failure reflections recorded for this expert!
                        </div>
                      )}
                    </div>
                  </div>

                  {/* ELO Rating Timeline Curve (using custom SvgTimelineChart) */}
                  <div className={`${styles.chartCard} glass`}>
                    <h3 className={styles.cardHeaderSmall}>Reputation score (ELO) timeline</h3>
                    <div className={styles.chartWrapper}>
                      <SvgTimelineChart history={expertDetail.elo_history} />
                    </div>
                  </div>

                  {/* Case Participation List & Self-Critiques */}
                  <div className={`${styles.casesCard} glass`}>
                    <h3 className={styles.cardHeaderSmall}>Deliberation & Self-Critique History</h3>
                    <div className={styles.caseList}>
                      {expertDetail.participations.length > 0 ? (
                        expertDetail.participations.map((part, index) => (
                          <div key={index} className={styles.caseItem}>
                            <div className={styles.caseItemHeader}>
                              <strong className={styles.caseQuery}>"{part.case_query}"</strong>
                              <span className={styles.caseDate}>{new Date(part.created_at).toLocaleDateString()}</span>
                            </div>
                            <div className={styles.caseItemMeta}>
                              <span className={styles.caseRec}>Rec: {part.recommendation}</span>
                              <span className={styles.caseConf}>Conf: {part.confidence}%</span>
                              <span className={styles.caseScore}>Score: {part.contribution_score}%</span>
                            </div>
                            <p className={styles.caseReasoning}>
                              <strong>Reasoning:</strong> {part.reasoning}
                            </p>
                            {part.self_critique && (
                              <div className={styles.selfCritiqueBlock}>
                                <strong>⚠️ Retrospective Self-Critique:</strong> {part.self_critique}
                              </div>
                            )}
                          </div>
                        ))
                      ) : (
                        <p className={styles.emptyText}>No case participations recorded yet.</p>
                      )}
                    </div>
                  </div>
                </div>
              ) : (
                <p className={styles.emptyText}>Select an expert to display detailed performance analytics.</p>
              )}
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
