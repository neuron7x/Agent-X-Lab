import type {
  CoverageProvider,
  CoverageProviderModule,
  ReportContext,
  ResolvedCoverageOptions,
  Vitest,
} from "vitest/node";

class NoopCoverageProvider implements CoverageProvider {
  name = "custom";

  private options!: ResolvedCoverageOptions<"custom">;

  initialize(ctx: Vitest): void {
    this.options = ctx.config.coverage as ResolvedCoverageOptions<"custom">;
  }

  resolveOptions(): ResolvedCoverageOptions<"custom"> {
    return this.options;
  }

  async clean(): Promise<void> {
    // No-op: custom provider doesn't emit coverage artifacts.
  }

  async onAfterSuiteRun(): Promise<void> {
    // No-op: no runtime coverage data to aggregate.
  }

  generateCoverage(_reportContext: ReportContext): Record<string, never> {
    return {};
  }

  async reportCoverage(_coverage: unknown, _reportContext: ReportContext): Promise<void> {
    // No-op: keep test command functional in restricted environments.
  }
}

const module: CoverageProviderModule = {
  getProvider: () => new NoopCoverageProvider(),
};

export default module;
