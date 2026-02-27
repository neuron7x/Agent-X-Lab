export type ActionGateStatus =
  | 'ALLOWED'
  | 'DEV_BYPASS'
  | 'BLOCKED';

function isDevEnv(): boolean {
  return import.meta.env.DEV === true || window.location.hostname === 'localhost';
}

function hasApiKey(): boolean {
  return Boolean(import.meta.env.VITE_AXL_API_KEY);
}

export function getActionGateStatus(): ActionGateStatus {
  if (hasApiKey()) return 'ALLOWED';
  if (isDevEnv()) return 'DEV_BYPASS';
  return 'BLOCKED';
}
