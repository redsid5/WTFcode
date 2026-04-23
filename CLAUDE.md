# WTFcode Assistant Rules (Graph-First)

## Context-navigation rules (must follow)

1. Always query the knowledge graph first.
2. Before using or reading any raw files, first attempt to answer the query by querying the knowledge graph.
3. Only proceed to raw files if the knowledge graph does not contain the required information or if the user explicitly instructs you to read raw files.
4. Only read raw files if explicitly requested.
5. Treat raw files (for example, full documents, logs, or source-code dumps) as a secondary fallback.
6. If the user says (or implies) to "read the raw file," "open the file," or similar, then you may access and process those files directly; otherwise, stay within the knowledge-graph layer.

## Token minimization policy

1. Prefer graph summary output over full file reads.
2. Return concise answers with only relevant evidence.
3. Avoid broad file scans when graph query or path query can answer.
4. Use focused follow-up graph queries instead of loading large contexts.

## Graphify usage policy

1. Use graph outputs from `graphify-out/` first.
2. Read `graphify-out/GRAPH_REPORT.md` before architecture/system questions.
3. Use graph-level commands (`query`, `path`, `explain`) before any raw-file search.
4. If graph artifacts are missing, prompt to run `/graphify .` in a supported assistant session.

## Key artifacts

- **`graphify-out/GRAPH_REPORT.md`** — primary navigation layer; read this before answering architecture questions. Contains god nodes, community structure, and surprising cross-file connections.
- **`graphify-out/graph.html`** — interactive browser graph; use this to visually explore node clusters and spot isolated concepts that need documentation.
- **`graphify-out/graph.json`** — raw graph data; source of truth for `query`, `path`, and `explain` commands across sessions.
- **`.graphifyignore`** — exclude folders or files from graph extraction (same syntax as `.gitignore`); update when adding generated or vendor files.
- **Trigger behavior** — `/graphify` invokes the Graphify skill before any other repo analysis; the skill definition lives in the global `CLAUDE.md`.
- **Cache (`graphify-out/cache/`)** — SHA256-based; only changed files are re-extracted on `--update` runs.

## Build workflow for this repo

1. Run `/graphify .` to generate the graph artifacts.
2. Use `graphify-out/GRAPH_REPORT.md` as the primary navigation layer.
3. Use graph queries for task execution.
4. Use raw files only by explicit user request.

## Trigger behavior

- When user invokes `/graphify`, execute the Graphify skill first before other repository analysis.
