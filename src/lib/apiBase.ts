export function getApiBase(): string {
  const base = (import.meta.env?.VITE_AXL_API_BASE as string | undefined) ?? "";
  if (base) {
    return base.replace(/\/$/, "");
  }
  if (import.meta.env?.DEV) {
    return "http://localhost:8787";
  }
  throw new Error("VITE_AXL_API_BASE is not configured. Set it in your environment variables.");
}
