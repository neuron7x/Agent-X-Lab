#!/bin/sh
set -eu

VERIFY_ONLY=0
if [ "${1-}" = "--verify-only" ]; then
  VERIFY_ONLY=1
fi

run_step() {
  printf '\n==> %s\n' "$1"
  shift
  "$@"
}

if [ "$VERIFY_ONLY" -eq 1 ]; then
  run_step "doctor" make doctor
  run_step "check" make check
  run_step "test" make test
  printf '\nDone. Verify-only run completed. Next step: make proof\n'
  exit 0
fi

run_step "doctor" make doctor
run_step "setup" make setup
run_step "check" make check
run_step "test" make test

printf '\nDone. Next steps:\n'
printf '  1) make proof\n'
printf '  2) Review artifacts/ for generated evidence\n'
