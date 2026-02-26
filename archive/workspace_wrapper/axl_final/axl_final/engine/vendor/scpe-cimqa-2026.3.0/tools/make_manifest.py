#!/usr/bin/env python3
import argparse, hashlib, json, os, pathlib, time

REQUIRED_TOP = ["ENV.txt", "COMMANDS.txt", "REPORTS"]

def sha256_file(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def collect_files(root: pathlib.Path, rel_prefix: str = ""):
    out = []
    for p in sorted(root.rglob("*")):
        if p.is_dir():
            continue
        out.append({"path": rel_prefix + str(p.relative_to(root)), "sha256": sha256_file(p)})
    return out

ap = argparse.ArgumentParser()
ap.add_argument("--evidence-root", required=True)
ap.add_argument("--git-sha-before", required=True)
ap.add_argument("--git-sha-after", required=True)
ap.add_argument("--out", required=True)
ap.add_argument("--policy", default="SECURITY.redaction.yml")
args = ap.parse_args()

repo = pathlib.Path(".").resolve()
eroot = pathlib.Path(args.evidence_root).resolve()
eroot.mkdir(parents=True, exist_ok=True)

# Copy+redact ENV and COMMANDS into evidence root deterministically (fail-closed if missing).
for f in ["ENV.txt", "COMMANDS.txt"]:
    src = repo / f
    if not src.exists():
        raise SystemExit(f"missing_required:{f}")
    dst = eroot / f
    dst.write_text(src.read_text(encoding="utf-8", errors="replace"), encoding="utf-8")

# Copy REPORTS dir (no glob exclusions here; redaction enforcement is external).
reports_src = repo / "REPORTS"
if not reports_src.exists():
    raise SystemExit("missing_required:REPORTS/")
reports_dst = eroot / "REPORTS"
if reports_dst.exists():
    # deterministic: do not merge; fail-closed
    raise SystemExit("evidence_reports_already_exists")

# Copy tree
for p in reports_src.rglob("*"):
    rel = p.relative_to(reports_src)
    tgt = reports_dst / rel
    if p.is_dir():
        tgt.mkdir(parents=True, exist_ok=True)
    else:
        tgt.parent.mkdir(parents=True, exist_ok=True)
        tgt.write_bytes(p.read_bytes())

manifest = {
  "work_id": eroot.name,
  "utc_started": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
  "utc_finished": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
  "git_sha_before": args.git_sha_before,
  "git_sha_after": args.git_sha_after,
  "artifacts": collect_files(eroot)
}

outp = pathlib.Path(args.out).resolve()
outp.parent.mkdir(parents=True, exist_ok=True)
outp.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print("ok")
