export type AuthFailureEvent = {
  reason: string;
  status: 401 | 403;
  requestId: string;
};

type AuthFailureListener = (event: AuthFailureEvent) => void;

const listeners = new Set<AuthFailureListener>();

export const onAuthFailure = (listener: AuthFailureListener): (() => void) => {
  listeners.add(listener);
  return () => listeners.delete(listener);
};

export const emitAuthFailure = (event: AuthFailureEvent): void => {
  listeners.forEach((listener) => listener(event));
};

export const __resetAuthEventsForTests = (): void => {
  listeners.clear();
};
