# Graph Report - .  (2026-04-23)

## Corpus Check
- Corpus is ~4,133 words - fits in a single context window. You may not need a graph.

## Summary
- 42 nodes · 54 edges · 7 communities detected
- Extraction: 93% EXTRACTED · 7% INFERRED · 0% AMBIGUOUS · INFERRED: 4 edges (avg confidence: 0.72)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_Graph-First Navigation Rules|Graph-First Navigation Rules]]
- [[_COMMUNITY_Graphify Tool & Ecosystem|Graphify Tool & Ecosystem]]
- [[_COMMUNITY_Output Artifacts & Auto-Sync|Output Artifacts & Auto-Sync]]
- [[_COMMUNITY_Query & Navigation Interface|Query & Navigation Interface]]
- [[_COMMUNITY_Graph Structure & Extraction Quality|Graph Structure & Extraction Quality]]
- [[_COMMUNITY_Extraction Pipeline|Extraction Pipeline]]
- [[_COMMUNITY_Clustering & Similarity|Clustering & Similarity]]

## God Nodes (most connected - your core abstractions)
1. `Graphify AI Coding Assistant Skill` - 16 edges
2. `Knowledge Graph` - 6 edges
3. `Three-Pass Extraction Pipeline` - 6 edges
4. `WTFcode Assistant Rules (Graph-First)` - 5 edges
5. `graphify-out Output Directory` - 5 edges
6. `Graphify Graph-Level Commands (query, path, explain)` - 4 edges
7. `GRAPH_REPORT.md God Nodes and Community Structure` - 4 edges
8. `Context-Navigation Rules` - 3 edges
9. `Token Minimization Policy` - 3 edges
10. `Graphify Usage Policy` - 3 edges

## Surprising Connections (you probably didn't know these)
- `Raw Files as Secondary Fallback` --semantically_similar_to--> `Privacy Model (Local Code Processing)`  [INFERRED] [semantically similar]
  CLAUDE.md → WTFcode.md
- `Token Minimization Policy` --semantically_similar_to--> `Token Reduction Benchmark (71.5x)`  [INFERRED] [semantically similar]
  CLAUDE.md → WTFcode.md
- `graphify-out/GRAPH_REPORT.md` --conceptually_related_to--> `GRAPH_REPORT.md God Nodes and Community Structure`  [EXTRACTED]
  CLAUDE.md → WTFcode.md
- `Graphify Graph-Level Commands (query, path, explain)` --conceptually_related_to--> `graphify query Command`  [EXTRACTED]
  CLAUDE.md → WTFcode.md
- `Graphify Graph-Level Commands (query, path, explain)` --conceptually_related_to--> `graphify path Command`  [EXTRACTED]
  CLAUDE.md → WTFcode.md

## Hyperedges (group relationships)
- **Three-Pass Extraction Pipeline (AST + Whisper + Claude Subagents)** — WTFcode_ast_pass, WTFcode_faster_whisper, WTFcode_claude_subagents [EXTRACTED 1.00]
- **Graphify Output Artifacts (graph.html + GRAPH_REPORT.md + graph.json + cache)** — WTFcode_graph_html, WTFcode_graph_report_md, WTFcode_graph_json, WTFcode_sha256_cache [EXTRACTED 1.00]
- **Graph-First Navigation System (CLAUDE.md rules + GRAPH_REPORT.md + graphify commands)** — CLAUDE_knowledge_graph_first, WTFcode_graph_report_md, CLAUDE_graphify_commands [INFERRED 0.90]

## Communities

### Community 0 - "Graph-First Navigation Rules"
Cohesion: 0.24
Nodes (10): Build Workflow for WTFcode Repo, Context-Navigation Rules, graphify-out/GRAPH_REPORT.md, Graphify Usage Policy, Knowledge Graph First Query Policy, Raw Files as Secondary Fallback, Token Minimization Policy, Graphify Trigger Behavior (+2 more)

### Community 1 - "Graphify Tool & Ecosystem"
Cohesion: 0.25
Nodes (8): Git Hooks (post-commit/post-checkout), Graphify AI Coding Assistant Skill, .graphifyignore Exclusion File, graphifyy PyPI Package, Multimodal File Support (Code/PDF/Images/Video), Penpax Enterprise Layer, Privacy Model (Local Code Processing), Wiki Mode (Community Articles)

### Community 2 - "Output Artifacts & Auto-Sync"
Cohesion: 0.29
Nodes (7): God Nodes (Highest-Degree Concepts), graph.html Interactive Visualization, GRAPH_REPORT.md God Nodes and Community Structure, graphify-out Output Directory, PreToolUse Hook (Claude Code Always-On), SHA256 File Cache, Watch Mode Auto-Sync

### Community 3 - "Query & Navigation Interface"
Cohesion: 0.33
Nodes (6): Graphify Graph-Level Commands (query, path, explain), graph.json Persistent Graph, graphify explain Command, graphify path Command, graphify query Command, MCP Server for graph.json

### Community 4 - "Graph Structure & Extraction Quality"
Cohesion: 0.4
Nodes (5): Deterministic AST Pass (tree-sitter), Confidence Scoring (EXTRACTED/INFERRED/AMBIGUOUS), Hyperedges (3+ Node Group Relationships), Knowledge Graph, Rationale-For Nodes (Design Rationale Extraction)

### Community 5 - "Extraction Pipeline"
Cohesion: 0.5
Nodes (4): Claude Subagents Parallel Extraction, faster-whisper Local Audio Transcription, NetworkX Graph Library, Three-Pass Extraction Pipeline

### Community 6 - "Clustering & Similarity"
Cohesion: 1.0
Nodes (2): Leiden Community Detection Clustering, Semantic Similarity Edges

## Knowledge Gaps
- **14 isolated node(s):** `Graphify Trigger Behavior`, `graph.html Interactive Visualization`, `.graphifyignore Exclusion File`, `Claude Subagents Parallel Extraction`, `NetworkX Graph Library` (+9 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **Thin community `Clustering & Similarity`** (2 nodes): `Leiden Community Detection Clustering`, `Semantic Similarity Edges`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Graphify AI Coding Assistant Skill` connect `Graphify Tool & Ecosystem` to `Graph-First Navigation Rules`, `Output Artifacts & Auto-Sync`, `Query & Navigation Interface`, `Graph Structure & Extraction Quality`, `Extraction Pipeline`?**
  _High betweenness centrality (0.726) - this node is a cross-community bridge._
- **Why does `Three-Pass Extraction Pipeline` connect `Extraction Pipeline` to `Graphify Tool & Ecosystem`, `Graph Structure & Extraction Quality`, `Clustering & Similarity`?**
  _High betweenness centrality (0.216) - this node is a cross-community bridge._
- **Why does `Knowledge Graph` connect `Graph Structure & Extraction Quality` to `Graphify Tool & Ecosystem`, `Output Artifacts & Auto-Sync`, `Clustering & Similarity`?**
  _High betweenness centrality (0.205) - this node is a cross-community bridge._
- **What connects `Graphify Trigger Behavior`, `graph.html Interactive Visualization`, `.graphifyignore Exclusion File` to the rest of the system?**
  _14 weakly-connected nodes found - possible documentation gaps or missing edges._