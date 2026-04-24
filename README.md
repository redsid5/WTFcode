# WTFcode

**Graph-first failure prediction for repos you didn't write.**

One command. Five output files. Know what breaks before you touch anything.

---

## What it does

WTFcode scans a codebase's knowledge graph, finds the highest-risk nodes, and produces a plain-English report explaining:

- **What this system is** and how its layers connect
- **Where it's fragile** — which nodes, if changed, cascade into failures
- **How to touch it safely** — what to check before editing each hotspot

It never reads raw files. It reads a compact graph summary (~700 tokens instead of ~568,000 for FastAPI) and reasons from structure.

---

## Quick Start

**Step 1 — Install WTFcode**
```bash
pip install -e .
```

**Step 2 — Build the graph for the repo you want to analyze** (once per repo)
```bash
cd target-repo
pip install graphifyy
# then in Claude Code: /graphify .
# or from terminal:   python -m graphify .
```

**Step 3 — Run the scan**
```bash
wtfcode scan path/to/target-repo
```

**Step 4 — Read the output, starting with `PRODUCT_OVERVIEW.md`**
```
wtfcode-output/
├── PRODUCT_OVERVIEW.md   ← start here: what this is, how it's wired, smells
├── FAILURE_REPORT.md     ← where it breaks, blast radius, how to vibe safely
├── CRITICAL_PATH.md      ← don't touch these casually
├── tokens_saved.json     ← proof: N tokens vs M naive (Xx savings)
└── graph.json            ← raw graph for future queries
```

---

## Two Modes

