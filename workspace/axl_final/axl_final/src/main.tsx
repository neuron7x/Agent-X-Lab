import { createRoot } from "react-dom/client";
import App from "./App.tsx";
import "./index.css";
import { initObservability } from "./lib/observability";

// Boot observability (Sentry when DSN configured, structured logging always)
initObservability().catch(console.error);

createRoot(document.getElementById("root")!).render(<App />);
