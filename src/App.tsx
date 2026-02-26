/**
 * App root — D1: route-based architecture with code-splitting.
 * Each route is a separate lazy chunk.
 */
import { Toaster } from "@/components/ui/toaster";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { LanguageProvider } from "@/hooks/useLanguage";
import { AppShell } from "@/components/shell/AppShell";
import { ToastHost } from "@/components/ToastHost";
import { isAxlError } from "@/lib/error";
import {
  StatusRoute,
  PipelineRoute,
  EvidenceRoute,
  ArsenalRoute,
  ForgeRoute,
  SettingsRoute,
} from "@/modules/index";
import NotFound from "./pages/NotFound";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: (failureCount, error) => {
        // Don't retry auth/rate limit errors
        if (isAxlError(error) && (error.kind === 'AuthError' || error.kind === 'RateLimitError')) return false;
        return failureCount < 2;
      },
      refetchOnWindowFocus: true,
    },
  },
});

const App = () => (
  <QueryClientProvider client={queryClient}>
    <TooltipProvider>
      <LanguageProvider>
        <Toaster />
        <Sonner />
        <ToastHost />
        <BrowserRouter>
          <Routes>
            <Route element={<AppShell />}>
              <Route index element={<StatusRoute />} />
              <Route path="pipeline" element={<PipelineRoute />} />
              <Route path="evidence" element={<EvidenceRoute />} />
              <Route path="arsenal" element={<ArsenalRoute />} />
              <Route path="forge" element={<ForgeRoute />} />
              <Route path="settings" element={<SettingsRoute />} />
            </Route>
            <Route path="*" element={<NotFound />} />
          </Routes>
        </BrowserRouter>
      </LanguageProvider>
    </TooltipProvider>
  </QueryClientProvider>
);

export default App;
