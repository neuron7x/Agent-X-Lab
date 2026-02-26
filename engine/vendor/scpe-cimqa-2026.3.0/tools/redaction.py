#!/usr/bin/env python3
import argparse, re, yaml
from pathlib import Path

def load_rules(path: Path):
    spec = yaml.safe_load(path.read_text(encoding="utf-8"))
    rules = []
    for r in (spec.get("rules") or []):
        repl = r.get("replacement", "[REDACTED]")
        for pat in (r.get("patterns") or []):
            rules.append((re.compile(pat), repl))
    return rules

def apply(text: str, rules):
    out = text
    for rx, repl in rules:
        out = rx.sub(repl, out)
    return out

ap = argparse.ArgumentParser()
ap.add_argument("--policy", default="SECURITY.redaction.yml")
ap.add_argument("--in", dest="inp", required=True)
ap.add_argument("--out", required=True)
args = ap.parse_args()

rules = load_rules(Path(args.policy))
raw = Path(args.inp).read_text(encoding="utf-8", errors="replace")
Path(args.out).write_text(apply(raw, rules), encoding="utf-8")
print("ok")
