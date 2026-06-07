/**
 * PipelineRail — top progress indicator showing pipeline stages.
 */
import styles from './PipelineRail.module.css';

const STAGES = [
  { key: 'routing',          label: 'Routing'  },
  { key: 'council_formation',label: 'Council'  },
  { key: 'debate',           label: 'Debate'   },
  { key: 'judging',          label: 'Judging'  },
  { key: 'consensus',        label: 'Consensus'},
  { key: 'completed',        label: 'Verdict'  },
];

const STATUS_ORDER = [
  'idle', 'pending', 'routing', 'council_formation',
  'debate', 'judging', 'consensus', 'completed',
];

function stageIndex(status) {
  return STATUS_ORDER.indexOf(status);
}

export default function PipelineRail({ status }) {
  const currentIdx = stageIndex(status);
  const isCompleted = status === 'completed';

  return (
    <div className={styles.rail}>
      <div className={styles.inner}>
        {STAGES.map((stage, i) => {
          const stageIdx = stageIndex(stage.key);
          const isActive  = !isCompleted && stageIdx === currentIdx;
          const isDone    = isCompleted || stageIdx < currentIdx;
          const isPending = !isCompleted && stageIdx > currentIdx;

          return (
            <div key={stage.key} className={styles.stageWrap}>
              {i > 0 && (
                <div className={`${styles.connector} ${isDone || isActive ? styles.connectorActive : ''}`} />
              )}
              <div className={`${styles.node} ${isActive ? styles.nodeActive : ''} ${isDone ? styles.nodeDone : ''} ${isPending ? styles.nodePending : ''}`}>
                <div className={styles.dot}>
                  {isDone && <span className={styles.check}>✓</span>}
                  {isActive && <span className={styles.spinner} />}
                </div>
                <span className={styles.label}>{stage.label}</span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
