"""
Graph-first failure analyzer.

Token discipline (CLAUDE.md rules encoded here):
  1. Build a compact graph summary — never pass raw files to the LLM.
  2. Pass only critical nodes + their edges (top ~20 by degree).
  3. One focused prompt per analysis pass; no follow-up re-reads.
  4. Track input tokens explicitly so token savings are measurable.

The compact summary is the "context block" that Claude reasons over.
Raw file reads are forbidden in this module.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from google import genai
import networkx as nx

from .models import FailureScenario, RepoFile
from .scanner import extract_repo_files

MODEL = "gemini-2.5-flash"
MAX_NODES_IN_PROMPT = 20


def _build_compact_summary(G: nx.Graph, repo_files: list[RepoFile]) -> str:
    """
    Serialize the critical subgraph as plain text — not the full graph.
    Only top MAX_NODES_IN_PROMPT nodes by degree + their edges.

    This is the primary token compression step. A 1000-node graph
    becomes ~800 tokens instead of ~40,000 tokens.
    """
    critical_ids = {
        node_id
        for node_id, _ in sorted(
            G.degree(), key=lambda x: x[1], reverse=True
        )[:MAX_NODES_IN_PROMPT]
    }

    lines = ["# Critical subgraph (top nodes by dependency degree)\n"]

    for node_id in critical_ids:
        data = G.nodes[node_id]
        raw_label = data.get("label", node_id)
        src_file = Path(data.get("source_file", "") or "").name or "?"
        # Use filename when label is a docstring (long, has newlines, or starts with backtick)
        is_docstring = len(raw_label) > 50 or "\n" in raw_label or raw_label.startswith("`")
        label = src_file if is_docstring else raw_label
        degree = G.degree(node_id)
        community = data.get("community_name", "?")
        lines.append(f"NODE {label} [src={src_file} degree={degree} community={community}]")

    lines.append("\n# Edges between critical nodes\n")
    for u, v, edata in G.edges(data=True):
        if u in critical_ids and v in critical_ids:
            rel = edata.get("relation", "?")
            conf = edata.get("confidence", "?")
            u_label = G.nodes[u].get("label", u)
            v_label = G.nodes[v].get("label", v)
            lines.append(f"EDGE {u_label} --{rel} [{conf}]--> {v_label}")

    return "\n".join(lines)


def _estimate_naive_tokens(repo_path: Path) -> int:
    """
    Estimate how many tokens a naive 'read every file' approach would cost.
    Uses ~4 chars/token as the standard estimate.
    """
    total_chars = 0
    for p in repo_path.rglob("*"):
        if p.is_file() and p.suffix in {
            ".py", ".ts", ".js", ".go", ".rs", ".java",
            ".c", ".cpp", ".md", ".txt", ".json", ".yaml", ".yml",
        }:
            try:
                total_chars += len(p.read_text(encoding="utf-8", errors="ignore"))
            except OSError:
                pass
    return total_chars // 4


def _structural_scenarios(G: nx.Graph, repo_files: list[RepoFile]) -> list[FailureScenario]:
    """
    Generate failure scenarios from graph topology alone — no LLM needed.
    Works directly from the graph: top nodes by degree, their neighbors as blast radius.
    """
    top_nodes = sorted(G.degree(), key=lambda x: x[1], reverse=True)[:10]
    scenarios: list[FailureScenario] = []

    for nid, degree in top_nodes:
        if degree < 2:
            continue
        data = G.nodes[nid]
        label = data.get("label", nid)
        src = Path(data.get("source_file", "") or "").name or nid
        neighbors = list(G.neighbors(nid))
        neighbor_labels = [G.nodes[n].get("label", n) for n in neighbors[:6]]

        severity = "high" if degree >= 20 else "medium" if degree >= 8 else "low"
        fragility = round(degree / (top_nodes[0][1] or 1), 2)
        scenarios.append(FailureScenario(
            title=f"{label} ({src})",
            trigger=f"{label} in {src} breaks or changes its interface. {degree} nodes depend on it.",
            downstream=neighbor_labels,
            severity=severity,
            likelihood="medium",
            consequence=f"{degree} dependents fail. Blast radius includes {', '.join(neighbor_labels[:2])}.",
            mitigation=f"Add a contract test for {label} so callers fail fast on interface changes.",
        ))
        if len(scenarios) == 5:
            break

    return scenarios


def analyze(
    G: nx.Graph,
    repo_path: Path,
    repo_files: list[RepoFile] | None = None,
    use_llm: bool = True,
) -> tuple[list[RepoFile], list[FailureScenario], dict]:
    """
    Core analysis: critical path ranking + failure scenario generation.

    Returns:
        repo_files:        ranked list of RepoFile (sorted by fragility)
        scenarios:         list of FailureScenario
        token_report:      dict with naive_tokens, wtfcode_tokens, savings_ratio
    """
    if repo_files is None:
        repo_files = extract_repo_files(G)

    naive_tokens = _estimate_naive_tokens(repo_path)

    if not use_llm:
        scenarios = _structural_scenarios(G, repo_files)
        compact_chars = len(_build_compact_summary(G, repo_files))
        graph_tokens = compact_chars // 4
        token_report = {
            "naive_tokens": naive_tokens,
            "wtfcode_input_tokens": graph_tokens,
            "wtfcode_output_tokens": 0,
            "savings_ratio": round(naive_tokens / graph_tokens, 1) if graph_tokens else 0,
            "model": "structural (no LLM)",
            "method": "graph topology only — set ANTHROPIC_API_KEY for Claude analysis",
        }
        return repo_files, scenarios, token_report

    compact_summary = _build_compact_summary(G, repo_files)

    prompt = f"""You are a senior engineer who has been paged at 3am because something broke.
