import os
import sys
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from .graph_analyzer import analyze
from .llm import detect_provider, load_dotenv
from .reporter import write_critical_path, write_failure_report, write_product_overview, write_token_report
from .scanner import extract_repo_files, load_or_build_graph

console = Console()


@click.group()
def main():
    """WTFcode — graph-first failure prediction for repos you didn't write."""


@main.command()
@click.argument("repo_path", default=".", type=click.Path(exists=True, file_okay=False))
@click.option("--output-dir", "-o", default=None, help="Where to write outputs (default: <repo>/wtfcode-output)")
@click.option("--top", default=20, show_default=True, help="Number of critical files to surface")
@click.option("--no-llm", is_flag=True, help="Use graph topology only (free, no API key needed)")
@click.option("--model", default=None, help="Model to use, e.g. gpt-4o, claude-sonnet-4-5, gemini-2.5-flash, ollama/llama3.2")
def scan(repo_path: str, output_dir: str | None, top: int, no_llm: bool, model: str | None):
    """Scan a repo and produce CRITICAL_PATH.md + FAILURE_REPORT.md."""
    repo = Path(repo_path).resolve()
    out_dir = Path(output_dir).resolve() if output_dir else repo / "wtfcode-output"
    out_dir.mkdir(parents=True, exist_ok=True)

    # Load .env from repo root so users don't need to export keys manually
    load_dotenv(repo)

    console.print(f"\n[bold cyan]WTFcode scan[/bold cyan] [dim]{repo}[/dim]\n")

    with console.status("Building knowledge graph..."):
        try:
            G, graph_path = load_or_build_graph(repo)
        except Exception as e:
            console.print(f"[red]Graph build failed:[/red] {e}")
            console.print("[dim]Tip: run /graphify in Claude Code first for richer semantic graph.[/dim]")
            sys.exit(1)

    console.print(f"  Graph: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges  [dim](from {graph_path})[/dim]")

    with console.status("Ranking critical files..."):
        repo_files = extract_repo_files(G, top_n=top)

    provider_info = detect_provider()
    use_llm = not no_llm and (bool(model) or provider_info is not None)

    if not use_llm and not no_llm:
        console.print("  [yellow]No LLM API key found — running structural analysis (--no-llm mode)[/yellow]")
        console.print("  [dim]Set ANTHROPIC_API_KEY, OPENAI_API_KEY, or GEMINI_API_KEY to enable AI analysis.[/dim]")
        console.print("  [dim]Or add a .env file in the repo with your key.[/dim]")
    elif use_llm:
        display_model = model or (provider_info[1] if provider_info else "")
        console.print(f"  [dim]Model: {display_model}[/dim]")

    label = f"Generating failure scenarios..." if use_llm else "Analyzing graph topology..."
    with console.status(label):
        try:
            repo_files, scenarios, token_report, repo_intro = analyze(
                G, repo, repo_files, use_llm=use_llm, model=model
            )
        except Exception as e:
            console.print(f"[red]Analysis failed:[/red] {e}")
            sys.exit(1)

    # Write outputs
    from collections import Counter as _Counter
    _comm_counts = _Counter(
        d.get("community_name") or str(d.get("community", "?"))
        for _, d in G.nodes(data=True)
    )
    graph_stats = {
        "nodes": G.number_of_nodes(),
        "edges": G.number_of_edges(),
        "communities": sum(1 for c, n in _comm_counts.items() if n >= 5 and c != "?"),
        "cross_edge_pct": round(
            100 * sum(
                1 for u, v in G.edges()
                if (G.nodes[u].get("community_name") or str(G.nodes[u].get("community")))
                != (G.nodes[v].get("community_name") or str(G.nodes[v].get("community")))
            ) / max(G.number_of_edges(), 1)
        ),
    }
    po_path = write_product_overview(repo_intro, scenarios, out_dir, repo, graph_stats, token_report)
    cp_path = write_critical_path(repo_files, out_dir, repo)
    fr_path = write_failure_report(scenarios, out_dir, repo, token_report, repo_intro)
    tr_path = write_token_report(token_report, out_dir)

    # Copy graph.json into wtfcode-output
    import shutil
    shutil.copy(graph_path, out_dir / "graph.json")

    # Print summary
    console.print("\n[bold green]Done.[/bold green] Outputs:\n")
    cwd = Path.cwd()
    for p in [po_path, fr_path, cp_path, tr_path, out_dir / "graph.json"]:
        try:
            label = p.relative_to(cwd)
        except ValueError:
            label = p
        console.print(f"  {label}")

    _print_token_savings(token_report)
    _print_top_failures(scenarios)


def _print_token_savings(report: dict):
    ratio = report["savings_ratio"]
    naive = report["naive_tokens"]
    wtfcode = report["wtfcode_input_tokens"]

    console.print(f"\n[bold]Token discipline[/bold]")
    console.print(f"  Naive (read all files):  [red]{naive:,}[/red] tokens")
    console.print(f"  WTFcode (graph summary): [green]{wtfcode:,}[/green] tokens")
    console.print(f"  Savings ratio:           [bold green]{ratio}x[/bold green]\n")


def _print_top_failures(scenarios):
    if not scenarios:
        return

    table = Table(title="Top failure scenarios", show_lines=True, min_width=72)
    table.add_column("#", style="dim", width=3)
    table.add_column("Scenario", style="bold", min_width=30)
    table.add_column("Sev", justify="center", width=7)
    table.add_column("If this breaks", min_width=34)

    severity_color = {"high": "red", "medium": "yellow", "low": "green"}
    for i, s in enumerate(scenarios[:5], 1):
        color = severity_color.get(s.severity, "white")
        # Use consequence (user-facing outage story) — it's already 1 sentence
        impact = s.consequence or s.trigger
        # Clean to first sentence only
        first_sentence = impact.split(".")[0].strip()
        table.add_row(str(i), s.title, f"[{color}]{s.severity}[/{color}]", first_sentence)

    console.print(table)
    console.print("  [dim]Full report: wtfcode-output/FAILURE_REPORT.md[/dim]\n")
