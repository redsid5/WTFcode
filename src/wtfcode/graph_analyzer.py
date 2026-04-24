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

import networkx as nx

from .llm import call_llm
from .models import FailureScenario, RepoFile
from .scanner import extract_repo_files

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


def _clean_label(G: nx.Graph, node_id: str) -> str:
    data = G.nodes[node_id]
    raw = data.get("label", node_id)
    src = Path(data.get("source_file", "") or "").name or "?"
    is_docstring = len(raw) > 50 or "\n" in raw or raw.startswith("`")
    return src if is_docstring else raw


def _build_repo_intro(G: nx.Graph, repo_files: list[RepoFile]) -> list[str]:
    """
    Build a 3-5 bullet 'how this works in 60 seconds' from graph structure.
    Derives from community sizes, god nodes, and cross-community edges.
    Handles both community_name (full graphify run) and community int (AST-only run).
    """
    from collections import Counter

    # Determine community key: prefer community_name, fall back to int community
    use_name = any(
        data.get("community_name") and data.get("community_name") != "?"
        for _, data in G.nodes(data=True)
    )

    def _community_key(data: dict) -> str:
        if use_name:
            return data.get("community_name", "?")
        return str(data.get("community", "?"))

    def _community_label(key: str, member_nodes: list) -> str:
        """Derive a readable label from dominant source files when name is an int ID."""
        if use_name:
            return key
        file_counter: Counter = Counter()
        for nid in member_nodes:
            stem = Path(G.nodes[nid].get("source_file", "") or "").stem
            if stem:
                file_counter[stem] += 1
        top = [f for f, _ in file_counter.most_common(2)]
        return " / ".join(top) if top else f"module-{key}"

    # Group nodes by community
    community_members: dict[str, list] = {}
    for nid, data in G.nodes(data=True):
        key = _community_key(data)
        community_members.setdefault(key, []).append(nid)

    top_communities = sorted(community_members.items(), key=lambda x: len(x[1]), reverse=True)[:5]

    # God nodes (top 3 by degree)
    top_nodes = sorted(G.degree(), key=lambda x: x[1], reverse=True)[:3]
    god_labels = [_clean_label(G, nid) for nid, _ in top_nodes]
    god_degrees = [deg for _, deg in top_nodes]

    bullets: list[str] = []

    # Bullet 1: god nodes = the load-bearing spine
    bullets.append(
        f"Load-bearing spine: {', '.join(god_labels)} "
        f"(degree {god_degrees[0]}, {god_degrees[1]}, {god_degrees[2]}) — "
        "break any of these and the system cascades."
    )

    # Bullets 2-5: top communities as architectural layers
    for key, members in top_communities[:4]:
        label = _community_label(key, members)
        bullets.append(f"{label} layer — {len(members)} nodes")

    # Final bullet: cross-community coupling signal
    cross = sum(
        1 for u, v in G.edges()
        if _community_key(G.nodes[u]) != _community_key(G.nodes[v])
    )
    total_edges = G.number_of_edges()
    pct = round(100 * cross / total_edges) if total_edges else 0
    coupling = "tightly interlocked — changes ripple far" if pct >= 30 else "reasonably isolated — changes stay local"
    bullets.append(
        f"Cross-layer coupling: {cross}/{total_edges} edges cross module boundaries ({pct}%) — {coupling}."
    )

    return bullets


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
        src = Path(data.get("source_file", "") or "").name or nid
        label = _clean_label(G, nid)
        neighbors = list(G.neighbors(nid))
        seen_labels: set[str] = set()
        neighbor_labels: list[str] = []
        for n in neighbors:
            lbl = _clean_label(G, n)
            # skip bare method names like .__init__() — meaningless without class context
            if lbl.startswith(".") or not lbl:
                continue
            if lbl not in seen_labels:
                seen_labels.add(lbl)
                neighbor_labels.append(lbl)
            if len(neighbor_labels) >= 6:
                break

        neighbor_communities = {G.nodes[n].get("community_name", "?") for n in neighbors}
        n_communities = len(neighbor_communities)

        is_file_node = label == src or label.endswith(".py") or label.endswith(".ts") or label.endswith(".js")

        if degree >= 40:
            smell = "single point of failure"
            why = f"Centralized control: {degree} nodes depend on it, making every caller a victim of one change."
            if is_file_node:
                vibe = (
                    f"Treat {label} as read-only. "
                    f"If you must change it, grep every caller first — there are {degree} of them."
                )
            else:
                vibe = (
                    f"Never edit {label} directly — wrap or subclass it instead. "
                    f"If you must change it, grep for every caller first — there are {degree} of them."
                )
        elif n_communities >= 4:
            smell = "high coupling"
            why = f"Connects {n_communities} distinct subsystems (approx) — changes in {src} bleed across unrelated layers."
            vibe = (
                f"If you touch {src}, run integration tests across all subsystems it connects. "
                "Don't add new responsibilities here — create a separate module."
            )
        elif degree >= 10:
            smell = "hidden dependency chain"
            why = f"Deep convergence: {degree} nodes route through this with no isolation layer between them."
            vibe = (
                f"Trace the full call chain before changing {label}. "
                "Any interface change silently cascades — there is no safety net between callers."
            )
        else:
            continue  # degree < 10 and spans < 4 subsystems — not structurally significant in v1

        severity = "high" if degree >= 20 else "medium" if degree >= 8 else "low"
        title = label if label == src else f"{label} ({src})"
        scenarios.append(FailureScenario(
            title=title,
            trigger=f"{label} in {src} breaks or changes its interface. {degree} nodes depend on it.",
            downstream=neighbor_labels,
            severity=severity,
            likelihood="medium",
            consequence=f"{degree} dependents fail. Blast radius includes {', '.join(neighbor_labels[:2])}.",
            mitigation=f"Add a contract test for {label} so callers fail fast on interface changes.",
            why_this_happens=why,
            system_smell=smell,
            how_to_vibe_safely=vibe,
        ))
        if len(scenarios) == 5:
            break

    return scenarios


