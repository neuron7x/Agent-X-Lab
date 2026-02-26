export type GateStatus = 'PASS' | 'FAIL' | 'RUNNING' | 'ASSUMED' | 'PENDING' | 'BLOCKED';

export interface VRData {
  status: string;
  utc: string;
  work_id: string;
  blockers: unknown[];
  metrics: Record<string, unknown> & {
    pass_rate?: number;
    baseline_pass?: boolean;
    catalog_ok?: boolean;
    determinism?: string;
    determinism_ok?: boolean;
    evidence_manifest_entries?: number;
    catalog_objects?: number;
  };
  schema?: string;
}

export interface ContractJson {
  required_checks: Array<{ name: string; description?: string }>;
  [key: string]: unknown;
}

export interface EvidenceEvent {
  ts?: string;
  utc?: string;
  id?: string;
  command?: string;
  exit?: number;
  status?: string;
  path?: string;
  sha?: string;
  [key: string]: unknown;
}

export interface Gate {
  id: string;
  status: GateStatus;
  tool: string;
  elapsed: string;
  log?: string;
}

export interface EvidenceEntry {
  timestamp: string;
  type: string;
  status: GateStatus;
  sha: string;
  path: string;
}

export interface PullRequest {
  number: number;
  title: string;
  checksTotal: number;
  checksPassed: number;
  checksFailed: number;
  url: string;
}

/**
 * GitHubSettings — NO TOKEN.
 * The PAT lives exclusively in the Cloudflare Worker secret (GITHUB_TOKEN).
 * The browser only stores owner, repo, pollInterval.
 * token field kept as optional for legacy type compat — always empty string.
 */
export interface GitHubSettings {
  token: string;      // ALWAYS '' — never stored, never sent from browser
  owner: string;
  repo: string;
  pollInterval: number;
}

export type ArsenalRole = 'PR-AGENT' | 'CI-AGENT' | 'DOCS-AGENT' | 'SCIENCE-AGENT' | 'SECURITY-AGENT' | 'OTHER';

export type ArsenalFilter = 'ALL' | ArsenalRole;

export interface ArsenalPrompt {
  id: string;
  title: string;
  role: ArsenalRole;
  version: string;
  target: string;
  content: string;
  sha: string;
  path: string;
}

export type ConnectionStatus = 'DISCONNECTED' | 'CONNECTED' | 'POLLING' | 'ERROR' | 'RATE_LIMITED';

export interface AXLState {
  vrData: VRData | null;
  gates: Gate[];
  evidence: EvidenceEntry[];
  prs: PullRequest[];
  connectionStatus: ConnectionStatus;
  error: string | null;
  rateLimitReset: number | null;
  lastVerified: string | null;
}
