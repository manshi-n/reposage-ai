"""
JavaScript / TypeScript static analysis: wraps ESLint (lint/bugs/quality)
and `npm audit` (vulnerable dependencies). Degrades gracefully (returns an
empty list) if the tools or a package.json aren't present, since we don't
want a missing devDependency to fail the whole analysis pipeline.
"""
import json
import os
import subprocess
from typing import Any, Dict, List

TOOL_TIMEOUT_SECONDS = 90


def _run(cmd: List[str], cwd: str) -> str:
    try:
        result = subprocess.run(
            cmd, cwd=cwd, capture_output=True, text=True, timeout=TOOL_TIMEOUT_SECONDS,
        )
        return result.stdout
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return ""


def run_eslint(repo_path: str) -> List[Dict[str, Any]]:
    output = _run(
        ["npx", "--yes", "eslint", ".", "--format", "json", "--ext", ".js,.jsx,.ts,.tsx"],
        cwd=repo_path,
    )
    if not output:
        return []
    try:
        data = json.loads(output)
    except ValueError:
        return []

    issues = []
    for file_result in data:
        rel_path = os.path.relpath(file_result.get("filePath", ""), repo_path)
        for msg in file_result.get("messages", []):
            severity = "high" if msg.get("severity") == 2 else "low"
            rule_id = msg.get("ruleId") or ""
            category = "security" if "security" in rule_id else "code_quality"
            issues.append({
                "title": rule_id or "Lint issue",
                "severity": severity,
                "category": category,
                "file_path": rel_path,
                "line_number": msg.get("line"),
                "language": "JavaScript/TypeScript",
                "description": msg.get("message"),
                "risk": None,
                "suggested_fix": None,
                "generated_patch": None,
                "source_tool": "eslint",
            })
    return issues


def run_npm_audit(repo_path: str) -> List[Dict[str, Any]]:
    if not os.path.exists(os.path.join(repo_path, "package.json")):
        return []
    output = _run(["npm", "audit", "--json"], cwd=repo_path)
    if not output:
        return []
    try:
        data = json.loads(output)
    except ValueError:
        return []

    issues = []
    vulnerabilities = data.get("vulnerabilities", {})
    severity_map = {"critical": "critical", "high": "high", "moderate": "medium", "low": "low"}
    for name, vuln in vulnerabilities.items():
        issues.append({
            "title": f"Vulnerable dependency: {name}",
            "severity": severity_map.get(vuln.get("severity"), "medium"),
            "category": "security",
            "file_path": "package.json",
            "line_number": None,
            "language": "JavaScript/TypeScript",
            "description": f"Package '{name}' has known vulnerabilities (severity: {vuln.get('severity')}).",
            "risk": "Vulnerable dependencies can be exploited by attackers with public CVE details.",
            "suggested_fix": "Run `npm audit fix` or upgrade the package to a patched version.",
            "generated_patch": None,
            "source_tool": "npm-audit",
        })
    return issues


def analyze_javascript(repo_path: str) -> List[Dict[str, Any]]:
    issues: List[Dict[str, Any]] = []
    issues += run_eslint(repo_path)
    issues += run_npm_audit(repo_path)
    return issues
