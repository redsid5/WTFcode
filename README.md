# WTFcode

<div align="center">

```text
 ██╗    ██╗████████╗███████╗ ██████╗  ██████╗ ██████╗ ███████╗
 ██║    ██║╚══██╔══╝██╔════╝██╔════╝ ██╔═══██╗██╔══██╗██╔════╝
 ██║ █╗ ██║   ██║   █████╗  ██║      ██║   ██║██║  ██║█████╗  
 ██║███╗██║   ██║   ██╔══╝  ██║      ██║   ██║██║  ██║██╔══╝  
 ╚███╔███╔╝   ██║   ██║     ╚██████╗ ╚██████╔╝██████╔╝███████╗
  ╚══╝╚══╝    ╚═╝   ╚═╝      ╚═════╝  ╚═════╝ ╚═════╝ ╚══════╝
# WTFcode
## What it does

WTFcode builds a dependency graph of your repo from AST and import analysis, ranks every node by structural risk, and produces six output files:

- **What this system is** — its architectural layers and how they wire together
- **Which files are load-bearing** — ranked by dependents and cross-layer coupling
- **Blast radius per file** — exactly how many nodes break if you touch it
- **System smells** — single points of failure, hidden dependency chains, high-coupling zones
- **How to touch it safely** — specific checks before editing each hotspot

It never reads raw source files. It works from a compact graph summary — **~700 tokens instead of ~568,000 for a repo like FastAPI** — so your LLM reasons from structure, not from a wall of code.

**v1 scope:** WTFcode v1 scans your local repo. It does not scan the internet, compare across GitHub, or automatically rewrite code. It gives you the map. You — or your AI coder — make the moves.

---

## Quick Start

**Step 1 — Install**
```bash
pip install wtfcode
```
This installs both WTFcode and Graphify in one shot. Nothing else needed.

**Step 2 — Scan**
```bash
wtfcode scan path/to/repo
```

**Step 3 — Read the output**
```
wtfcode-output/
├── EASY_OVERVIEW.md      ← start here: plain English, 3 questions you must answer
├── PRODUCT_OVERVIEW.md   ← architecture layers, load-bearing nodes, system smells
├── FAILURE_REPORT.md     ← where it breaks, blast radius, how to touch it safely
├── CRITICAL_PATH.md      ← don't touch these casually
├── tokens_saved.json     ← proof: N tokens vs M naive (Xx savings)
└── graph.json            ← raw graph for follow-up queries
```

> **Richer analysis (optional):** Run `/graphify .` in Claude Code first to build a full semantic graph. WTFcode uses it automatically if present — otherwise it builds a structural graph from your repo directly.

---

## Works With Any LLM

WTFcode auto-detects whichever API key you have set. No config needed.

| Key in your env | Install |
|---|---|
| `ANTHROPIC_API_KEY` | `pip install wtfcode[anthropic]` |
| `OPENAI_API_KEY` | `pip install wtfcode[openai]` |
| `GEMINI_API_KEY` | `pip install wtfcode[gemini]` |
| Ollama running locally | just run `ollama serve` |
| No key | `--no-llm` — free and instant |

```bash
wtfcode scan path/to/repo                          # auto-detects your key
wtfcode scan path/to/repo --model gpt-4o           # override model
wtfcode scan path/to/repo --model claude-opus-4-7
wtfcode scan path/to/repo --model gemini-2.5-flash
wtfcode scan path/to/repo --model ollama/llama3.2
wtfcode scan path/to/repo --no-llm                 # graph topology only, no API call
```

**Use a `.env` file** (WTFcode loads it automatically if `python-dotenv` is installed):
```bash
pip install wtfcode[dotenv]
```
```
# .env
ANTHROPIC_API_KEY=sk-ant-...
```

---

## Options

```
wtfcode scan <repo_path>

Options:
  --output-dir, -o  Where to write outputs  [default: <repo>/wtfcode-output]
  --top             Number of critical files to surface  [default: 20]
  --no-llm          Graph topology only — no API call, no cost
  --model           Override model  [default: auto-detected from API key]