You are analyzing a codebase's failure risk from its knowledge graph.
Answer only from the graph. Do not read raw files.

{compact_summary}

Produce exactly this JSON and nothing else:
{{
  "scenarios": [
    {{
      "title": "short name, max 6 words",
      "trigger": "1 sentence: exactly what breaks and why. Name the node. Be specific.",
      "downstream": ["exact node names from the graph that break next"],
      "severity": "high|medium|low",
      "likelihood": "high|medium|low",
      "consequence": "1 sentence: what the user experiences when this fails. No jargon. E.g. 'Every API route returns 500. Users can't log in. Your on-call phone rings.'",
      "mitigation": "1 concrete action a developer can do today. Not 'add tests'. E.g. 'Pin the HTTPException interface with a contract test in test_exceptions.py.'"
    }}
  ]
}}

Rules:
- Exactly 5 scenarios, ordered worst-first.
- severity=high only if 3+ downstream nodes break.
- consequence must sound like a real outage, not an academic description.
- mitigation must be a specific file or action, not generic advice.
- No preamble, no markdown fences, only the JSON object."""

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not set. Run: $env:GEMINI_API_KEY='your-key-here'")

    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model=MODEL,
        contents=prompt,
    )

    wtfcode_input_tokens = len(prompt) // 4
    wtfcode_output_tokens = len(response.text) // 4

    raw = response.text.strip()
    # Strip accidental markdown fences
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    parsed = json.loads(raw)

    scenarios: list[FailureScenario] = []
    for s in parsed.get("scenarios", []):
        scenarios.append(FailureScenario(
            title=s.get("title", ""),
            trigger=s.get("trigger", ""),
            downstream=s.get("downstream", []),
            severity=s.get("severity", "medium"),
            likelihood=s.get("likelihood", "medium"),
            consequence=s.get("consequence", ""),
            mitigation=s.get("mitigation", ""),
        ))

    savings_ratio = round(naive_tokens / wtfcode_input_tokens, 1) if wtfcode_input_tokens else 0

    token_report = {
        "naive_tokens": naive_tokens,
        "wtfcode_input_tokens": wtfcode_input_tokens,
        "wtfcode_output_tokens": wtfcode_output_tokens,
        "savings_ratio": savings_ratio,
        "model": MODEL,
        "method": "compact graph summary (top 20 nodes by degree)",
    }

    return repo_files, scenarios, token_report
