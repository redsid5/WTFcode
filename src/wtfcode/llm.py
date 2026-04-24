"""
Multi-provider LLM client.

Auto-detects from environment in priority order:
  ANTHROPIC_API_KEY → Claude  (claude-sonnet-4-5)
  OPENAI_API_KEY    → GPT     (gpt-4o-mini)
  GEMINI_API_KEY    → Gemini  (gemini-2.5-flash)
  Ollama running    → Ollama  (llama3.2)

Override with --model flag or WTFCODE_MODEL env var.
Loads .env automatically if python-dotenv is installed.
"""

from __future__ import annotations

import json
import os
import urllib.request
from pathlib import Path

_DEFAULT_MODELS = {
    "anthropic": "claude-sonnet-4-5",
    "openai": "gpt-4o-mini",
    "gemini": "gemini-2.5-flash",
    "ollama": "llama3.2",
}


def load_dotenv(repo_path: Path | None = None) -> None:
    """Load .env from repo_path or cwd if python-dotenv is available."""
    try:
        from dotenv import load_dotenv as _load
    except ImportError:
        return
    candidates = []
    if repo_path:
        candidates.append(repo_path / ".env")
    candidates.append(Path.cwd() / ".env")
    for p in candidates:
        if p.exists():
            _load(p, override=False)
            return


def detect_provider() -> tuple[str, str] | None:
    """Return (provider, default_model) from env vars, or None if nothing set."""
    if os.environ.get("ANTHROPIC_API_KEY"):
        return "anthropic", _DEFAULT_MODELS["anthropic"]
    if os.environ.get("OPENAI_API_KEY"):
        return "openai", _DEFAULT_MODELS["openai"]
    if os.environ.get("GEMINI_API_KEY"):
        return "gemini", _DEFAULT_MODELS["gemini"]
    if _ollama_running():
        return "ollama", _DEFAULT_MODELS["ollama"]
    return None


def provider_from_model(model: str) -> str:
    """Infer provider from model name prefix."""
    m = model.lower()
    if m.startswith("claude"):
        return "anthropic"
    if m.startswith(("gpt-", "o1-", "o3-", "o4-")):
        return "openai"
    if m.startswith("gemini"):
        return "gemini"
    return "ollama"


def call_llm(prompt: str, model: str | None = None) -> tuple[str, str]:
    """
    Send prompt to LLM. Returns (response_text, model_name_used).

    Resolution order:
      1. model argument
      2. WTFCODE_MODEL env var
      3. Auto-detect from available API keys
    """
    if not model:
        model = os.environ.get("WTFCODE_MODEL")

    if model:
        provider = provider_from_model(model)
        return _dispatch(provider, model, prompt), model

    detected = detect_provider()
    if not detected:
        raise RuntimeError(
            "No LLM provider found. Set one of:\n"
            "  ANTHROPIC_API_KEY  → Claude\n"
            "  OPENAI_API_KEY     → OpenAI\n"
            "  GEMINI_API_KEY     → Gemini\n"
            "Or run with --no-llm for free structural analysis."
        )
    provider, default_model = detected
    return _dispatch(provider, default_model, prompt), default_model


def _dispatch(provider: str, model: str, prompt: str) -> str:
    if provider == "anthropic":
        return _anthropic(model, prompt)
    if provider == "openai":
        return _openai(model, prompt)
    if provider == "gemini":
        return _gemini(model, prompt)
    return _ollama(model, prompt)


def _anthropic(model: str, prompt: str) -> str:
    try:
        import anthropic
    except ImportError:
        raise RuntimeError("Run: pip install anthropic")
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    msg = client.messages.create(
        model=model,
        max_tokens=2048,
        messages=[{"role": "user", "content": prompt}],
    )
    return msg.content[0].text


def _openai(model: str, prompt: str) -> str:
    try:
        import openai
    except ImportError:
        raise RuntimeError("Run: pip install openai")
    client = openai.OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
    )
    return resp.choices[0].message.content


def _gemini(model: str, prompt: str) -> str:
    try:
        from google import genai
    except ImportError:
        raise RuntimeError("Run: pip install google-genai")
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    response = client.models.generate_content(model=model, contents=prompt)
    return response.text


def _ollama(model: str, prompt: str) -> str:
    model_name = model.removeprefix("ollama/")
    host = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
    payload = json.dumps({"model": model_name, "prompt": prompt, "stream": False}).encode()
    req = urllib.request.Request(
        f"{host}/api/generate",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            return json.loads(resp.read())["response"]
    except Exception as e:
        raise RuntimeError(f"Ollama request failed: {e}. Is `ollama serve` running?")


def _ollama_running() -> bool:
    try:
        urllib.request.urlopen("http://localhost:11434/api/tags", timeout=1)
        return True
    except Exception:
        return False
