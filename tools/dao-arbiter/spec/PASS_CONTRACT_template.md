# PASS_CONTRACT (template)

A PASS_CONTRACT defines the termination criteria for **one** closure cycle.

## TARGET_STATE
- goal: "<one-sentence, externally verifiable end state>"
- scope: "<what is in-scope and out-of-scope>"

## DONE_WHEN (binary checklist)
When *all* items below are true, the cycle is eligible for closure.

- [ ] Required checks are green in CI (truth plane).
- [ ] Artifacts are produced and hashed (PROOF_BUNDLE).
- [ ] All FAIL_PACKETs created in this cycle are resolved or explicitly deferred.
- [ ] No unapproved refactors were introduced (diff budget respected).
- [ ] Human governor explicitly authorizes termination (merge/checkpoint).

## CONSTRAINTS
- refactor_policy: "no-refactor" | "limited" | "allowed"
- diff_budget: "<max files/LOC or specific boundaries>"
- security_policy: "<what must not be disclosed / copied into logs>"
- external_dependencies: "<allowed tools/services for this cycle>"

## REQUIRED_CHECKS (truth plane)
List the checks that constitute “reality” for this cycle.

- check_1: "<name>" — "<how to run locally>"
- check_2: "<name>" — "<how to run locally>"

## PROOF_BUNDLE POINTERS
At closure, record:

- commit_sha: "<git SHA>"
- CI run URL: "<immutable URL>"
- artifact hashes: "<path -> sha256>"

## NOTES
- If a check cannot be made objective, add an oracle step with explicit procedure.
- If the target state is ambiguous, rewrite it until a binary test exists.
