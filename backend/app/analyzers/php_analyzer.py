"""
PHP static source checks.
"""

from __future__ import annotations

import os
import re
from typing import Any, Dict, List


PHP_RULES = [
    {
        "pattern": re.compile(
            r"\$_GET\s*\["
        ),
        "title": "Direct GET input usage",
        "severity": "medium",
        "category": "security",
        "description": (
            "GET input is used directly and may "
            "not be validated or sanitized."
        ),
        "suggested_fix": (
            "Validate input with filter_input or "
            "an explicit allow-list."
        ),
    },
    {
        "pattern": re.compile(
            r"\$_POST\s*\["
        ),
        "title": "Direct POST input usage",
        "severity": "medium",
        "category": "security",
        "description": (
            "POST input is used directly and may "
            "not be validated or sanitized."
        ),
        "suggested_fix": (
            "Validate and sanitize every field "
            "before use."
        ),
    },
    {
        "pattern": re.compile(
            r"\$_REQUEST\s*\["
        ),
        "title": "Unsafe REQUEST input usage",
        "severity": "high",
        "category": "security",
        "description": (
            "$_REQUEST combines multiple untrusted "
            "input sources."
        ),
        "suggested_fix": (
            "Use the specific input source and "
            "validate it explicitly."
        ),
    },
    {
        "pattern": re.compile(
            r"\bmysql_query\s*\("
        ),
        "title": "Deprecated MySQL API",
        "severity": "high",
        "category": "security",
        "description": (
            "mysql_query is removed from modern PHP "
            "and commonly leads to insecure queries."
        ),
        "suggested_fix": (
            "Use PDO or MySQLi with prepared statements."
        ),
    },
    {
        "pattern": re.compile(
            r"\beval\s*\("
        ),
        "title": "Unsafe PHP eval usage",
        "severity": "critical",
        "category": "security",
        "description": (
            "eval executes arbitrary PHP code."
        ),
        "suggested_fix": (
            "Replace dynamic code execution with "
            "explicit application logic."
        ),
    },
    {
        "pattern": re.compile(
            r"\b(shell_exec|exec|system|passthru)\s*\("
        ),
        "title": "Operating system command execution",
        "severity": "high",
        "category": "security",
        "description": (
            "Shell execution can become a command "
            "injection vulnerability."
        ),
        "suggested_fix": (
            "Avoid shell execution or allow-list all "
            "commands and arguments."
        ),
    },
    {
        "pattern": re.compile(
            r"\becho\s+\$_(GET|POST|REQUEST)"
        ),
        "title": "Potential reflected XSS",
        "severity": "high",
        "category": "security",
        "description": (
            "Request data appears to be rendered "
            "without output escaping."
        ),
        "suggested_fix": (
            "Escape output with htmlspecialchars "
            "and validate the input."
        ),
    },
    {
        "pattern": re.compile(
            r"SELECT\s+.*\.\s*\$_",
            re.IGNORECASE,
        ),
        "title": "Potential SQL injection",
        "severity": "critical",
        "category": "security",
        "description": (
            "User-controlled input may be concatenated "
            "into a SQL query."
        ),
        "suggested_fix": (
            "Use prepared statements and bound parameters."
        ),
    },
]


def analyze_php(
    repo_path: str,
    files: List[str],
) -> List[Dict[str, Any]]:
    issues: List[Dict[str, Any]] = []

    for relative_path in files:
        full_path = os.path.join(
            repo_path,
            relative_path,
        )

        try:
            with open(
                full_path,
                "r",
                encoding="utf-8",
                errors="ignore",
            ) as source_file:
                lines = source_file.readlines()

        except OSError:
            continue

        for line_number, line in enumerate(
            lines,
            start=1,
        ):
            for rule in PHP_RULES:
                if rule["pattern"].search(line):
                    issues.append(
                        {
                            "title": rule["title"],
                            "severity": rule["severity"],
                            "category": rule["category"],
                            "file_path": relative_path,
                            "line_number": line_number,
                            "language": "PHP",
                            "description": (
                                rule["description"]
                            ),
                            "risk": None,
                            "suggested_fix": (
                                rule["suggested_fix"]
                            ),
                            "generated_patch": None,
                            "source_tool": (
                                "reposage-php-checks"
                            ),
                        }
                    )

        if len(lines) > 600:
            issues.append(
                {
                    "title": "Very large PHP file",
                    "severity": "medium",
                    "category": "code_quality",
                    "file_path": relative_path,
                    "line_number": None,
                    "language": "PHP",
                    "description": (
                        f"The file contains "
                        f"{len(lines)} lines."
                    ),
                    "risk": None,
                    "suggested_fix": (
                        "Split it into controllers, "
                        "services, helpers, or classes."
                    ),
                    "generated_patch": None,
                    "source_tool": (
                        "reposage-php-checks"
                    ),
                }
            )

    return issues