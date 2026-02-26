# Submission metadata (arXiv / public preprint)

## Title
**The Dopaminergic Arbiter Hypothesis: Human Loop-Closure as a Necessary Invariant in AI Alignment**

## Author
Yaroslav Vasylenko (Ukraine)

## Categories
- cs.AI (primary)
- cs.LG
- q-bio.NC

## Abstract (≥150 words)

We propose the **Dopaminergic Arbiter Hypothesis**: alignment failures in agentic optimization are, at root, failures of **termination**. An optimizer that cannot receive an externally verified “stop” signal lacks a gradient toward “enough” and tends to prolong or expand optimization beyond the intended target. We formalize a three-plane architecture—**Control** (human governor), **Data** (AI agents), and **Truth** (CI/oracle)—that separates goal-setting, proposal generation, and objective verification. Methodologically, we treat each iteration as a closed-loop control cycle governed by a *PASS_CONTRACT* (explicit done-when criteria and constraints). Failures are reduced to a minimal **FAIL_PACKET** (verbatim error extract + single reproduction command), and successful closures are attested by a **PROOF_BUNDLE** (green checks + artifact hashes + timestamp). As an existence proof, we describe the author’s DAO-LIFEBOOK operational practice for coordinating multiple agent proposals while preserving an external merge/termination decision. The hypothesis yields falsifiable predictions about when automated self-evaluation fails and when external truth-plane constraints restore stable loop-closure. We conclude that “alignment” must explicitly include a verified termination mechanism, not only preference shaping or reward optimization.

## Comments
This repository contains the preprint PDF and operational schemas for FAIL_PACKET and PROOF_BUNDLE.

## License
For this repository: CC BY 4.0 for text/preprint; MIT for schemas/scripts (see `LICENSE` and `LICENSE-MIT`).
