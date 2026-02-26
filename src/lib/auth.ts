import { useEffect, useSyncExternalStore } from "react";
import { apiFetch } from "@/lib/apiFetch";
import { whoamiSchema } from "@/lib/apiSchemas";
import { isAxlError } from "@/lib/error";

export type AuthState = {
  status: "PENDING" | "AUTHORIZED" | "UNAUTHORIZED";
  user?: { email?: string };
  reason?: string;
};

let authState: AuthState = { status: "PENDING" };
let initialized = false;
const subscribers = new Set<() => void>();

const emit = (): void => subscribers.forEach((fn) => fn());

const setAuthState = (next: AuthState): void => {
  authState = next;
  emit();
};

const fetchWhoAmI = async (): Promise<void> => {
  setAuthState({ status: "PENDING" });
  try {
    const { data } = await apiFetch({ url: "/whoami", schema: whoamiSchema });
    if (data.user) {
      setAuthState({ status: "AUTHORIZED", user: { email: data.user.email } });
      return;
    }
    setAuthState({ status: "UNAUTHORIZED", reason: "missing_user" });
  } catch (error) {
    if (isAxlError(error) && error.kind === "HttpError" && error.status === 404) {
      setAuthState({ status: "UNAUTHORIZED", reason: "whoami_missing" });
      return;
    }
    setAuthState({ status: "UNAUTHORIZED", reason: isAxlError(error) ? error.kind : "unknown" });
  }
};

export const initializeAuth = async (): Promise<void> => {
  if (initialized) return;
  initialized = true;
  await fetchWhoAmI();
};

export const subscribeAuth = (listener: () => void): (() => void) => {
  subscribers.add(listener);
  return () => subscribers.delete(listener);
};

export const getAuthSnapshot = (): AuthState => authState;

export function useAuth(): AuthState {
  useEffect(() => {
    void initializeAuth();
  }, []);

  return useSyncExternalStore(subscribeAuth, getAuthSnapshot, getAuthSnapshot);
}

export const __resetAuthForTests = (): void => {
  authState = { status: "PENDING" };
  initialized = false;
  subscribers.clear();
};
