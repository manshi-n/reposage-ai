"""
Python static analysis: wraps Bandit (security), Ruff (lint/bugs/quality),
and Radon (complexity). Each tool is invoked as a subprocess against the
cloned repo and results are normalized into the common issue dict shape
used everywhere else in the pipeline.

Every subprocess call is bounded by a timeout and never touches network
access or executes repository code - it only reads and parses source.
"""
import json
import subprocess
from typing import Any, Dict, List

TOOL_TIMEOUT_SECONDS = 60


def _run(cmd: List[str], cwd: str) -> str:
    try:
        result = subprocess.run(
            cmd, cwd=cwd, capture_output=True, text=True, timeout=TOOL_TIMEOUT_SECONDS,
        )
        return result.stdout
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return ""


def run_bandit(repo_path: str) -> List[Dict[str, Any]]:
    """Security issues in Python source, e.g. hard-coded secrets, unsafe eval, etc."""
    output = _run(["bandit", "-r", ".", "-f", "json", "-q"], cwd=repo_path)
    if not output:
        return []
    try:
        data = json.loads(output)
    except ValueError:
        return []

    issues = []
    severity_map = {"HIGH": "high", "MEDIUM": "medium", "LOW": "low"}
    for r in data.get("results", []):
        issues.append({
            "title": r.get("test_name", "Security issue"),
            "severity": severity_map.get(r.get("issue_severity"), "medium"),
            "category": "security",
            "file_path": r.get("filename", "").lstrip("./"),
            "line_number": r.get("line_number"),
            "language": "Python",
            "description": r.get("issue_text"),
            "risk": f"Confidence: {r.get('issue_confidence', 'UNKNOWN')}",
            "suggested_fix": None,
            "generated_patch": None,
            "source_tool": "bandit",
        })
    return issues


def run_ruff(repo_path: str) -> List[Dict[str, Any]]:
    """Lint / bug / code-quality issues in Python source."""
    output = _run(["ruff", "check", ".", "--output-format", "json"], cwd=repo_path)
    if not output:
        return []
    try:
        data = json.loads(output)
    except ValueError:
        return []

    issues = []
    for r in data:
        code = r.get("code", "")
        category = "bug" if code.startswith(("F", "E7", "E9")) else "code_quality"
        issues.append({
            "title": r.get("message", "Lint issue"),
            "severity": "medium" if category == "bug" else "low",
            "category": category,
            "file_path": r.get("filename", "").lstrip("./"),
            "line_number": (r.get("location") or {}).get("row"),
            "language": "Python",
            "description": f"[{code}] {r.get('message')}",
            "risk": None,
            "suggested_fix": r.get("fix", {}).get("message") if r.get("fix") else None,
            "generated_patch": None,
            "source_tool": "ruff",
        })
    return issues


def run_radon_complexity(repo_path: str) -> List[Dict[str, Any]]:
    """Flags functions with high cyclomatic complexity as maintainability issues."""
    output = _run(["radon", "cc", ".", "-j"], cwd=repo_path)
    if not output:
        return []
    try:
        data = json.loads(output)
    except ValueError:
        return []

    issues = []
    for file_path, blocks in data.items():
        for block in blocks:
            complexity = block.get("complexity", 0)
            if complexity >= 10:
                issues.append({
                    "title": f"High cyclomatic complexity in `{block.get('name')}`",
                    "severity": "high" if complexity >= 20 else "medium",
                    "category": "code_quality",
                    "file_path": file_path.lstrip("./"),
                    "line_number": block.get("lineno"),
                    "language": "Python",
                    "description": (
                        f"Function/method '{block.get('name')}' has a cyclomatic "
                        f"complexity of {complexity}, making it hard to test and reason about."
                    ),
                    "risk": "High complexity correlates with more bugs and higher maintenance cost.",
                    "suggested_fix": "Break the function into smaller, single-purpose functions.",
                    "generated_patch": None,
                    "source_tool": "radon",
                })
    return issues


def analyze_python(repo_path: str) -> List[Dict[str, Any]]:
    issues: List[Dict[str, Any]] = []
    issues += run_bandit(repo_path)
    issues += run_ruff(repo_path)
    issues += run_radon_complexity(repo_path)
    return issues
