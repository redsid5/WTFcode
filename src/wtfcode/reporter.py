"""Writes PRODUCT_OVERVIEW.md, CRITICAL_PATH.md, FAILURE_REPORT.md, and tokens_saved.json."""

import json
from collections import defaultdict
from pathlib import Path

from .models import FailureScenario, RepoFile


def _clean_connection(label: str) -> str | None:
    """Return None if label looks like a docstring (should be skipped)."""
    if len(label) > 60 or "\n" in label or label.startswith("`"):
        return None
    return label.strip()


def _why_it_matters(f: RepoFile) -> str:
    d = f.degree
    if d >= 40:
        return f"Single point of failure — {d} nodes depend on this. Any interface change is system-wide."
    if d >= 20:
        return f"Load-bearing across {len(f.connections)} downstream chains — changes here ripple broadly."
    if d >= 10:
        return f"Critical convergence point — {d} callers route through this with no isolation layer."
    return f"Notable dependency — {d} nodes rely on this within the {f.community} layer."


def write_critical_path(
    repo_files: list[RepoFile],
    output_dir: Path,
    repo_path: Path,
) -> Path:
    lines = [
        f"# Critical Path Map — `{repo_path.name}`\n",
        "> Don't touch these casually. Ranked by dependency degree — higher = more things break if this changes.\n",
        "---\n",
    ]

    critical = [f for f in repo_files if f.is_critical]
    rest = [f for f in repo_files if not f.is_critical]

    lines.append("## Load-bearing nodes\n")
    for f in critical:
        lines.append(f"### `{f.path}`")
        lines.append(f"**Why it matters:** {_why_it_matters(f)}\n")
        lines.append(f"- Fragility score: `{f.fragility_score}` | Degree: `{f.degree}` | Layer: {f.community}")
        clean_conns = [c for raw in f.connections if (c := _clean_connection(raw)) is not None]
        if clean_conns:
            lines.append(f"- Connects to: {', '.join(clean_conns[:5])}")
        lines.append("")

    if rest:
        lines.append(f"---\n\n## Watch list ({len(rest)} nodes)\n")
        for f in rest[:10]:
            lines.append(f"- `{f.path}` — degree {f.degree}, {f.community} layer")
        if len(rest) > 10:
            lines.append(f"- _...and {len(rest) - 10} more_")

    out = output_dir / "CRITICAL_PATH.md"
    out.write_text("\n".join(lines), encoding="utf-8")
    return out


def write_failure_report(
    scenarios: list[FailureScenario],
    output_dir: Path,
    repo_path: Path,
    token_report: dict | None = None,
    repo_intro: list[str] | None = None,
) -> Path:
    severity_order = {"high": 0, "medium": 1, "low": 2}
    scenarios = sorted(scenarios, key=lambda s: severity_order.get(s.severity, 1))

    savings = token_report.get("savings_ratio", "?") if token_report else "?"
    naive = token_report.get("naive_tokens", 0) if token_report else 0
    wtf = token_report.get("wtfcode_input_tokens", 0) if token_report else 0

    lines = [
        f"# WTFcode Failure Report — `{repo_path.name}`\n",
        f"> Scanned {repo_path.name} in {wtf:,} tokens vs {naive:,} naive ({savings}x savings)\n",
        "---\n",
    ]

    # Section 1: How this works in 60 seconds
    if repo_intro:
        lines.append("## How this works (60 seconds)\n")
        for bullet in repo_intro:
            lines.append(f"- {bullet}")
        lines.append("\n---\n")

    # Section 2: Where it's weak
    lines.append("## Where it's weak\n")

    for i, s in enumerate(scenarios, 1):
        severity_label = {"high": "CRITICAL", "medium": "WARNING", "low": "WATCH"}.get(s.severity, s.severity.upper())
        lines.append(f"### {i}. {s.title}")
        lines.append(f"**[{severity_label}]** — likelihood: {s.likelihood}\n")

        lines.append(f"**What breaks:** {s.trigger}\n")

        if s.why_this_happens:
            smell_tag = f" `{s.system_smell}`" if s.system_smell else ""
            lines.append(f"**Why this happens:**{smell_tag} {s.why_this_happens}\n")

        if s.downstream:
            lines.append("**Blast radius:**")
            for d in s.downstream:
                label = d.strip().split("\n")[0][:80]
                lines.append(f"  - `{label}`")
            lines.append("")

        if s.consequence:
            lines.append(f"**What your users see:** {s.consequence}\n")

        if s.mitigation:
            lines.append(f"**Fix it:** {s.mitigation}\n")

        # Section 3 (per scenario): How to vibe safely
        if s.how_to_vibe_safely:
            lines.append(f"**How to vibe safely:** {s.how_to_vibe_safely}\n")

        lines.append("---\n")

    out = output_dir / "FAILURE_REPORT.md"
    out.write_text("\n".join(lines), encoding="utf-8")
    return out


