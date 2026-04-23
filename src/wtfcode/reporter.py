"""Writes CRITICAL_PATH.md, FAILURE_REPORT.md, and tokens_saved.json."""

import json
from pathlib import Path

from .models import FailureScenario, RepoFile


def write_critical_path(
    repo_files: list[RepoFile],
    output_dir: Path,
    repo_path: Path,
) -> Path:
    lines = [
        f"# Critical Path Map — `{repo_path.name}`\n",
        "Ranked by dependency degree. Higher = more things break if this changes.\n",
    ]

    critical = [f for f in repo_files if f.is_critical]
    rest = [f for f in repo_files if not f.is_critical]

    lines.append("## Load-bearing nodes\n")
    for f in critical:
        bar = "#" * int(f.fragility_score * 10)
        lines.append(f"- **{f.path}** `{bar}` fragility={f.fragility_score} degree={f.degree}")
        lines.append(f"  community: {f.community}")
        if f.connections:
            lines.append(f"  connects to: {', '.join(f.connections[:5])}")
        lines.append("")

    if rest:
        lines.append(f"## Other nodes ({len(rest)} total)\n")
        for f in rest[:10]:
            lines.append(f"- {f.path} (degree={f.degree})")
        if len(rest) > 10:
            lines.append(f"- ... and {len(rest) - 10} more")

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


def write_token_report(token_report: dict, output_dir: Path) -> Path:
    out = output_dir / "tokens_saved.json"
    out.write_text(json.dumps(token_report, indent=2), encoding="utf-8")
    return out
