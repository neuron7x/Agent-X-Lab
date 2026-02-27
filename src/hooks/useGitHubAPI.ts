/* eslint-disable react-hooks/rules-of-hooks */
import { useEffect, useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import type { GitHubSettings, AXLState, Gate, EvidenceEntry, ContractJson } from '@/lib/types';
import {
  fetchVRJson,
  fetchContract,
  fetchEvidenceJsonl,
  fetchPullRequests,
  fetchActionRuns,
  resolveGatesFromContract,
} from '@/lib/github';
import { MOCK_VR, MOCK_GATES, MOCK_EVIDENCE, MOCK_PRS } from '@/lib/mockData';

function isRateLimitError(err: unknown): err is Error {
  return err instanceof Error && err.message.startsWith('RATE_LIMITED:');
}

function parseRateLimitReset(err: unknown): number | null {
  if (!isRateLimitError(err)) return null;
  const parts = err.message.split(':');
  const resetStr = parts.length >= 2 ? parts[1] : '';
  const reset = parseInt(resetStr, 10);
  return Number.isFinite(reset) && reset > 0 ? reset : null;
}

function isContractMissingError(err: unknown): boolean {
  if (!(err instanceof Error)) return false;
  // cachedFetch throws: API_ERROR:<status>:<url>
  return err.message.startsWith('API_ERROR:404:') && err.message.includes('/contents/artifacts/agent/contract.json');
}

export function useGitHubAPI(settings: GitHubSettings, isConfigured: boolean, demoMode: boolean) {
  const pollMs = settings.pollInterval * 1000;

  // Persist rate-limit reset across renders so we can stop polling deterministically.
  const [rateLimitResetState, setRateLimitResetState] = useState<number | null>(null);
  const [nowSec, setNowSec] = useState(() => Math.floor(Date.now() / 1000));

  const recordRateLimit = (err: unknown) => {
    const reset = parseRateLimitReset(err);
    if (!reset) return;
    setRateLimitResetState(prev => {
      if (!prev) return reset;
      return reset > prev ? reset : prev;
    });
  };

  // Base enable: fully halt all polling while rate-limited.
  const isRateLimitedByState = rateLimitResetState !== null && nowSec < rateLimitResetState;
  const baseEnabled = isConfigured && !demoMode && !isRateLimitedByState;

  // VR.json
  const vrQuery = useQuery({
    queryKey: ['vr', settings.owner, settings.repo],
    queryFn: () => fetchVRJson(settings),
    enabled: baseEnabled,
    refetchInterval: baseEnabled ? pollMs : false,
    retry: (failureCount, error) => {
      if (isRateLimitError(error)) return false;
      return failureCount < 1;
    },
    onError: recordRateLimit,
  });

  // contract.json
  const contractQuery = useQuery({
    queryKey: ['contract', settings.owner, settings.repo],
    queryFn: () => fetchContract(settings),
    enabled: baseEnabled,
    refetchInterval: baseEnabled ? pollMs * 2 : false,
    retry: (failureCount, error) => {
      if (isRateLimitError(error)) return false;
      return failureCount < 1;
    },
    onError: recordRateLimit,
  });

  // evidence.jsonl
  const evidenceQuery = useQuery({
    queryKey: ['evidence-jsonl', settings.owner, settings.repo],
    queryFn: () => fetchEvidenceJsonl(settings),
    enabled: baseEnabled,
    refetchInterval: baseEnabled ? pollMs : false,
    retry: (failureCount, error) => {
      if (isRateLimitError(error)) return false;
      return failureCount < 1;
    },
    onError: recordRateLimit,
  });

  // workflow runs
  const runsQuery = useQuery({
    queryKey: ['runs', settings.owner, settings.repo],
    queryFn: () => fetchActionRuns(settings, { branch: 'main', per_page: 50 }),
    enabled: baseEnabled,
    refetchInterval: baseEnabled ? pollMs : false,
    retry: (failureCount, error) => {
      if (isRateLimitError(error)) return false;
      return failureCount < 1;
    },
    onError: recordRateLimit,
  });

  // PRs
  const prsQuery = useQuery({
    queryKey: ['prs', settings.owner, settings.repo],
    queryFn: () => fetchPullRequests(settings),
    enabled: baseEnabled,
    refetchInterval: baseEnabled ? pollMs : false,
    retry: (failureCount, error) => {
      if (isRateLimitError(error)) return false;
      return failureCount < 1;
    },
    onError: recordRateLimit,
  });

  // Resolve gates from contract + runs
  const contract = contractQuery.data as ContractJson | undefined;
  const runs = runsQuery.data?.workflow_runs;

  const gatesQuery = useQuery({
    queryKey: ['gates-resolved', settings.owner, settings.repo, contract?.required_checks?.length, runs?.length],
    queryFn: () => resolveGatesFromContract(settings, contract!, runs!),
    enabled: baseEnabled && !!contract && !!runs && runs.length > 0,
    staleTime: pollMs,
    retry: (failureCount, error) => {
      if (isRateLimitError(error)) return false;
      return failureCount < 1;
    },
    onError: recordRateLimit,
  });

  if (demoMode) {
    return {
      vrData: MOCK_VR,
      gates: MOCK_GATES,
      evidence: MOCK_EVIDENCE,
      prs: MOCK_PRS,
      connectionStatus: 'DISCONNECTED' as const,
      error: null,
      rateLimitReset: null,
      isLoading: false,
      contractError: null,
      parseFailures: 0,
      refetch: () => {},
    };
  }

  // Clear rate limit state after reset.
  useEffect(() => {
    if (!rateLimitResetState) return;
    if (nowSec >= rateLimitResetState) setRateLimitResetState(null);
  }, [nowSec, rateLimitResetState]);

  const effectiveRateLimitReset = rateLimitResetState;
  const isRateLimitedActive = effectiveRateLimitReset !== null && nowSec < effectiveRateLimitReset;

  // Ensure we tick time whenever we are rate-limited.
  useEffect(() => {
    if (!isRateLimitedActive) return;
    const id = window.setInterval(() => setNowSec(Math.floor(Date.now() / 1000)), 1000);
    return () => window.clearInterval(id);
  }, [isRateLimitedActive]);

  const anyNonRateError = useMemo(() => {
    const queryErrors = [
      vrQuery.error,
      contractQuery.error,
      evidenceQuery.error,
      runsQuery.error,
      prsQuery.error,
      gatesQuery.error,
    ];

    for (const error of queryErrors) {
      if (!error) continue;
      if (isRateLimitError(error)) continue;
      return error as Error;
    }

    return null;
  }, [
    vrQuery.error,
    contractQuery.error,
    evidenceQuery.error,
    runsQuery.error,
    prsQuery.error,
    gatesQuery.error,
  ]);

  let connectionStatus: AXLState['connectionStatus'] = 'DISCONNECTED';

  const haveData = Boolean(
    vrQuery.data ||
      contractQuery.data ||
      evidenceQuery.data ||
      runsQuery.data ||
      prsQuery.data
  );

  const isFetchingAny = Boolean(
    vrQuery.isFetching ||
      contractQuery.isFetching ||
      evidenceQuery.isFetching ||
      runsQuery.isFetching ||
      prsQuery.isFetching
  );

  if (!isConfigured) {
    connectionStatus = 'DISCONNECTED';
  } else if (isRateLimitedActive) {
    connectionStatus = 'RATE_LIMITED';
  } else if (anyNonRateError) {
    connectionStatus = 'ERROR';
  } else if (isFetchingAny && haveData) {
    connectionStatus = 'POLLING';
  } else if (haveData && !isFetchingAny) {
    connectionStatus = 'CONNECTED';
  } else {
    connectionStatus = 'DISCONNECTED';
  }

  // Contract missing = explicit error (do not override RATE_LIMITED)
  const contractError = contractQuery.error && isContractMissingError(contractQuery.error) ? 'MISSING_CONTRACT_SSOT' : null;

  const gates: Gate[] = gatesQuery.data || [];

  const evidence: EvidenceEntry[] = evidenceQuery.data?.entries || [];
  const parseFailures = evidenceQuery.data?.parseFailures || 0;

  const errorMessage = anyNonRateError ? anyNonRateError.message : null;

  return {
    vrData: vrQuery.data || null,
    gates,
    evidence,
    prs: prsQuery.data || [],
    connectionStatus,
    error: errorMessage,
    rateLimitReset: effectiveRateLimitReset,
    isLoading: vrQuery.isLoading,
    contractError,
    parseFailures,
    refetch: () => {
      if (isRateLimitedActive) return;
      vrQuery.refetch();
      contractQuery.refetch();
      runsQuery.refetch();
      prsQuery.refetch();
      evidenceQuery.refetch();
    },
  };
}
