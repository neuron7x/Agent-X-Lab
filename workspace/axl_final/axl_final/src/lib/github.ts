/**
 * @deprecated Use src/lib/api.ts directly.
 *
 * This module re-exports everything from api.ts for backward compatibility.
 * All GitHub API calls are now routed through the BFF Worker.
 * Zero direct api.github.com calls from browser.
 *
 * MIGRATION: Replace `import { X } from '@/lib/github'`
 *            with     `import { X } from '@/lib/api'`
 */

export {
  type GitHubSettings,
  testConnection,
  fetchRepoInfo,
  fetchContentsText,
  fetchContentsJson,
  fetchVRJsonSettings as fetchVRJson,
  fetchContract,
  fetchManifest,
  parseEvidenceLines,
  fetchEvidenceJsonl,
  fetchActionRuns,
  fetchRunJobs,
  mapJobToGateStatus,
  jobElapsed,
  resolveGatesFromContract,
  fetchPullRequests,
  parseArsenalMeta,
  fetchArsenalIndex,
  dispatchRunEngine,
  AXLApiError,
} from './api';
