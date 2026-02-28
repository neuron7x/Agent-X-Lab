import { createRoot } from "react-dom/client";
import App from "./App.tsx";
import "./index.css";
import { initObservability } from "./lib/observability";

/**
 * UI runtime entrypoint.
 *
 * Invariants:
 * - Observability boot is non-blocking for render (errors are logged, not rethrown).
 * - The browser process only mounts the React tree; network boundaries live in `src/lib/api.ts`.
 */
initObservability().catch(console.error);

createRoot(document.getElementById("root")!).render(<App />);
