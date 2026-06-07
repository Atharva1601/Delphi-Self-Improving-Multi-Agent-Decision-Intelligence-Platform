/**
 * src/hooks/useDecision.js
 * Polling hook that drives the UI state machine.
 * Polls getDecision + getStageData every 2s until completed/failed.
 */
import { useState, useEffect, useRef, useCallback } from 'react';
import { getDecision, getStageData } from '../api/client';

const TERMINAL_STATUSES = new Set(['completed', 'failed']);
const POLL_INTERVAL_MS = 2000;

export function useDecision() {
  const [caseId, setCaseId]       = useState(null);
  const [status, setStatus]       = useState('idle');   // idle | pending | <CaseStatus> | completed | failed
  const [caseData, setCaseData]   = useState(null);     // DecisionStatusResponse
  const [stageData, setStageData] = useState({});       // incremental pipeline snapshot
  const [error, setError]         = useState(null);

  const intervalRef = useRef(null);

  const stopPolling = useCallback(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
  }, []);

  const poll = useCallback(async (id) => {
    try {
      const [decision, stage] = await Promise.all([
        getDecision(id),
        getStageData(id),
      ]);
      setCaseData(decision);
      setStageData(stage || {});
      setStatus(decision.status);

      if (TERMINAL_STATUSES.has(decision.status)) {
        stopPolling();
      }
    } catch (err) {
      setError(err.message);
      setStatus('failed');
      stopPolling();
    }
  }, [stopPolling]);

  const startCase = useCallback((id) => {
    setCaseId(id);
    setStatus('pending');
    setCaseData(null);
    setStageData({});
    setError(null);

    // Immediate first poll
    poll(id);

    intervalRef.current = setInterval(() => poll(id), POLL_INTERVAL_MS);
  }, [poll]);

  const reset = useCallback(() => {
    stopPolling();
    setCaseId(null);
    setStatus('idle');
    setCaseData(null);
    setStageData({});
    setError(null);
  }, [stopPolling]);

  // Cleanup on unmount
  useEffect(() => () => stopPolling(), [stopPolling]);

  return { caseId, status, caseData, stageData, error, startCase, reset };
}
