"""
DAO-LIFEBOOK — CLI Interface.

Entry point for running the canonical loop against a GitHub PR.
Uses Rich for structured terminal output.
"""

from __future__ import annotations

import json
import logging
import os
import sys
from pathlib import Path

import typer
from rich.console import Console
from rich.logging import RichHandler
from rich.panel import Panel
from rich.table import Table
from rich.tree import Tree

from .models import (
    AuditVerdict,
    CheckStatus,
    Constraints,
    DiffBudget,
    Phase,
    RefactorPolicy,
    SecurityPolicy,
    TargetState,
)
from .engine import CanonicalLoop, EngineConfig, GovernorDecision
from .evidence import CheckpointStore
from .truth_plane import CIOracle

console = Console()
app = typer.Typer(
    name="dao",
    help="DAO-LIFEBOOK: Deterministic AI Orchestration CLI",
    no_args_is_help=True,
)


def _setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(message)s",
        handlers=[RichHandler(console=console, rich_tracebacks=True)],
    )


def _get_token() -> str:
    token = os.environ.get("GITHUB_TOKEN", "")
    if not token:
        console.print("[red]GITHUB_TOKEN not set[/red]")
        raise typer.Exit(1)
    return token


def _load_config(path: str | None) -> dict:
    if path and Path(path).exists():
        return json.loads(Path(path).read_text())
    return {}


# ─── Commands ─────────────────────────────────────────────────────────────────

