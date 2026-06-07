/**
 * src/api/client.js
 * Thin fetch wrapper for all Delphi API calls.
 * Uses relative paths so the Vite dev proxy forwards to :8000.
 */

const BASE = '/api/v1';

async function request(method, path, body) {
  const opts = {
    method,
    headers: { 'Content-Type': 'application/json' },
  };
  if (body !== undefined) opts.body = JSON.stringify(body);

  const res = await fetch(`${BASE}${path}`, opts);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

/** POST /decisions → { case_id, status, message } */
export function submitDecision(query, mock = false) {
  return request('POST', '/decisions', { query, mock });
}

/** GET /decisions/{case_id} → DecisionStatusResponse */
export function getDecision(caseId) {
  return request('GET', `/decisions/${caseId}`);
}

/** GET /decisions/{case_id}/stage → partial stage snapshot */
export function getStageData(caseId) {
  return request('GET', `/decisions/${caseId}/stage`);
}

/** GET /decisions → list of recent cases */
export function listDecisions(limit = 8) {
  return request('GET', `/decisions?limit=${limit}`);
}

/** GET /analytics/leaderboard → list of experts sorted by ELO */
export function getLeaderboard() {
  return request('GET', '/analytics/leaderboard');
}

/** GET /analytics/memory-bank → combined reflections and success patterns */
export function getMemoryBank() {
  return request('GET', '/analytics/memory-bank');
}

/** GET /analytics/timeline → list of recent reputation history entries */
export function getTimeline() {
  return request('GET', '/analytics/timeline');
}

/** GET /analytics/experts/{id} → detailed analytics for single expert */
export function getExpertDetail(expertId) {
  return request('GET', `/analytics/experts/${expertId}`);
}