**With AI** (richer causal analysis — free key at [aistudio.google.com](https://aistudio.google.com))
```bash
# Windows
$env:GEMINI_API_KEY = "your-key"
# Mac/Linux
export GEMINI_API_KEY="your-key"

wtfcode scan path/to/repo
```

**Without AI** (graph topology only — instant, no API key needed)
```bash
wtfcode scan path/to/repo --no-llm
```

Both modes produce the same five output files. The `--no-llm` mode derives all failure scenarios from degree, community membership, and cross-layer coupling — no LLM call.

---

## Options

```
wtfcode scan <repo_path>

Options:
  --output-dir, -o  Where to write outputs  [default: <repo>/wtfcode-output]
  --top             Number of critical files to surface  [default: 20]
  --no-llm          Use graph topology only; skip Gemini API
```

---

## Real Example — FastAPI

```
$ wtfcode scan fastapi/

  Graph: 532 nodes, 1,536 edges

  Token discipline
    Naive (read all files):  568,365 tokens
    WTFcode (graph summary):     683 tokens
    Savings ratio:             832.2x

  Top failure scenarios
  ┌─────────────────────────────────────┬────────┬───────────────────────┐
  │ Scenario                            │  Sev   │ If this breaks        │
  ├─────────────────────────────────────┼────────┼───────────────────────┤
  │ HTTPException (exceptions.py)       │  high  │ 107 dependents fail   │
  │ DefaultPlaceholder (datastructures) │  high  │ 56 dependents fail    │
  │ RequestValidationError              │  high  │ 52 dependents fail    │
  └─────────────────────────────────────┴────────┴───────────────────────┘
```

`PRODUCT_OVERVIEW.md` opens with:
> Codebase with 532 nodes across 12 architectural layers, wired through HTTPException, DefaultPlaceholder, RequestValidationError as load-bearing central points.
>
> System smells: `single point of failure` — HTTPException, DefaultPlaceholder, RequestValidationError. Central control points — any change propagates to every caller with no isolation layer.

---

## Using the Output with Your AI Coder

After running `wtfcode scan`, paste the output files directly into your AI coding assistant before you start a task. This gives it structural context it could never get from reading files one by one.

### The paste-in pattern

Open a new chat with your AI coder (Claude Code, Cursor, Copilot, etc.) and start like this:

```
Here's a structural analysis of the codebase I need you to help with.

--- PRODUCT_OVERVIEW.md ---
<paste contents>

--- FAILURE_REPORT.md ---
<paste contents>

--- CRITICAL_PATH.md ---
<paste contents>

Now here's my task: [what you want to do]
```

That's it. The AI now knows:
- Which files are load-bearing and why
- What breaks if it touches each one
- Which system smells are present and where
- How to make changes safely

### What the AI gets that it wouldn't otherwise

Without WTFcode, your AI coder reads individual files and guesses at the blast radius of a change. With WTFcode, it starts with a ranked map of every risk in the system.

**Before (without WTFcode):**
> "I'll refactor `exceptions.py` to add a new error type."

**After (with WTFcode):**
> "`exceptions.py` is a single point of failure — 107 nodes depend on `HTTPException`. I'll add the new type without changing the existing interface, and I'll check the 3 downstream callers listed in `CRITICAL_PATH.md` before touching anything."

### Which file to paste for which task

| Task | Paste this |
|---|---|
| "Help me understand this codebase" | `PRODUCT_OVERVIEW.md` |
| "I want to change X, what else breaks?" | `FAILURE_REPORT.md` |
| "Which files should I avoid touching?" | `CRITICAL_PATH.md` |
| "Should I refactor this module?" | `FAILURE_REPORT.md` + `CRITICAL_PATH.md` |
| Starting a new feature from scratch | All three — takes 30 seconds |

### Prompt templates

**New to the codebase:**
```
Read PRODUCT_OVERVIEW.md below. Tell me what this system does and which
parts I should understand before writing any code.

<paste PRODUCT_OVERVIEW.md>
```

**Before making a change:**
```
I need to modify [file/function]. Using FAILURE_REPORT.md and CRITICAL_PATH.md
below, tell me what could break and what I should check first.

<paste FAILURE_REPORT.md>
<paste CRITICAL_PATH.md>
```

**Reviewing a PR:**
```
Here's a diff I need to review. Using the structural analysis below, flag
any changes that touch load-bearing nodes or high-severity failure scenarios.

<paste diff>
<paste FAILURE_REPORT.md>
```

---

## How It Works

WTFcode never reads raw source files. It works in three steps:

1. **Load the graph** — reads `graphify-out/graph.json` built by [Graphify](https://github.com/safishamsi/graphify). If no graph exists, falls back to AST-only extraction from the repo directly.

2. **Build a compact summary** — serializes the top 20 nodes by dependency degree + their edges into ~700 tokens of plain text. A 1,000-node graph becomes a paragraph, not a wall of code.

3. **Analyze** — sends the compact summary to Gemini (or uses topology alone in `--no-llm` mode) to identify failure scenarios, system smells, and safe-change guidance.

### System Smells

WTFcode classifies every hotspot into one of four structural smells:

| Smell | What it means |
|---|---|
| `single point of failure` | 40+ nodes depend on this — any change is system-wide |
| `high coupling` | bridges 4+ architectural communities |
| `hidden dependency chain` | 10+ callers route through this with no isolation layer |
| `overloaded module` | too many roles in one place |

### Output Files

| File | Read when... |
|---|---|
| `PRODUCT_OVERVIEW.md` | You're new to the repo and need a 60-second orientation |
| `FAILURE_REPORT.md` | You're about to change something and want to know what else breaks |
| `CRITICAL_PATH.md` | You need to know which files are load-bearing and why |
| `tokens_saved.json` | You want to measure the token savings vs naive file reading |
| `graph.json` | You want to run follow-up queries with `/graphify query` |

---

## Requirements

- Python 3.10+
- [Graphify](https://github.com/safishamsi/graphify) (`pip install graphifyy`) — to build the knowledge graph for a repo
- Gemini API key (optional) — free at [aistudio.google.com](https://aistudio.google.com); only needed for AI mode

---

## Install from Source

```bash
git clone <this-repo>
cd WTFcode
pip install -e .
```

Run tests:
```bash
pytest tests/
```

The contract tests in `tests/test_contracts.py` verify the output bundle shape, model field contracts, and CLI options. Tests that require a pre-built graph are skipped automatically if `graphify-out/graph.json` is absent.