def write_product_overview(
    repo_intro: list[str],
    scenarios: list[FailureScenario],
    output_dir: Path,
    repo_path: Path,
    graph_stats: dict,
    token_report: dict | None = None,
) -> Path:
    savings = token_report.get("savings_ratio", "?") if token_report else "?"
    wtf = token_report.get("wtfcode_input_tokens", 0) if token_report else 0
    naive = token_report.get("naive_tokens", 0) if token_report else 0

    n_nodes = graph_stats.get("nodes", 0)
    n_edges = graph_stats.get("edges", 0)
    n_layers = graph_stats.get("communities", 0)
    cross_pct = graph_stats.get("cross_edge_pct", 0)

    # Aggregate system smells across scenarios
    smell_nodes: dict[str, list[str]] = defaultdict(list)
    for s in scenarios:
        if s.system_smell:
            smell_nodes[s.system_smell].append(s.title.split(" (")[0])

    smell_descriptions = {
        "single point of failure": "Central control points — any change propagates to every caller with no isolation layer.",
        "high coupling": "Module bridges multiple architectural layers — changes in one layer bleed into others.",
        "hidden dependency chain": "Deep call convergence — no isolation between callers and this node.",
        "overloaded module": "Too many responsibilities in one place — callers absorb unrelated internal changes.",
    }

    lines = [
        f"# Product Overview — `{repo_path.name}`\n",
        f"> WTFcode structural analysis — {wtf:,} tokens vs {naive:,} naive ({savings}x savings)\n",
        "---\n",
        "## What this is\n",
    ]

    # Derive a 1-sentence summary from graph stats + god nodes
    if repo_intro:
        spine_bullet = next((b for b in repo_intro if "Load-bearing spine" in b), "")
        if spine_bullet:
            spine_names = spine_bullet.split(":")[1].split("(")[0].strip()
            lines.append(
                f"Codebase with {n_nodes} nodes across {n_layers} architectural layers, "
                f"wired through **{spine_names}** as load-bearing central points.\n"
            )
        else:
            lines.append(
                f"Codebase with {n_nodes} nodes, {n_edges} edges, "
                f"and {n_layers} architectural layers.\n"
            )

    lines.append("## How it's wired\n")
    for bullet in repo_intro:
        lines.append(f"- {bullet}")
    lines.append("")

    if smell_nodes:
        lines.append("\n## System smells present\n")
        for smell, nodes in smell_nodes.items():
            desc = smell_descriptions.get(smell, "")
            lines.append(f"- **`{smell}`** — affects: {', '.join(nodes)}")
            if desc:
                lines.append(f"  {desc}")
        lines.append("")

    lines.append("\n## Structural stats\n")
    lines.append(f"- {n_nodes:,} nodes, {n_edges:,} edges")
    lines.append(f"- {n_layers} architectural layers")
    lines.append(f"- {cross_pct}% cross-layer coupling")
    fragile = sum(1 for s in scenarios if s.severity == "high")
    lines.append(f"- {fragile} high-severity fragility hotspots")
    lines.append(f"\n_Full details: FAILURE_REPORT.md_\n")

    out = output_dir / "PRODUCT_OVERVIEW.md"
    out.write_text("\n".join(lines), encoding="utf-8")
    return out


def write_token_report(token_report: dict, output_dir: Path) -> Path:
    out = output_dir / "tokens_saved.json"
    out.write_text(json.dumps(token_report, indent=2), encoding="utf-8")
    return out