```

---

## Real Example — FastAPI

```
$ wtfcode scan fastapi/

  Graph: 532 nodes, 1,536 edges

  Top 3 nodes drive ~72% of structural risk:
    1. HTTPException (exceptions.py)        107 dependents
    2. DefaultPlaceholder (datastructures)   56 dependents
    3. RequestValidationError                52 dependents

  Token compression: 568,365 → 683 (832x)
```

`PRODUCT_OVERVIEW.md` opens with:
> Codebase with 532 nodes across 12 architectural layers, wired through HTTPException, DefaultPlaceholder, RequestValidationError as load-bearing central points.
>
> System smells: `single point of failure` — HTTPException, DefaultPlaceholder, RequestValidationError. Central control points — any change propagates to every caller with no isolation layer.

---

## Using the Output with Your AI Coder

WTFcode's output is designed to be pasted directly into any AI coding assistant before you start a task. Three files, 30 seconds, and your AI now understands the structural risk of every move it makes.

### How to paste it in

Open a new chat with Cursor, Claude Code, Copilot, or any other AI coder and start like this:

```
Here's a structural analysis of the codebase I need your help with.
Read this before suggesting any changes.

--- PRODUCT_OVERVIEW.md ---
<paste contents>

--- FAILURE_REPORT.md ---
<paste contents>

--- CRITICAL_PATH.md ---
<paste contents>

My task: [what you want to do]
```

No plugin, no extension, no integration required.

### What changes with WTFcode context

Without WTFcode, your AI coder reads individual files and guesses at the blast radius of a change. With WTFcode, it starts from a ranked structural map.

**Without WTFcode — AI flying blind:**
> "I'll refactor `exceptions.py` to add a new error type. Looks straightforward."

**With WTFcode — AI working from the map:**
> "`exceptions.py` is a single point of failure — 107 nodes depend on `HTTPException`. Adding a new error type is safe only if I leave the existing interface unchanged. I'll check the 3 downstream callers in `CRITICAL_PATH.md` before writing anything."

### Which file to paste for which task

| Task | Files to paste |
|---|---|
| "Explain this codebase to me" | `PRODUCT_OVERVIEW.md` |
| "I want to change X — what else breaks?" | `FAILURE_REPORT.md` |
| "Which files should I not touch casually?" | `CRITICAL_PATH.md` |
| "Help me refactor this module safely" | `FAILURE_REPORT.md` + `CRITICAL_PATH.md` |
| Starting a new feature | All three — takes 30 seconds |

### Prompt templates

**New to the codebase:**
```
Read PRODUCT_OVERVIEW.md below. Tell me what this system does, which parts are
load-bearing, and what I should understand before writing any code.

<paste PRODUCT_OVERVIEW.md>
```

**Before making a change:**
```
I need to modify [file/function]. Using FAILURE_REPORT.md and CRITICAL_PATH.md below,
tell me what could break and what I should check or lock down first.

<paste FAILURE_REPORT.md>
<paste CRITICAL_PATH.md>
```

**Reviewing a PR:**
```
Here's a diff I need to review. Using the structural analysis below, flag any changes
that touch load-bearing nodes or high-severity failure scenarios.

<paste diff>
<paste FAILURE_REPORT.md>
```

---

## How to read the output (without reading everything)

You don't need to read every line of every file. Here's exactly what you must do, and what you can delegate.

### The one file you must read: `EASY_OVERVIEW.md`

WTFcode generates `EASY_OVERVIEW.md` specifically for you — plain English, no graph jargon, no node IDs. It answers three questions:

1. **What does this system do?**
2. **What is the main user-facing flow?**
3. **Which files could break 50+ other things if changed?**

Read this file until you can answer all three in your own words. That's the only requirement. After that, let your AI coder handle the details.

### What the other files are for

| File | You need to | Or just paste it into your AI coder |
|---|---|---|
| `EASY_OVERVIEW.md` | **Read it yourself** — know the big picture | — |
| `PRODUCT_OVERVIEW.md` | Skim for architecture and system smells | Yes |
| `FAILURE_REPORT.md` | Skip — let your AI read it | Yes |
| `CRITICAL_PATH.md` | Skip — let your AI read it | Yes |

### The paste-in that gives your AI full context

Once you understand the big picture from `EASY_OVERVIEW.md`, open a new chat and paste everything:

```
I've read EASY_OVERVIEW.md and understand the system. Here's the full structural context.

