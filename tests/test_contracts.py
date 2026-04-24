"""
Contract tests for WTFcode's load-bearing interfaces.

These tests catch silent drift in:
  1. Output bundle — all five files must be produced
  2. Report sections — required headings must be present
  3. Model fields — FailureScenario and RepoFile must not lose fields
  4. CLI interface — expected options must be present
"""

import json
import tempfile
from pathlib import Path

import pytest

from wtfcode.models import FailureScenario, RepoFile


# ---------------------------------------------------------------------------
# 1. Model field contracts
# ---------------------------------------------------------------------------

class TestFailureScenarioContract:
    def test_required_fields(self):
        s = FailureScenario(
            title="t", trigger="tr", downstream=[], severity="high", likelihood="medium"
        )
        assert hasattr(s, "title")
        assert hasattr(s, "trigger")
        assert hasattr(s, "downstream")
        assert hasattr(s, "severity")
        assert hasattr(s, "likelihood")

    def test_optional_fields_exist_with_defaults(self):
        s = FailureScenario(
            title="t", trigger="tr", downstream=[], severity="high", likelihood="medium"
        )
        assert hasattr(s, "consequence")
        assert hasattr(s, "mitigation")
        assert hasattr(s, "why_this_happens")
        assert hasattr(s, "system_smell")
        assert hasattr(s, "how_to_vibe_safely")

    def test_system_smell_values(self):
        valid = {
            "single point of failure",
            "high coupling",
            "hidden dependency chain",
            "overloaded module",
            "",
        }
        s = FailureScenario(
            title="t", trigger="tr", downstream=[], severity="high",
            likelihood="medium", system_smell="high coupling"
        )
        assert s.system_smell in valid

    def test_severity_values(self):
        for sev in ("high", "medium", "low"):
            s = FailureScenario(
                title="t", trigger="tr", downstream=[], severity=sev, likelihood="medium"
            )
            assert s.severity == sev


class TestRepoFileContract:
    def test_required_fields(self):
        f = RepoFile(path="a.py", degree=5, community="core")
        assert hasattr(f, "path")
        assert hasattr(f, "degree")
        assert hasattr(f, "community")

    def test_optional_fields_exist_with_defaults(self):
        f = RepoFile(path="a.py", degree=5, community="core")
        assert hasattr(f, "is_critical")
        assert hasattr(f, "fragility_score")
        assert hasattr(f, "connections")
        assert f.connections == []


# ---------------------------------------------------------------------------
# 2. Output bundle contract — run on the WTFcode repo itself
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).parent.parent
GRAPH_JSON = REPO_ROOT / "graphify-out" / "graph.json"


@pytest.mark.skipif(
    not GRAPH_JSON.exists(),
    reason="graphify-out/graph.json not present — run /graphify . first"
)
class TestOutputBundleContract:
    @pytest.fixture(scope="class")
    def output_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            from wtfcode.scanner import load_or_build_graph, extract_repo_files
            from wtfcode.graph_analyzer import analyze
            from wtfcode.reporter import (
                write_product_overview,
                write_critical_path,
                write_failure_report,
                write_token_report,
            )
            import shutil

            out = Path(tmp)
            G, graph_path = load_or_build_graph(REPO_ROOT)
            repo_files = extract_repo_files(G, top_n=10)
            repo_files, scenarios, token_report, repo_intro = analyze(
                G, REPO_ROOT, repo_files, use_llm=False
            )

            graph_stats = {
                "nodes": G.number_of_nodes(),
                "edges": G.number_of_edges(),
                "communities": 5,
                "cross_edge_pct": 20,
            }

            write_product_overview(repo_intro, scenarios, out, REPO_ROOT, graph_stats, token_report)
            write_critical_path(repo_files, out, REPO_ROOT)
            write_failure_report(scenarios, out, REPO_ROOT, token_report, repo_intro)
            write_token_report(token_report, out)
            shutil.copy(graph_path, out / "graph.json")

            yield out

    def test_all_five_files_present(self, output_dir):
        expected = [
            "PRODUCT_OVERVIEW.md",
            "FAILURE_REPORT.md",
            "CRITICAL_PATH.md",
            "tokens_saved.json",
            "graph.json",
        ]
        for name in expected:
            assert (output_dir / name).exists(), f"Missing: {name}"

    def test_product_overview_sections(self, output_dir):
        text = (output_dir / "PRODUCT_OVERVIEW.md").read_text(encoding="utf-8")
        for section in ("## What this is", "## How it's wired", "## Structural stats"):
            assert section in text, f"PRODUCT_OVERVIEW.md missing section: {section}"

    def test_failure_report_sections(self, output_dir):
        text = (output_dir / "FAILURE_REPORT.md").read_text(encoding="utf-8")
        assert "## How this works" in text
        assert "## Where it's weak" in text

    def test_critical_path_has_why_it_matters(self, output_dir):
        text = (output_dir / "CRITICAL_PATH.md").read_text(encoding="utf-8")
        assert "Why it matters" in text
        assert "Don't touch these casually" in text

    def test_tokens_saved_schema(self, output_dir):
        data = json.loads((output_dir / "tokens_saved.json").read_text(encoding="utf-8"))
        for key in ("naive_tokens", "wtfcode_input_tokens", "savings_ratio", "model"):
            assert key in data, f"tokens_saved.json missing key: {key}"
        assert data["naive_tokens"] > 0
        assert data["savings_ratio"] > 1

    def test_graph_json_has_nodes_and_edges(self, output_dir):
        data = json.loads((output_dir / "graph.json").read_text(encoding="utf-8"))
        assert "nodes" in data
        # graphify uses "links" (node-link format); AST-only uses "edges"
        assert "edges" in data or "links" in data
        assert len(data["nodes"]) > 0


# ---------------------------------------------------------------------------
# 3. CLI interface contract
# ---------------------------------------------------------------------------

class TestCLIContract:
    def test_scan_command_exists(self):
        from wtfcode.cli import main
        from click.testing import CliRunner
        runner = CliRunner()
        result = runner.invoke(main, ["scan", "--help"])
        assert result.exit_code == 0

    def test_scan_has_no_llm_flag(self):
        from wtfcode.cli import main
        from click.testing import CliRunner
        runner = CliRunner()
        result = runner.invoke(main, ["scan", "--help"])
        assert "--no-llm" in result.output

    def test_scan_has_output_dir_option(self):
        from wtfcode.cli import main
        from click.testing import CliRunner
        runner = CliRunner()
        result = runner.invoke(main, ["scan", "--help"])
        assert "--output-dir" in result.output

    def test_scan_has_top_option(self):
        from wtfcode.cli import main
        from click.testing import CliRunner
        runner = CliRunner()
        result = runner.invoke(main, ["scan", "--help"])
        assert "--top" in result.output