def top_node_risk_share(repo_files: list[RepoFile], top_n: int = 3, pool_n: int = 20) -> int:
    """Structural risk share of top_n nodes vs top pool_n nodes. Returns integer percentage."""
    pool = repo_files[:pool_n]
    top = repo_files[:top_n]
    pool_sum = sum(f.degree for f in pool)
    top_sum = sum(f.degree for f in top)
    return round(100 * top_sum / pool_sum) if pool_sum else 0


def analyze(
    G: nx.Graph,
    repo_path: Path,
    repo_files: list[RepoFile] | None = None,
    use_llm: bool = True,
    model: str | None = None,
) -> tuple[list[RepoFile], list[FailureScenario], dict, list[str]]:
    """
    Core analysis: critical path ranking + failure scenario generation.

    Returns:
        repo_files:   ranked list of RepoFile (sorted by fragility)
        scenarios:    list of FailureScenario
        token_report: dict with naive_tokens, wtfcode_tokens, savings_ratio
        repo_intro:   list of bullet strings — 60-second system overview
    """
    if repo_files is None:
        repo_files = extract_repo_files(G)

    naive_tokens = _estimate_naive_tokens(repo_path)
    repo_intro = _build_repo_intro(G, repo_files)

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
            "method": "graph topology only — set any LLM API key for AI analysis",
        }
        return repo_files, scenarios, token_report, repo_intro

    compact_summary = _build_compact_summary(G, repo_files)

    prompt = f"""You are a senior engineer who has been paged at 3am because something broke.
You are analyzing a codebase's failure risk from its knowledge graph.
Answer only from the graph. Do not read raw files.

{compact_summary}

Produce exactly this JSON and nothing else:
{{
  "repo_intro": {{
    "summary": "1 sentence: this repo is basically X entrypoint -> Y routing -> Z data/auth layer",
    "bullets": [
      "3 to 5 bullets describing how the system is wired, at the architecture level",
      "Each bullet max 15 words. No code jargon. Name real modules from the graph."
    ]
  }},
  "scenarios": [
    {{
      "title": "short name, max 6 words",
      "trigger": "1 sentence: exactly what breaks and why. Name the node. Be specific.",
      "downstream": ["exact node names from the graph that break next"],
      "severity": "high|medium|low",
      "likelihood": "high|medium|low",
      "consequence": "1 sentence: what the user experiences when this fails. No jargon.",
      "mitigation": "1 concrete action a developer can do today. Name a specific file or test.",
      "why_this_happens": "1 sentence (max 18 words): what structural property makes this failure likely. Use one of: single point of failure, high coupling, hidden dependency chain.",
      "system_smell": "single point of failure|high coupling|hidden dependency chain",
      "how_to_vibe_safely": "2 sentences: what a developer must check before touching this. First: what not to do. Second: the safer pattern."
    }}
  ]
}}

Rules:
- Exactly 5 scenarios, ordered worst-first.
- severity=high only if 3+ downstream nodes break.
- consequence must sound like a real outage.
- mitigation must name a specific file or action, not generic advice.
- how_to_vibe_safely must reference architecture, not individual lines.
- No preamble, no markdown fences, only the JSON object."""

    raw_response, model_used = call_llm(prompt, model=model)

    wtfcode_input_tokens = len(prompt) // 4
    wtfcode_output_tokens = len(raw_response) // 4

    raw = raw_response.strip()
    # Strip accidental markdown fences
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    parsed = json.loads(raw)

    # Use LLM repo_intro if available, fall back to structural
    llm_intro = parsed.get("repo_intro", {})
    if llm_intro.get("bullets"):
        repo_intro = llm_intro["bullets"]
        summary = llm_intro.get("summary", "")
        if summary:
            repo_intro = [summary] + repo_intro

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
            why_this_happens=s.get("why_this_happens", ""),
            system_smell=s.get("system_smell", ""),
            how_to_vibe_safely=s.get("how_to_vibe_safely", ""),
        ))

    savings_ratio = round(naive_tokens / wtfcode_input_tokens, 1) if wtfcode_input_tokens else 0

    token_report = {
        "naive_tokens": naive_tokens,
        "wtfcode_input_tokens": wtfcode_input_tokens,
        "wtfcode_output_tokens": wtfcode_output_tokens,
        "savings_ratio": savings_ratio,
        "model": model_used,
        "method": "compact graph summary (top 20 nodes by degree)",
    }

    return repo_files, scenarios, token_report, repo_intro
