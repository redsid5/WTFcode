"""
Benchmark: naive Claude vs WTFcode token usage on a target repo.

Usage:
    python scripts/measure_tokens.py <repo_path>

Prints a comparison table showing how much WTFcode saves vs reading raw files.
"""

import json
import sys
from pathlib import Path

EXTENSIONS = {
    ".py", ".ts", ".js", ".go", ".rs", ".java",
    ".c", ".cpp", ".md", ".txt", ".json", ".yaml", ".yml",
}


def count_raw_tokens(repo_path: Path) -> dict:
    total_chars = 0
    file_count = 0
    for p in repo_path.rglob("*"):
        if p.is_file() and p.suffix in EXTENSIONS:
            try:
                chars = len(p.read_text(encoding="utf-8", errors="ignore"))
                total_chars += chars
                file_count += 1
            except OSError:
                pass
    return {
        "files": file_count,
        "chars": total_chars,
        "tokens_est": total_chars // 4,
    }


def count_graph_tokens(graph_path: Path) -> dict:
    data = json.loads(graph_path.read_text(encoding="utf-8"))
    nodes = data.get("nodes", [])
    links = data.get("links", [])

    # Simulate the compact summary WTFcode sends to Claude
    lines = []
    sorted_nodes = sorted(nodes, key=lambda n: n.get("degree", 0), reverse=True)[:20]
    node_ids = {n["id"] for n in sorted_nodes}

    for n in sorted_nodes:
        lines.append(
            f"NODE {n.get('label', n['id'])} "
            f"[src={n.get('source_file', '?')} degree={n.get('degree', 0)}]"
        )

    for e in links:
        if e.get("source") in node_ids and e.get("target") in node_ids:
            lines.append(
                f"EDGE {e.get('source', '?')} --{e.get('relation', '?')}--> {e.get('target', '?')}"
            )

    summary = "\n".join(lines)
    tokens = len(summary) // 4
    return {
        "nodes": len(nodes),
        "edges": len(links),
        "compact_nodes": len(sorted_nodes),
        "chars": len(summary),
        "tokens_est": tokens,
    }


def main():
    if len(sys.argv) < 2:
        print(f"Usage: python {sys.argv[0]} <repo_path>")
        sys.exit(1)

    repo_path = Path(sys.argv[1]).resolve()
    graph_path = repo_path / "graphify-out" / "graph.json"
    if not graph_path.exists():
        graph_path = repo_path / "wtfcode-output" / "graph.json"
    if not graph_path.exists():
        print(f"No graph.json found in {repo_path}. Run wtfcode scan first.")
        sys.exit(1)

    raw = count_raw_tokens(repo_path)
    graph = count_graph_tokens(graph_path)
    ratio = round(raw["tokens_est"] / graph["tokens_est"], 1) if graph["tokens_est"] else 0

    print(f"\nToken benchmark: {repo_path.name}")
    print(f"{'─' * 50}")
    print(f"  Naive (read all {raw['files']} files):   {raw['tokens_est']:>8,} tokens")
    print(f"  WTFcode (compact graph, top 20 nodes): {graph['tokens_est']:>8,} tokens")
    print(f"  Savings ratio:                         {ratio:>8}x")
    print(f"  Graph: {graph['nodes']} nodes, {graph['edges']} edges → {graph['compact_nodes']} critical nodes in prompt")

    output = {
        "repo": str(repo_path),
        "naive_tokens": raw["tokens_est"],
        "wtfcode_tokens": graph["tokens_est"],
        "savings_ratio": ratio,
        "naive_files": raw["files"],
        "graph_nodes": graph["nodes"],
        "graph_edges": graph["edges"],
    }

    out_path = repo_path / "wtfcode-output" / "tokens_benchmark.json"
    out_path.parent.mkdir(exist_ok=True)
    out_path.write_text(json.dumps(output, indent=2))
    print(f"\n  Saved to {out_path}")


if __name__ == "__main__":
    main()
