"""
Repo scanner: runs graphify extraction on a target repo and returns parsed graph data.

Prefers an existing graphify-out/graph.json if present (respects the --update workflow).
Falls back to running the graphify Python API directly (AST-only for code files, no LLM cost).
For full semantic extraction (docs, images), the user should run /graphify first.
"""

import json
import subprocess
import sys
from pathlib import Path

import networkx as nx
from networkx.readwrite import json_graph

from .models import RepoFile


def _run_ast_extraction(repo_path: Path, graph_path: Path) -> None:
    """Run graphify's AST extractor directly (no LLM, free)."""
    script = f"""
import json, sys
from graphify.detect import detect
from graphify.extract import collect_files, extract
from graphify.build import build_from_json
from graphify.cluster import cluster
from graphify.export import to_json
from pathlib import Path

repo = Path({str(repo_path)!r})
detection = detect(repo)
code_files = [Path(f) for f in detection["files"].get("code", [])]

if not code_files:
    print("no-code-files", file=sys.stderr)
    sys.exit(0)

all_files = []
for f in code_files:
    all_files.extend([f] if f.is_file() else list(f.rglob("*")))

result = extract([f for f in all_files if f.is_file()])
G = build_from_json(result)
communities = cluster(G)
Path({str(graph_path.parent)!r}).mkdir(parents=True, exist_ok=True)
to_json(G, communities, {str(graph_path)!r})
print(f"AST: {{G.number_of_nodes()}} nodes, {{G.number_of_edges()}} edges")
"""
    subprocess.run([sys.executable, "-c", script], check=True)


def load_or_build_graph(repo_path: Path) -> tuple[nx.Graph, Path]:
    """
    Return (graph, graph_json_path).
    Uses existing graphify-out/graph.json if present; otherwise runs AST extraction.
    """
    existing = repo_path / "graphify-out" / "graph.json"
    wtfcode_out = repo_path / "wtfcode-output"
    fallback = wtfcode_out / "graph.json"

    if existing.exists():
        graph_path = existing
    elif fallback.exists():
        graph_path = fallback
    else:
        fallback.parent.mkdir(parents=True, exist_ok=True)
        _run_ast_extraction(repo_path, fallback)
        graph_path = fallback

    data = json.loads(graph_path.read_text(encoding="utf-8"))
    G = json_graph.node_link_graph(data, edges="links")
    return G, graph_path


def extract_repo_files(G: nx.Graph, top_n: int = 20) -> list[RepoFile]:
    """Return RepoFile list sorted by degree (highest = most critical)."""
    files: list[RepoFile] = []
    for node_id, data in G.nodes(data=True):
        degree = G.degree(node_id)
        neighbors = [
            G.nodes[n].get("label", n)
            for n in G.neighbors(node_id)
        ]
        raw_src = data.get("source_file", "") or node_id
        # Use relative filename only — absolute paths are noisy in reports
        src = Path(raw_src).name if raw_src else node_id
        label = data.get("label", src)
        files.append(RepoFile(
            path=f"{src}::{label}" if label != src else src,
            degree=degree,
            community=data.get("community_name", str(data.get("community", "unknown"))),
            connections=neighbors[:10],
        ))

    files.sort(key=lambda f: f.degree, reverse=True)

    # Mark top_n as critical
    for f in files[:top_n]:
        f.is_critical = True

    # Fragility score: normalized degree (higher degree = more dependents = more fragile)
    max_degree = files[0].degree if files else 1
    for f in files:
        f.fragility_score = round(f.degree / max_degree, 2)

    return files
