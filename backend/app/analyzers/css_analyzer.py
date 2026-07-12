"""
CSS, SCSS, Sass and Less static checks.
"""

from __future__ import annotations

import os
import re
from typing import Any, Dict, List


def analyze_css(
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

        issues.extend(
            _analyze_file(
                relative_path,
                lines,
            )
        )

    return issues


def _analyze_file(
    relative_path: str,
    lines: List[str],
) -> List[Dict[str, Any]]:
    issues: List[Dict[str, Any]] = []

    brace_depth = 0
    in_comment = False
    current_properties: dict[
        str,
        int,
    ] = {}

    for line_number, raw_line in enumerate(
        lines,
        start=1,
    ):
        line, in_comment = _remove_comments(
            raw_line,
            in_comment,
        )

        stripped = line.strip()

        if not stripped:
            continue

        if "!important" in stripped:
            issues.append(
                _issue(
                    title="Use of !important",
                    severity="low",
                    category="code_quality",
                    file_path=relative_path,
                    line_number=line_number,
                    description=(
                        "!important makes the CSS cascade "
                        "harder to understand and override."
                    ),
                    suggested_fix=(
                        "Improve selector specificity, "
                        "component scoping, or source order."
                    ),
                )
            )

        opening_braces = stripped.count("{")
        closing_braces = stripped.count("}")

        if opening_braces:
            current_properties = {}

        inside_rule = (
            brace_depth > 0
            or opening_braces > 0
        )

        if (
            inside_rule
            and _looks_like_declaration(
                stripped
            )
        ):
            property_name = stripped.split(
                ":",
                1,
            )[0].strip().lower()

            if property_name in current_properties:
                issues.append(
                    _issue(
                        title=(
                            "Duplicate CSS property "
                            "in the same rule"
                        ),
                        severity="low",
                        category="code_quality",
                        file_path=relative_path,
                        line_number=line_number,
                        description=(
                            f"The '{property_name}' property "
                            "appears more than once in the same "
                            "rule and may unintentionally "
                            "override an earlier value."
                        ),
                        suggested_fix=(
                            "Remove the duplicate declaration "
                            "or document why the override is "
                            "required."
                        ),
                    )
                )

            current_properties[
                property_name
            ] = line_number

            if _declaration_missing_semicolon(
                stripped
            ):
                issues.append(
                    _issue(
                        title=(
                            "CSS declaration may be "
                            "missing semicolon"
                        ),
                        severity="low",
                        category="bug",
                        file_path=relative_path,
                        line_number=line_number,
                        description=(
                            "The declaration appears to end "
                            "without a semicolon."
                        ),
                        suggested_fix=(
                            "Add a semicolon after the "
                            "property value."
                        ),
                    )
                )

        brace_depth += (
            opening_braces
            - closing_braces
        )

        brace_depth = max(
            brace_depth,
            0,
        )

        if closing_braces:
            current_properties = {}

    if len(lines) > 800:
        issues.append(
            _issue(
                title="Very large stylesheet",
                severity="medium",
                category="code_quality",
                file_path=relative_path,
                line_number=None,
                description=(
                    f"The stylesheet contains "
                    f"{len(lines)} lines."
                ),
                suggested_fix=(
                    "Split the stylesheet by component, "
                    "feature, or page."
                ),
            )
        )

    return issues


def _remove_comments(
    line: str,
    in_comment: bool,
) -> tuple[str, bool]:
    output = ""
    index = 0

    while index < len(line):
        if in_comment:
            end = line.find(
                "*/",
                index,
            )

            if end == -1:
                return output, True

            in_comment = False
            index = end + 2
            continue

        start = line.find(
            "/*",
            index,
        )

        if start == -1:
            output += line[index:]
            break

        output += line[
            index:start
        ]

        index = start + 2
        in_comment = True

    return output, in_comment


def _looks_like_declaration(
    stripped: str,
) -> bool:
    if ":" not in stripped:
        return False

    if stripped.startswith(
        (
            "@",
            "http://",
            "https://",
        )
    ):
        return False

    if stripped.endswith("{"):
        return False

    property_name = stripped.split(
        ":",
        1,
    )[0].strip()

    return bool(
        re.fullmatch(
            r"--[a-zA-Z0-9_-]+"
            r"|[a-zA-Z-]+",
            property_name,
        )
    )


def _declaration_missing_semicolon(
    stripped: str,
) -> bool:
    normalized = stripped.strip()

    if not normalized:
        return False

    if normalized.startswith(
        (
            "/*",
            "*",
            "//",
            "@",
        )
    ):
        return False

    if normalized.endswith(
        (
            ";",
            "{",
            "}",
            ",",
            ":",
        )
    ):
        return False

    if ":" not in normalized:
        return False

    property_name, value = normalized.split(
        ":",
        1,
    )

    property_name = property_name.strip()
    value = value.strip()

    if not re.fullmatch(
        r"--[a-zA-Z0-9_-]+|[a-zA-Z-]+",
        property_name,
    ):
        return False

    # A line such as "--shadow:" begins a multiline value.
    if not value:
        return False

    # Multiline functions such as gradients and calc().
    if normalized.count("(") != normalized.count(")"):
        return False

    # Continued lists or multiline values.
    if normalized.endswith(
        (
            "\\",
            ")",
        )
    ):
        return False

    return True


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
        "language": "CSS",
        "description": description,
        "risk": None,
        "suggested_fix": suggested_fix,
        "generated_patch": None,
        "source_tool": (
            "reposage-css-checks"
        ),
    }