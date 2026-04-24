# v0.1.0 — First release

WTFcode turns a repo into a graph, then shows what breaks first and why.

## What it does

Run one command on any repo that has a Graphify knowledge graph:

```bash
wtfcode scan .
```

Get five files:

- **PRODUCT_OVERVIEW.md** — what the repo is, how it's wired, which system smells are present
- **FAILURE_REPORT.md** — failure scenarios with blast radius, why it happens (system smell tag), and how to vibe safely
- **CRITICAL_PATH.md** — ranked load-bearing nodes, each with a "why it matters" line
- **tokens_saved.json** — proof of token savings
- **graph.json** — raw graph for future queries

## Proven on FastAPI

- 532 nodes, 1,536 edges
- 568,365 naive tokens → 683 WTFcode tokens = **832x savings**
- Top fragility hotspot: `HTTPException` with 107 dependents — single point of failure for every route

## Two modes

- **With Gemini** (`GEMINI_API_KEY`): AI-generated failure scenarios with outage-story consequences and specific mitigations
- **Structural** (`--no-llm`): topology-derived scenarios from degree, community membership, and cross-layer coupling — no API key needed

## System smell detection

Derived from graph topology without any LLM:

- `single point of failure` — degree >= 40, or highest in graph
- `high coupling` — node bridges 4+ architectural communities
- `hidden dependency chain` — deep convergence, degree >= 10
- `overloaded module` — handles too many roles, callers absorb unrelated changes

## Install

```bash
pip install -e .   # from source

# Requires: graphifyy (build graph once per repo)
pip install graphifyy
```

## Known limitations

- Requires a Graphify graph (`graphify-out/graph.json`) — run `/graphify .` first
- `--no-llm` scenarios are topology-derived, not causal — use Gemini for deeper analysis
- Community layer names are inferred from dominant source files when `community_name` is absent
