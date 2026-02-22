# OPERATIONS

## Observability contract

### Structured logs (JSON)
All logs are JSON objects with deterministic key ordering.

Required fields:
- `ts` (UTC ISO-8601)
- `level`
- `logger`
- `event`
- `message`
- `request_id`

Common event-specific fields:
- `command`
- `backend`
- `error_code`
- `latency_ms`
- `gate_outcome`
- `status`

### Metrics contract
Metrics are emitted to JSONL (default: `artifacts/observability/metrics.jsonl`) with one object per line.

Required metric fields:
- `metric` (currently `sg.command`)
- `request_id`
- `status` (`success` or `error`)
- `success` (`true`/`false`)
- `latency_ms`
- `latency_bucket` (`le_50ms`, `le_100ms`, `le_250ms`, `le_500ms`, `le_1000ms`, `gt_1000ms`)
- `gate_outcome` (`success`, `failure`, `error`)
- `error` (nullable)
- `ts`

## Correlation/request ID
- Provide with CLI flag `--request-id` to preserve an external correlation id.
- If omitted, a UUIDv4 hex id is generated.
- The same value is injected into all logs and metrics emitted during one CLI invocation.

## Alert examples
1. **Command error spike**
   - Condition: `metric=sg.command AND status=error` over 5 minutes exceeds baseline.
2. **Latency regression**
   - Condition: `metric=sg.command AND latency_bucket in (le_1000ms, gt_1000ms)` ratio > threshold.
3. **Gate failures**
   - Condition: `metric=sg.command AND gate_outcome=failure` detected in CI runs.
4. **Missing request id (pipeline guard)**
   - Condition: any log/metric missing non-empty `request_id` should fail ingest validation.
