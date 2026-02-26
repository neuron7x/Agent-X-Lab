/**
 * Stable TanStack Query key factory.
 * Single source of truth — prevents cache mismatches across modules.
 */

export const QK = {
  healthz: () => ['healthz'] as const,

  vr: (owner: string, repo: string) =>
    ['vr', owner, repo] as const,

  contract: (owner: string, repo: string) =>
    ['contract', owner, repo] as const,

  evidence: (owner: string, repo: string) =>
    ['evidence', owner, repo] as const,

  runs: (owner: string, repo: string) =>
    ['runs', owner, repo] as const,

  prs: (owner: string, repo: string) =>
    ['prs', owner, repo] as const,

  gates: (owner: string, repo: string, contractLen: number, runsLen: number) =>
    ['gates-resolved', owner, repo, contractLen, runsLen] as const,

  arsenal: (owner: string, repo: string, ref: string) =>
    ['arsenal', owner, repo, ref] as const,
} as const;

/**
 * Stale / refetch times per resource type.
 * Adjust based on observed freshness needs.
 */
export const CACHE_POLICY = {
  healthz: { staleTime: 30_000, refetchInterval: 30_000 },
  vr: { staleTime: 60_000, refetchInterval: 90_000 },
  contract: { staleTime: 5 * 60_000 },
  evidence: { staleTime: 2 * 60_000 },
  runs: { staleTime: 60_000, refetchInterval: 120_000 },
  prs: { staleTime: 2 * 60_000 },
  arsenal: { staleTime: 10 * 60_000 },
} as const;
