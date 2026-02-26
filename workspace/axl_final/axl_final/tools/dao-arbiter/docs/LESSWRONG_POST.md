# LessWrong / Alignment Forum post draft

## Title
The Dopaminergic Arbiter Hypothesis: why “stop” must be externally verifiable in alignment

## TL;DR
Alignment failures are often termination failures. If an optimizer cannot receive an **externally verified** “enough/stop” signal, iteration tends to drift. I propose a three-plane architecture (Control/Data/Truth) and operational artifacts (PASS_CONTRACT, FAIL_PACKET, PROOF_BUNDLE) that make termination explicit.

---

## Core claim
An agentic system cannot, in general, certify its own completeness. Therefore, “done” must be decided by an **external arbiter** plus **objective checks**.

In practice, my proposal is not “replace RLHF”, but to make the missing invariant explicit:

- **Truth plane:** CI/tests/oracles define what is real.
- **Control plane:** a human defines the target state and the termination contract.
- **Data plane:** agents generate and apply proposals under constraints.

---

## The DAO loop (operational)
`FAIL → FIX → PROVE → CHECKPOINT`

- FAIL becomes a **FAIL_PACKET** (verbatim, reproducible).
- PROVE produces a **PROOF_BUNDLE** (green checks + hashes).
- CHECKPOINT is an explicit termination decision (merge/tag).

---

## Related work (and how this differs)

This proposal is adjacent to several alignment threads, but focuses on a specific invariant: **verified termination**.

- **RLHF / preference learning:** shapes behavior toward human preferences, but does not guarantee that an agent will stop iterating when the target is reached, especially under distribution shift or when reward proxies remain exploitable.
- **Scalable oversight / RRM / critique models:** improves evaluation, but can still collapse into self-referential evaluation if the evaluator is not anchored to external checks.
- **IDA / amplification-style agendas:** aim to scale human judgment, but often assume that a (possibly amplified) supervisor can decide completion; DAO treats that completion decision as a first-class contract (PASS_CONTRACT) and binds it to a truth plane (CI).
- **Constitutional / rule-based approaches:** provide constraints, but still require an external ground truth mechanism for “did we satisfy the contract?”

I’m claiming these are complementary; DAO is a runtime **loop-closure layer** for agentic optimization, not a replacement for training-time alignment.

---

## Falsifiable predictions

1. **Termination drift without an external truth plane:**  
   In agentic coding tasks, systems that rely on self-evaluation (no external tests/CI gates) will show higher rates of non-terminating iteration (more tool calls, broader scope drift) compared to identical systems constrained by a PASS_CONTRACT with mandatory external checks.

2. **Hash-anchored artifacts reduce “silent regressions”:**  
   When proofs include artifact hashes (PROOF_BUNDLE) and CI verifies them, the rate of “works on my machine” regressions and post-merge reversions should measurably decrease versus checklists without integrity anchoring.

3. **Explicit done-when contracts improve coordination of multiple agents:**  
   For multi-agent workflows (parallel patch proposals), requiring each proposal to reference the same PASS_CONTRACT should reduce conflict/oscillation (patches undoing each other) compared to unconstrained parallelism.

4. **Human termination is the bottleneck that remains:**  
   Even with strong critics and tools, the ultimate termination decision will concentrate on the control plane; attempts to automate that decision will fail most often in edge cases where external truth-plane signals are ambiguous or incomplete.

Each prediction can be tested with controlled A/B setups in open-source repos using standard CI.

---

## What I want feedback on
- Where exactly does my “termination is missing” framing break?
- What is the minimal counterexample where verified termination exists yet alignment still fails?
- Are there known formalisms in control theory / formal methods that already capture this invariant?

---

## Links (in this repository)
- Preprint PDF: `Vasylenko_DAO_Arbiter_2026.pdf`
- Loop example: `examples/loop_closure_example.md`
- Schemas: `FAIL_PACKET.json`, `PROOF_BUNDLE.json`
