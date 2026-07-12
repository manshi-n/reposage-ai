"""
HTML static checks.
"""

from __future__ import annotations

import os
import re
from typing import Any, Dict, List


def analyze_html(
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

        full_content = "".join(lines).lower()

        for line_number, line in enumerate(
            lines,
            start=1,
        ):
            lowered = line.lower()

            if (
                "<img" in lowered
                and "alt=" not in lowered
            ):
                issues.append(
                    _issue(
                        title="Image missing alt text",
                        severity="low",
                        category="code_quality",
                        file_path=relative_path,
                        line_number=line_number,
                        description=(
                            "Image elements should include "
                            "meaningful alternative text."
                        ),
                        suggested_fix=(
                            "Add an alt attribute that "
                            "describes the image."
                        ),
                    )
                )

            if re.search(
                r"\son\w+\s*=",
                lowered,
            ):
                issues.append(
                    _issue(
                        title=(
                            "Inline JavaScript event handler"
                        ),
                        severity="low",
                        category="code_quality",
                        file_path=relative_path,
                        line_number=line_number,
                        description=(
                            "Inline event handlers mix "
                            "markup and behavior."
                        ),
                        suggested_fix=(
                            "Move event logic into a "
                            "JavaScript module and register "
                            "the listener with addEventListener."
                        ),
                    )
                )

            if (
                'target="_blank"'
                in lowered
                and "noopener" not in lowered
            ):
                issues.append(
                    _issue(
                        title=(
                            "External link missing noopener"
                        ),
                        severity="low",
                        category="security",
                        file_path=relative_path,
                        line_number=line_number,
                        description=(
                            "A new-tab link without noopener "
                            "may expose window.opener."
                        ),
                        suggested_fix=(
                            'Add rel="noopener noreferrer".'
                        ),
                    )
                )

            if (
                "<input" in lowered
                and "type=" not in lowered
            ):
                issues.append(
                    _issue(
                        title=(
                            "Input element missing explicit type"
                        ),
                        severity="low",
                        category="code_quality",
                        file_path=relative_path,
                        line_number=line_number,
                        description=(
                            "Input behavior may be unclear "
                            "without an explicit type."
                        ),
                        suggested_fix=(
                            "Set a suitable input type such "
                            "as text, email, number, or password."
                        ),
                    )
                )

            if (
                "<script" in lowered
                and "src=" in lowered
                and "defer" not in lowered
                and "async" not in lowered
            ):
                issues.append(
                    _issue(
                        title=(
                            "Blocking external script"
                        ),
                        severity="low",
                        category="performance",
                        file_path=relative_path,
                        line_number=line_number,
                        description=(
                            "An external script in the document "
                            "head may block HTML parsing."
                        ),
                        suggested_fix=(
                            "Use defer or move the script "
                            "before the closing body tag."
                        ),
                    )
                )

        if (
            "<html" in full_content
            and 'lang="' not in full_content
        ):
            issues.append(
                _issue(
                    title=(
                        "HTML document missing language"
                    ),
                    severity="low",
                    category="code_quality",
                    file_path=relative_path,
                    line_number=1,
                    description=(
                        "The root html element has no "
                        "language declaration."
                    ),
                    suggested_fix=(
                        'Add lang="en" or the correct '
                        "document language."
                    ),
                )
            )

    return issues


def _issue(
    title: str,
    severity: str,
    category: str,
    file_path: str,
    line_number: int | None,
    description: str,
    suggested_fix: str,
) -> Dict[str, Any]:
    return {
        "title": title,
        "severity": severity,
        "category": category,
        "file_path": file_path,
        "line_number": line_number,
        "language": "HTML",
        "description": description,
        "risk": None,
        "suggested_fix": suggested_fix,
        "generated_patch": None,
        "source_tool": (
            "reposage-html-checks"
        ),
    }