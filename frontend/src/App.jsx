/**
 * App.jsx — Root state machine.
 * Maps pipeline status → screen component.
 */
import { useCallback, useState } from 'react';
import { useDecision } from './hooks/useDecision';
import PipelineRail from './components/PipelineRail';
import Chamber    from './views/Chamber';
import Council    from './views/Council';
import Debate     from './views/Debate';
import Judge      from './views/Judge';
import Verdict    from './views/Verdict';
import ErrorView  from './views/ErrorView';
import Dashboard  from './views/Dashboard';
import styles from './App.module.css';

/**
 * Which screen to show based on pipeline status.
 * Screens are shown "in advance" — e.g. show Council screen starting at
 * council_formation, keep it until debate begins (so user sees the council
 * even while waiting for debate data to arrive).
 */
function resolveScreen(status) {
  switch (status) {
    case 'idle':
      return 'chamber';
    case 'pending':
    case 'routing':
    case 'council_formation':
      return 'council';
    case 'debate':
      return 'debate';
    case 'judging':
    case 'consensus':
      return 'judge';
    case 'completed':
      return 'verdict';
    case 'failed':
      return 'error';
    default:
      return 'chamber';
  }
}

export default function App() {
  const { caseId, status, caseData, stageData, error, startCase, reset } = useDecision();
  const [activeView, setActiveView] = useState('decision'); // 'decision' | 'dashboard'

  const handleStart = useCallback((id) => {
    setActiveView('decision');
    startCase(id);
  }, [startCase]);

  const handleReset = useCallback(() => {
    setActiveView('decision');
    reset();
  }, [reset]);

  const screen = resolveScreen(status);
  const showRail = screen !== 'chamber';

  return (
    <div className={styles.app}>
      {/* Always-visible pipeline rail (except on landing) */}
      {showRail && (
        <PipelineRail status={status} />
      )}

      {/* Active query banner */}
      {caseId && screen !== 'verdict' && screen !== 'error' && (
        <div className={styles.queryBanner}>
          <span className={styles.queryBannerLabel}>Query</span>
          <span className={styles.queryBannerText}>{caseData?.query ?? '…'}</span>
        </div>
      )}

      {/* Main content area */}
      <main className={styles.main} key={screen === 'chamber' ? `${screen}-${activeView}` : screen}>
        {screen === 'chamber' && activeView === 'decision' && (
          <Chamber onStart={handleStart} onViewDashboard={() => setActiveView('dashboard')} />
        )}
        {screen === 'chamber' && activeView === 'dashboard' && (
          <Dashboard onBack={() => setActiveView('decision')} />
        )}
        {screen === 'council' && (
          <Council stageData={stageData} status={status} />
        )}
        {screen === 'debate' && (
          <Debate stageData={stageData} status={status} />
        )}
        {screen === 'judge' && (
          <Judge stageData={stageData} status={status} />
        )}
        {screen === 'verdict' && (
          <Verdict caseData={caseData} stageData={stageData} onReset={handleReset} />
        )}
        {screen === 'error' && (
          <ErrorView error={error || caseData?.error_detail} onReset={handleReset} />
        )}
      </main>

      {/* Footer */}
      <footer className={styles.footer}>
        <span>DELPHI</span>
        <span className={styles.footerDot}>·</span>
        <span>Multi-Agent Decision Intelligence</span>
      </footer>
    </div>
  );
}
