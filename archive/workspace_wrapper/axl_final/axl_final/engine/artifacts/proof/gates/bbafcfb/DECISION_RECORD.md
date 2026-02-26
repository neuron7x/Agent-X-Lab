Constraints: keep fail-closed behavior, support non-git, minimal scope.

Chosen fixes:
- Catch ValueError in CLI vr and return contract code 3.
- Avoid global BUILD_ID mutation; patch stack test for non-git fallback instead.
- Skip generated-artifact invariant only when git checkout unavailable.
- Add CI push trigger + expanded Python matrix.
- Add secret-scan gate in make check and fallback file enumeration when git absent.
- Enable mypy check_untyped_defs and keep typecheck green.

Rejected alternatives:
- Session autouse BUILD_ID fixture (breaks env isolation tests).
- Disabling non-git tests (green-by-omission risk).
