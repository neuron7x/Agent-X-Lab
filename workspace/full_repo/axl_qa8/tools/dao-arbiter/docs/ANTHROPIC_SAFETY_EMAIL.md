# Email draft: Safety / agentic termination invariant (Anthropic)

Subject: Loop-closure invariant for agentic optimization (DAO-Arbiter preprint)

Hello Anthropic Safety team,

I’m sharing a short preprint and a small reference repository that formalize the **Dopaminergic Arbiter Hypothesis**: in agentic optimization, a major failure mode is the absence of an externally verified termination signal (“enough/stop”). If the system cannot receive a verified stop condition, iteration tends to drift beyond the intended target.

What I’m proposing is a practical separation of planes:
- **Control plane (human):** defines the target state and an explicit PASS_CONTRACT.
- **Data plane (agents):** generates and applies proposals under constraints.
- **Truth plane (CI/oracle):** verifies objective conditions (tests/checks).

Repository contents include:
- Preprint PDF
- FAIL_PACKET and PROOF_BUNDLE schemas
- A realistic loop-closure example and CI verification script

**Repository URL (paste after pushing the repo):**
- Run in the repo root: `gh repo view --json url -q .url`
- Paste the output here before sending.

Thank you for taking a look. If this overlaps with ongoing work in scalable oversight / agentic safety, I’d appreciate pointers to the closest existing framing and where you think this hypothesis is wrong.

Best regards,  
Yaroslav Vasylenko
