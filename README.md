# WTFcode

**Graph‑first failure prediction for repos you didn’t write.**  
One CLI command, five output files, and a clear map of what breaks before you touch anything.

WTFcode scans a codebase’s knowledge graph, finds the highest‑risk nodes, and generates plain‑English reports that:
- Explain what the system is and how its layers connect.
- Pinpoint where it’s fragile (blast radius of each change).
- Show how to touch hotspots safely (what to check before editing).

No raw file reading. It reasons from a compact graph summary (~700 tokens instead of hundreds of thousands).

---

## 📌 Quick Start

### 1. Install

```bash
pip install wtfcode
```

This installs both `wtfcode` and `graphify` in one shot. No extra setup needed. [web:13]

### 2. Scan

```bash
wtfcode scan path/to/repo
```

### 3. Read the output

Look in `wtfcode-output/`:

```text
├── PRODUCT_OVERVIEW.md   ← start here: what this is, how it's wired, smells
├── FAILURE_REPORT.md     ← where it breaks, blast radius, how to touch safely
├── CRITICAL_PATH.md      ← don't touch these casually
├── tokens_saved.json     ← proof: N tokens vs M naive (Xx savings)
└── graph.json            ← raw graph for future queries
```

Optional richer analysis:  
Run `/graphify .` in your AI editor (e.g., Claude Code) first. WTFcode will use its `graph.json` if found; otherwise it builds a structural graph from your code directly. [web:13]

---

## 💡 What It Does

WTFcode:
- **Never reads raw files**. It ingests a graph summary (AST‑ or semantic‑based) and reasons over structure.
- Detects **high‑risk nodes** (HTTPException‑style load‑bearing points).
- Produces **three human‑readable reports** you can paste into your AI coder or RFC docs.
- Measures **token savings** vs naive “read‑all‑files” approaches.

Typical use‑case:  
You’re handed a legacy codebase and asked to refactor or add features. WTFcode surfaces:
- The **single points of failure**.
- The **high‑coupling bridges** across layers.
- The **hidden dependency chains** you never knew about.

---

## 🤖 Works With Any LLM

WTFcode auto‑detects whichever API key you already have set. [web:8]

| You have                          | Install command                          |
|-----------------------------------|------------------------------------------|
| `ANTHROPIC_API_KEY`               | `pip install wtfcode[anthropic]`        |
| `OPENAI_API_KEY`                  | `pip install wtfcode[openai]`           |
| `GEMINI_API_KEY`                  | `pip install wtfcode[gemini]`           |
| Ollama (local)                    | `pip install wtfcode[ollama]` + `ollama serve` |

You can also use `.env` if `python-dotenv` is installed:

```bash
pip install wtfcode[dotenv]
```

```env
ANTHROPIC_API_KEY=sk-ant-...
```

### Run with a specific model

```bash
wtfcode scan path/to/repo --model claude-opus-4-7
wtfcode scan path/to/repo --model gpt-4o
wtfcode scan path/to/repo --model gemini-2.5-flash
wtfcode scan path/to/repo --model ollama/llama3.2
```

### Free structural mode (no API calls)

```bash
wtfcode scan path/to/repo --no-llm
```

In `--no-llm` mode, all failure scenarios come from graph topology (degree, communities, cross‑layer coupling). [web:13]

---

## 🧩 Example — FastAPI

```text
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

> Codebase with 532 nodes across 12 architectural layers, wired through HTTPException, DefaultPlaceholder, RequestValidationError as load‑bearing central points.  
> System smells: single point of failure — HTTPException, DefaultPlaceholder, RequestValidationError. Central control points — any change propagates to every caller with no isolation layer.

---

## 🧠 Using the Output With Your AI Coder

After running `wtfcode scan`, paste the outputs into your AI assistant (Claude Code, Cursor, Copilot, etc.) before you start a task. This gives it **structural context** it could never get from reading files one‑by‑one. [web:7]

### The paste‑in pattern

```text
Here's a structural analysis of the codebase I need you to help with.

--- PRODUCT_OVERVIEW.md ---
<paste contents>

--- FAILURE_REPORT.md ---
<paste contents>