--- EASY_OVERVIEW.md ---
<paste contents>

--- PRODUCT_OVERVIEW.md ---
<paste contents>

--- FAILURE_REPORT.md ---
<paste contents>

--- CRITICAL_PATH.md ---
<paste contents>

My task: [what you want to do]
```

You understand the story. The AI understands the structure. Together you won't break prod.

---

## How It Works

WTFcode works in three steps and never reads raw source files:

1. **Build the graph** — reads `graphify-out/graph.json` if present (built by [Graphify](https://github.com/safishamsi/graphify)), or falls back to direct AST extraction from the repo. Either way, you get a dependency graph.

2. **Compress to a summary** — serializes the top 20 nodes by dependency degree and their edges into ~700 tokens of plain text. A 1,000-node repo becomes a paragraph, not a wall of code.

3. **Analyze** — sends the compact summary to your LLM (or uses graph topology alone in `--no-llm` mode) to rank failure scenarios, identify system smells, and generate safe-change guidance.

### System Smells

WTFcode v1 ships three structurally-defined smells — each is computed from graph topology, not from heuristics or "vibes":

| Smell | Structural definition |
|---|---|
| `single point of failure` | 40+ nodes depend on this — any change is system-wide |
| `high coupling` | connects 4+ distinct subsystems (approx) — changes bleed across unrelated layers |
| `hidden dependency chain` | 10+ callers route through this with no isolation layer |

> Risk percentages and smell classifications are proxies derived from degree, centrality, and bridging behavior — not from runtime data or failure logs.

### Output Files

| File | Read when... |
|---|---|
| `EASY_OVERVIEW.md` | You need to understand the codebase in plain English before touching anything |
| `PRODUCT_OVERVIEW.md` | You want the full architectural picture — layers, smells, god nodes |
| `FAILURE_REPORT.md` | You're about to change something and want the blast radius |
| `CRITICAL_PATH.md` | You need to know which files are load-bearing and why |
| `tokens_saved.json` | You want the token savings breakdown |
| `graph.json` | You want to run follow-up queries with `/graphify query` |

---

## v1 Vision

WTFcode v1 is deliberately scoped. Here's what it is, and what it isn't.

**What v1 does:**
- Scans any local repo and builds a structural dependency graph (AST + import analysis)
- Detects load-bearing nodes, blast radius, and three structurally-defined smells (no vibes — all computable from the graph)
- Generates six output files: plain-English overview, architecture report, failure map, critical path, token proof, and raw graph
- Runs free with `--no-llm`; plugs into any LLM with a single API key
- Works on any language codebase the graph can represent

**What v1 does not do:**
- Scan the internet, compare across GitHub, or find "similar code" globally
- Automatically rewrite or refactor your code
- Replace code review or human judgment
- Run as a persistent agent or CI integration (that's v2)

**Who it's for:**
- Any developer using an AI coding assistant — Cursor, Claude Code, Copilot, or similar
- Teams onboarding to a codebase they didn't write
- Anyone about to refactor a module they're not sure is safe to touch
- Python-first for now; the graph layer is language-agnostic

---

## Requirements

- Python 3.10+
- At least one LLM API key (optional) — Anthropic, OpenAI, or Gemini; or Ollama running locally. Structural mode is free with no key.

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

Contract tests in `tests/test_contracts.py` verify the output bundle shape, model field contracts, and CLI options. Tests requiring a pre-built graph skip automatically if `graphify-out/graph.json` is absent.

---

## Author

Built by **Siddharth Reddy**.
