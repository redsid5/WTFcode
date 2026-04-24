import os
import sys
from pathlib import Path

import click
from rich.console import Console

from .graph_analyzer import analyze, top_node_risk_share
from .llm import detect_provider, load_dotenv
from .reporter import write_critical_path, write_easy_overview, write_failure_report, write_product_overview, write_token_report
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

    label = "Generating failure scenarios..." if use_llm else "Analyzing graph topology..."
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
    eo_path = write_easy_overview(repo_intro, scenarios, graph_stats, out_dir, repo)
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
    for p in [eo_path, po_path, fr_path, cp_path, tr_path, out_dir / "graph.json"]:
        try:
            label = p.relative_to(cwd)
        except ValueError:
            label = p
        console.print(f"  {label}")

    _print_risk_summary(repo_files, token_report)


def _print_risk_summary(repo_files, token_report: dict):
    pct = top_node_risk_share(repo_files)
    ratio = token_report["savings_ratio"]
    naive = token_report["naive_tokens"]
    wtfcode = token_report["wtfcode_input_tokens"]

    console.print(f"\n  [bold]Top 3 nodes drive ~{pct}% of structural risk:[/bold]")
    for i, f in enumerate(repo_files[:3], 1):
        console.print(f"    {i}. [cyan]{f.path:<42}[/cyan] [dim]{f.degree} dependents[/dim]")

    console.print(f"\n  [dim]Token compression: {naive:,} → {wtfcode:,} ({ratio}x)[/dim]\n")