--- CRITICAL_PATH.md ---
<paste contents>

Now here's my task: [what you want to do]
```

Your AI now knows:
- Which files are load‑bearing and why.
- What breaks if it touches each one.
- Which system smells are present and where.
- How to make changes safely.

---

### Which file to paste for which task

| Task                                | Files to paste                          |
|-------------------------------------|-----------------------------------------|
| "Help me understand this codebase"  | `PRODUCT_OVERVIEW.md`                   |
| "I want to change X, what else breaks?" | `FAILURE_REPORT.md`                 |
| "Which files should I avoid touching?" | `CRITICAL_PATH.md`                   |
| "Should I refactor this module?"    | `FAILURE_REPORT.md` + `CRITICAL_PATH.md` |
| Starting a new feature from scratch | All three (takes 30 seconds)          |

---

## 📝 Prompt Templates

### New to the codebase

```text
Read PRODUCT_OVERVIEW.md below. Tell me what this system does and which
parts I should understand before writing any code.

<PASTE PRODUCT_OVERVIEW.md>
```

### Before making a change

```text
I need to modify [file/function]. Using FAILURE_REPORT.md and CRITICAL_PATH.md
below, tell me what could break and what I should check first.

<PASTE FAILURE_REPORT.md>
<PASTE CRITICAL_PATH.md>
```

### Reviewing a PR

```text
Here's a diff I need to review. Using the structural analysis below, flag
any changes that touch load‑bearing nodes or high‑severity failure scenarios.

<PASTE DIFF>
<PASTE FAILURE_REPORT.md>
```

---

## ⚙️ How It Works

WTFcode works in three steps:

1. **Load the graph**  
   Reads `graphify-out/graph.json` built by [Graphify](https://github.com/safishamsi/graphify).  
   If no graph exists, falls back to AST‑only extraction from the repo directly. [web:13]

2. **Build a compact summary**  
   Serializes the top 20 nodes by dependency degree + their edges into ~700 tokens of plain text.  
   A 1,000‑node graph becomes a paragraph, not a wall of code.

3. **Analyze**  
   Sends the compact summary to Gemini (or uses topology alone in `--no-llm` mode) to identify:
   - Failure scenarios.
   - System smells.
   - Safe‑change guidance.

---

## 🧪 System Smells

WTFcode classifies every hotspot into one of four structural smells:

| Smell                   | What it means                                                                 |
|-------------------------|-------------------------------------------------------------------------------|
| `single point of failure` | 40+ nodes depend on this — any change is system‑wide.                       |
| `high coupling`         | Bridges 4+ architectural communities.                                        |
| `hidden dependency chain` | 10+ callers route through this with no isolation layer.                    |
| `overloaded module`     | Too many roles in one place (controller + orchestrator + formatter, etc.). |

---

## 📁 Output Files

| File                    | When to read it                                                                 |
|-------------------------|---------------------------------------------------------------------------------|
| `PRODUCT_OVERVIEW.md`   | You’re new to the repo and need a 60‑second orientation.                      |
| `FAILURE_REPORT.md`     | You’re about to change something and want to know what else breaks.           |
| `CRITICAL_PATH.md`      | You need to know which files are load‑bearing and why.                        |
| `tokens_saved.json`     | You want to measure the token savings vs naive file reading.                  |
| `graph.json`            | You want to run follow‑up queries with `/graphify query`.                     |

---

## ✅ Requirements

- Python 3.10+
- At least one LLM API key (optional) — Anthropic, OpenAI, Gemini; or run Ollama locally. [web:13]

---

## 🧱 Install From Source

```bash
git clone https://github.com/redsid5/WTFcode
cd WTFcode
pip install -e .    # installs wtfcode + graphify together
```

Run tests:

```bash
pytest tests/
```

The contract tests in `tests/test_contracts.py` verify the output bundle shape, model field contracts, and CLI options. Tests that require a pre‑built graph are skipped automatically if `graphify-out/graph.json` is absent. [web:15]

---

## 📦 License

MIT (see `LICENSE`).

---

## 👥 Author

Built by **[Siddharth Reddy](https://github.com/redsid5)**. [web:17]