@app.command()
def observe(
    pr: str = typer.Argument(..., help="PR reference: owner/repo#N or URL"),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    """Phase A — Observe PR check statuses (read-only)."""
    _setup_logging(verbose)
    token = _get_token()

    with CIOracle(token, pr) as oracle:
        sha, checks = oracle.observe()

    # Display
    table = Table(title=f"Checks for {pr} @ {sha[:7]}")
    table.add_column("Check", style="cyan")
    table.add_column("Status", justify="center")
    table.add_column("URL", style="dim")

    status_styles = {
        CheckStatus.SUCCESS: "[green]✓ success[/green]",
        CheckStatus.FAILURE: "[red]✗ failure[/red]",
        CheckStatus.PENDING: "[yellow]⏳ pending[/yellow]",
        CheckStatus.SKIPPED: "[dim]⊘ skipped[/dim]",
        CheckStatus.UNKNOWN: "[dim]? unknown[/dim]",
    }

    green = 0
    failing = 0
    for c in sorted(checks, key=lambda x: (x.status != CheckStatus.FAILURE, x.name)):
        table.add_row(
            c.name,
            status_styles.get(c.status, c.status.value),
            c.run_url[:80] if c.run_url else "",
        )
        if c.status.is_green:
            green += 1
        elif c.status == CheckStatus.FAILURE:
            failing += 1

    console.print(table)
    console.print(
        f"\n[bold]{len(checks)}[/bold] checks: "
        f"[green]{green} green[/green], "
        f"[red]{failing} failing[/red], "
        f"{len(checks) - green - failing} other"
    )


@app.command()
def packetize(
    pr: str = typer.Argument(..., help="PR reference"),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    """Phase B — Extract FAIL_PACKETs from PR."""
    _setup_logging(verbose)
    token = _get_token()

    with CIOracle(token, pr) as oracle:
        sha, checks = oracle.observe()
        packets = oracle.packetize(sha, checks)

    if not packets:
        console.print("[green]No failing checks — nothing to packetize.[/green]")
        return

    for pkt in packets:
        tree = Tree(f"[red bold]{pkt.id}[/red bold] — {pkt.check_name}")
        tree.add(f"[dim]done_when:[/dim] {pkt.done_when}")
        tree.add(f"[dim]severity:[/dim] {pkt.severity}")
        for line in pkt.error_extract:
            tree.add(f"  {line}")
        if pkt.evidence_ptr.run:
            tree.add(f"[dim]run:[/dim] {pkt.evidence_ptr.run[:80]}")
        console.print(tree)
        console.print()


@app.command()
def run(
    pr: str = typer.Argument(..., help="PR reference"),
    config: str = typer.Option(None, "--config", "-c", help="Config JSON path"),
    max_iter: int = typer.Option(50, "--max-iter"),
    store: str = typer.Option(None, "--store", help="Checkpoint store path"),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    """Run one iteration of the canonical loop against a PR."""
    _setup_logging(verbose)
    token = _get_token()
    cfg_data = _load_config(config)

    # Build target + constraints from config or defaults
    target = TargetState(
        goal=cfg_data.get("goal", f"All required checks green on {pr}"),
        commands=cfg_data.get("commands", []),
        required_checks=cfg_data.get("required_checks", "auto-detect from PR"),
        done_when=cfg_data.get("done_when", ["All required CI checks pass"]),
    )

    constraints = Constraints(
        touch_allowlist=cfg_data.get("touch_allowlist", ["*"]),
        touch_denylist=cfg_data.get("touch_denylist", []),
        diff_budget=DiffBudget(
            max_files=cfg_data.get("max_files", 20),
            max_loc=cfg_data.get("max_loc", 500),
        ),
        refactor_policy=RefactorPolicy(
            cfg_data.get("refactor_policy", "no-refactor")
        ),
        security_policy=SecurityPolicy(
            no_disable_security_checks=cfg_data.get(
                "no_disable_security_checks", True
            ),
            actions_must_be_pinned=cfg_data.get("actions_must_be_pinned", True),
            dependencies_must_be_pinned=cfg_data.get(
                "dependencies_must_be_pinned", True
            ),
        ),
    )

    checkpoint_store = CheckpointStore(store) if store else CheckpointStore()

    engine_config = EngineConfig(
        max_iterations=max_iter,
        auto_checkpoint=True,
        checkpoint_store=checkpoint_store,
    )

    loop = CanonicalLoop(target, constraints, engine_config)

    # Run observation + iteration
    with CIOracle(token, pr) as oracle:
        sha, checks = oracle.observe()
        diff_summary = oracle.get_diff_summary()
        touched_files = oracle.get_changed_files()

    decision = loop.run_iteration(
        check_results=checks,
        sha=sha,
        pr_url=pr,
        diff_summary=diff_summary,
        touched_files=touched_files,
    )

    # Display results
    _render_decision(decision, loop)


@app.command()
def ledger(
    store: str = typer.Option(None, "--store", help="Checkpoint store path"),
    limit: int = typer.Option(20, "--limit", "-n"),
) -> None:
    """View the proof bundle ledger."""
    checkpoint_store = CheckpointStore(store) if store else CheckpointStore()
    entries = checkpoint_store.list_bundles(limit)

    if not entries:
        console.print("[dim]No entries in ledger.[/dim]")
        return

    table = Table(title="Proof Bundle Ledger")
    table.add_column("Timestamp", style="dim")
    table.add_column("Hash", style="cyan")
    table.add_column("PR")
    table.add_column("SHA", style="dim")

    for entry in entries:
        table.add_row(
            entry.get("ts", "")[:19],
            entry.get("hash", "")[:12] + "…",
            entry.get("pr", ""),
            entry.get("sha", "")[:7],
        )

    console.print(table)


@app.command()
def states(
    store: str = typer.Option(None, "--store", help="Checkpoint store path"),
) -> None:
    """List saved state snapshots."""
    checkpoint_store = CheckpointStore(store) if store else CheckpointStore()
    labels = checkpoint_store.list_states()

    if not labels:
        console.print("[dim]No state snapshots found.[/dim]")
        return

    for label in labels:
        console.print(f"  📸 {label}")


@app.command()
def verify(
    hash_prefix: str = typer.Argument(..., help="Proof bundle hash (prefix OK)"),
    store: str = typer.Option(None, "--store", help="Checkpoint store path"),
) -> None:
    """Verify a proof bundle's integrity and artifact hashes."""
    checkpoint_store = CheckpointStore(store) if store else CheckpointStore()
    bundle = checkpoint_store.load_bundle(hash_prefix)

    if bundle is None:
        console.print(f"[red]Bundle not found: {hash_prefix}[/red]")
        raise typer.Exit(1)

    console.print(Panel(
        f"[bold]PR:[/bold] {bundle.pr_url}\n"
        f"[bold]SHA:[/bold] {bundle.commit_sha}\n"
        f"[bold]All green:[/bold] {'✓' if bundle.all_green else '✗'}\n"
        f"[bold]Duration:[/bold] {bundle.time.duration_seconds or '?'}s\n"
        f"[bold]Integrity:[/bold] {bundle.integrity_hash()[:16]}…",
        title="Proof Bundle",
    ))

    # Verify artifacts
    failures = checkpoint_store.verify_bundle_artifacts(bundle)
    if failures:
        for f in failures:
            console.print(f"  [red]✗[/red] {f}")
    else:
        console.print("  [green]All artifact hashes verified.[/green]")


# ─── Rendering ────────────────────────────────────────────────────────────────

def _render_decision(decision: GovernorDecision, loop: CanonicalLoop) -> None:
    state = loop.state
    metrics = loop.metrics

    action_styles = {
        GovernorDecision.MERGE: "[bold green]MERGE[/bold green]",
        GovernorDecision.HOLD: "[bold yellow]HOLD[/bold yellow]",
        GovernorDecision.NEXT: "[bold cyan]NEXT LOOP[/bold cyan]",
        GovernorDecision.HALT: "[bold red]HALT[/bold red]",
    }

    console.print()
    console.print(Panel(
        f"[bold]Decision:[/bold] {action_styles.get(decision.action, decision.action)}\n"
        f"[bold]Reason:[/bold] {decision.reason}\n"
        f"[bold]Phase:[/bold] {state.phase.value}\n"
        f"[bold]Iteration:[/bold] {state.iteration}\n"
        f"[bold]Active packets:[/bold] {len(state.active_packets)}\n"
        f"[bold]Audit:[/bold] {state.audit_verdict.value if state.audit_verdict else 'N/A'}",
        title="DAO-LIFEBOOK — Loop Result",
    ))

    # Metrics
    m = metrics.summary()
    console.print(
        f"\n[dim]KPD: {m['kpd']} | "
        f"Closures: {m['closures']} | "
        f"Iterations: {m['total_iterations']} | "
        f"Rework: {m['r_rework']}[/dim]"
    )

    # Stop rule
    if loop.can_stop():
        console.print("\n[green bold]✓ STOP RULE MET — safe to stop.[/green bold]")


# ─── Entry point ──────────────────────────────────────────────────────────────

def main() -> None:
    app()


if __name__ == "__main__":
    main()
