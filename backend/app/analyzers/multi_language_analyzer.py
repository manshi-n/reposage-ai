"""
Lightweight cross-language static checks.

This analyzer supports languages where a dedicated external analyzer may
not be installed. It performs deterministic source-pattern checks without
executing repository code.
"""

from __future__ import annotations

import os
import re
from typing import Any, Dict, Iterable, List


IssueDict = Dict[str, Any]


COMMON_PATTERNS = [
    {
        "pattern": re.compile(
            r"\bTODO\b|\bFIXME\b",
            re.IGNORECASE,
        ),
        "title": "Unresolved TODO or FIXME",
        "severity": "info",
        "category": "code_quality",
        "description": (
            "The source contains an unresolved "
            "TODO or FIXME marker."
        ),
        "suggested_fix": (
            "Resolve the task or link it to a "
            "tracked issue."
        ),
    },
    {
        "pattern": re.compile(
            r"(?i)(password|secret|api[_-]?key)"
            r"\s*[:=]\s*[\"'][^\"']{6,}[\"']"
        ),
        "title": "Possible hard-coded secret",
        "severity": "high",
        "category": "security",
        "description": (
            "A value that resembles a credential "
            "is hard-coded in source code."
        ),
        "suggested_fix": (
            "Move credentials into environment "
            "variables or a secret manager."
        ),
    },
]


LANGUAGE_PATTERNS: Dict[
    str,
    List[Dict[str, Any]],
] = {
    "JavaScript": [
        {
            "text": "eval(",
            "title": "Unsafe eval usage",
            "severity": "high",
            "category": "security",
            "description": (
                "eval can execute attacker-controlled "
                "JavaScript."
            ),
            "suggested_fix": (
                "Replace eval with explicit parsing "
                "or controlled function calls."
            ),
        },
        {
            "text": ".innerHTML",
            "title": "Potential unsafe HTML injection",
            "severity": "medium",
            "category": "security",
            "description": (
                "innerHTML can introduce cross-site "
                "scripting when used with untrusted data."
            ),
            "suggested_fix": (
                "Prefer textContent or sanitize HTML "
                "before rendering."
            ),
        },
        {
            "text": "console.log(",
            "title": "Debug logging left in source",
            "severity": "low",
            "category": "code_quality",
            "description": (
                "Debug logging may expose implementation "
                "details and clutter production output."
            ),
            "suggested_fix": (
                "Remove the statement or use a structured "
                "logger with environment-based levels."
            ),
        },
        {
            "text": "document.querySelector",
            "title": "Repeated DOM lookup may affect performance",
            "severity": "low",
            "category": "performance",
            "description": (
                "Repeated DOM queries inside frequently "
                "called code may cause unnecessary work."
            ),
            "suggested_fix": (
                "Cache stable DOM references when the "
                "same element is accessed repeatedly."
            ),
        },
    ],
    "React": [
        {
            "text": "dangerouslySetInnerHTML",
            "title": "Unsafe React HTML rendering",
            "severity": "high",
            "category": "security",
            "description": (
                "dangerouslySetInnerHTML can create an "
                "XSS vulnerability."
            ),
            "suggested_fix": (
                "Avoid raw HTML or sanitize content "
                "with a trusted library."
            ),
        },
        {
            "text": "console.log(",
            "title": "Debug logging left in React code",
            "severity": "low",
            "category": "code_quality",
            "description": (
                "Debug output should normally be removed "
                "from production components."
            ),
            "suggested_fix": (
                "Remove the log or use a structured logger."
            ),
        },
    ],
    "TypeScript": [
        {
            "text": ": any",
            "title": "Use of any weakens type safety",
            "severity": "low",
            "category": "code_quality",
            "description": (
                "The any type disables useful compile-time "
                "checks."
            ),
            "suggested_fix": (
                "Replace any with an interface, generic, "
                "union, or unknown."
            ),
        },
        {
            "text": "eval(",
            "title": "Unsafe eval usage",
            "severity": "high",
            "category": "security",
            "description": (
                "eval executes arbitrary JavaScript."
            ),
            "suggested_fix": (
                "Use explicit parsing or controlled logic."
            ),
        },
    ],
    "React TypeScript": [
        {
            "text": "dangerouslySetInnerHTML",
            "title": "Unsafe React HTML rendering",
            "severity": "high",
            "category": "security",
            "description": (
                "Raw HTML rendering can introduce XSS."
            ),
            "suggested_fix": (
                "Avoid raw HTML or sanitize it before use."
            ),
        },
        {
            "text": ": any",
            "title": "Use of any weakens type safety",
            "severity": "low",
            "category": "code_quality",
            "description": (
                "The any type bypasses TypeScript checks."
            ),
            "suggested_fix": (
                "Use a specific interface or unknown."
            ),
        },
    ],
    "Java": [
        {
            "text": "System.out.println(",
            "title": "Console output in application code",
            "severity": "low",
            "category": "code_quality",
            "description": (
                "System.out.println is generally unsuitable "
                "for production logging."
            ),
            "suggested_fix": (
                "Use SLF4J, Log4j, java.util.logging, "
                "or another structured logger."
            ),
        },
        {
            "text": "Runtime.getRuntime().exec(",
            "title": "Operating system command execution",
            "severity": "high",
            "category": "security",
            "description": (
                "Executing shell commands with dynamic "
                "input can cause command injection."
            ),
            "suggested_fix": (
                "Avoid shell execution or strictly validate "
                "and allow-list every argument."
            ),
        },
        {
            "text": "new Random(",
            "title": "Non-cryptographic random generator",
            "severity": "medium",
            "category": "security",
            "description": (
                "java.util.Random must not be used for "
                "security-sensitive values."
            ),
            "suggested_fix": (
                "Use SecureRandom for tokens, passwords, "
                "or security-related identifiers."
            ),
        },
    ],
    "C": [
        {
            "text": "gets(",
            "title": "Unsafe gets function",
            "severity": "critical",
            "category": "security",
            "description": (
                "gets cannot limit input length and can "
                "cause buffer overflows."
            ),
            "suggested_fix": (
                "Use fgets with an explicit buffer size."
            ),
        },
        {
            "text": "strcpy(",
            "title": "Potential unsafe string copy",
            "severity": "high",
            "category": "security",
            "description": (
                "strcpy does not validate destination size."
            ),
            "suggested_fix": (
                "Use a bounded copy operation and verify "
                "buffer capacity."
            ),
        },
        {
            "text": "sprintf(",
            "title": "Potential unbounded formatting",
            "severity": "high",
            "category": "security",
            "description": (
                "sprintf may overflow the destination buffer."
            ),
            "suggested_fix": (
                "Use snprintf with an explicit buffer size."
            ),
        },
    ],
    "C++": [
        {
            "text": "strcpy(",
            "title": "Potential unsafe string copy",
            "severity": "high",
            "category": "security",
            "description": (
                "strcpy does not enforce destination size."
            ),
            "suggested_fix": (
                "Prefer std::string or bounded copy logic."
            ),
        },
        {
            "text": "new ",
            "title": "Manual memory allocation",
            "severity": "low",
            "category": "code_quality",
            "description": (
                "Manual allocation increases memory-leak "
                "and exception-safety risks."
            ),
            "suggested_fix": (
                "Prefer RAII and smart pointers such as "
                "std::unique_ptr."
            ),
        },
    ],
    "C/C++ Header": [],
    "C#": [
        {
            "text": "Console.WriteLine(",
            "title": "Console output in application code",
            "severity": "low",
            "category": "code_quality",
            "description": (
                "Console output is usually not suitable "
                "for production logging."
            ),
            "suggested_fix": (
                "Use ILogger or another structured logger."
            ),
        },
        {
            "text": "Process.Start(",
            "title": "External process execution",
            "severity": "high",
            "category": "security",
            "description": (
                "External process execution can become a "
                "command-injection risk."
            ),
            "suggested_fix": (
                "Use allow-listed commands and validate "
                "all arguments."
            ),
        },
    ],
    "Go": [
        {
            "text": "exec.Command(",
            "title": "External command execution",
            "severity": "high",
            "category": "security",
            "description": (
                "Dynamic command arguments can cause "
                "command injection."
            ),
            "suggested_fix": (
                "Avoid user-controlled command input and "
                "allow-list every executable."
            ),
        },
        {
            "text": "fmt.Println(",
            "title": "Console logging in application code",
            "severity": "low",
            "category": "code_quality",
            "description": (
                "Plain console output offers limited "
                "structure and filtering."
            ),
            "suggested_fix": (
                "Use a structured logger such as slog, "
                "zap, or zerolog."
            ),
        },
    ],
    "Rust": [
        {
            "text": "unwrap()",
            "title": "Potential panic from unwrap",
            "severity": "medium",
            "category": "bug",
            "description": (
                "unwrap will panic when the Result or "
                "Option contains an error or None."
            ),
            "suggested_fix": (
                "Handle the error using match, ?, "
                "unwrap_or, or a meaningful fallback."
            ),
        },
        {
            "text": "unsafe {",
            "title": "Unsafe Rust block",
            "severity": "medium",
            "category": "security",
            "description": (
                "Unsafe code bypasses Rust memory-safety "
                "guarantees."
            ),
            "suggested_fix": (
                "Minimize the unsafe block and document "
                "the safety invariants."
            ),
        },
    ],
    "Kotlin": [
        {
            "text": "!!",
            "title": "Unsafe Kotlin non-null assertion",
            "severity": "medium",
            "category": "bug",
            "description": (
                "The !! operator can throw a "
                "NullPointerException."
            ),
            "suggested_fix": (
                "Use safe calls, Elvis operators, or "
                "explicit null handling."
            ),
        },
        {
            "text": "println(",
            "title": "Console output in application code",
            "severity": "low",
            "category": "code_quality",
            "description": (
                "Console output is not ideal for "
                "production diagnostics."
            ),
            "suggested_fix": (
                "Use a structured logging framework."
            ),
        },
    ],
    "Swift": [
        {
            "text": "try!",
            "title": "Forced Swift error handling",
            "severity": "medium",
            "category": "bug",
            "description": (
                "try! terminates the application when "
                "the operation throws."
            ),
            "suggested_fix": (
                "Use do/catch, try?, or propagate the error."
            ),
        },
        {
            "text": " as!",
            "title": "Forced Swift type cast",
            "severity": "medium",
            "category": "bug",
            "description": (
                "A forced cast crashes when the value has "
                "an unexpected type."
            ),
            "suggested_fix": (
                "Use optional casting with as? and handle "
                "the failure."
            ),
        },
    ],
    "Ruby": [
        {
            "text": "eval(",
            "title": "Unsafe Ruby eval usage",
            "severity": "high",
            "category": "security",
            "description": (
                "eval executes arbitrary Ruby code."
            ),
            "suggested_fix": (
                "Use explicit parsing or controlled "
                "dispatch logic."
            ),
        },
        {
            "text": "system(",
            "title": "Shell command execution",
            "severity": "high",
            "category": "security",
            "description": (
                "Shell commands may be injectable when "
                "arguments contain untrusted data."
            ),
            "suggested_fix": (
                "Avoid shell execution or strictly "
                "allow-list arguments."
            ),
        },
    ],
}


def analyze_language_files(
    repo_path: str,
    language: str,
    files: Iterable[str],
) -> List[IssueDict]:
    issues: List[IssueDict] = []

    patterns = LANGUAGE_PATTERNS.get(
        language,
        [],
    )

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
            for common_rule in COMMON_PATTERNS:
                if common_rule["pattern"].search(
                    line
                ):
                    issues.append(
                        _make_issue(
                            rule=common_rule,
                            language=language,
                            file_path=relative_path,
                            line_number=line_number,
                            source_tool=(
                                "reposage-common-checks"
                            ),
                        )
                    )

            for rule in patterns:
                if rule["text"] in line:
                    issues.append(
                        _make_issue(
                            rule=rule,
                            language=language,
                            file_path=relative_path,
                            line_number=line_number,
                            source_tool=(
                                "reposage-"
                                f"{language.lower().replace(' ', '-')}"
                                "-checks"
                            ),
                        )
                    )

        issues.extend(
            _file_level_checks(
                relative_path=relative_path,
                language=language,
                lines=lines,
            )
        )

    return _deduplicate_issues(issues)


def _file_level_checks(
    relative_path: str,
    language: str,
    lines: List[str],
) -> List[IssueDict]:
    issues: List[IssueDict] = []

    if len(lines) > 600:
        issues.append(
            {
                "title": "Very large source file",
                "severity": "medium",
                "category": "code_quality",
                "file_path": relative_path,
                "line_number": None,
                "language": language,
                "description": (
                    f"The file contains {len(lines)} lines, "
                    "which may make it difficult to maintain."
                ),
                "risk": None,
                "suggested_fix": (
                    "Split the file into smaller modules, "
                    "classes, or functions."
                ),
                "generated_patch": None,
                "source_tool": (
                    "reposage-file-size-check"
                ),
            }
        )

    nested_loop_count = _count_nested_loops(
        language,
        lines,
    )

    if nested_loop_count > 0:
        issues.append(
            {
                "title": "Potential nested-loop performance issue",
                "severity": "medium",
                "category": "performance",
                "file_path": relative_path,
                "line_number": None,
                "language": language,
                "description": (
                    "Nested loops may lead to quadratic "
                    "or worse execution time."
                ),
                "risk": (
                    "Performance may degrade as input "
                    "size increases."
                ),
                "suggested_fix": (
                    "Consider using a map, set, index, "
                    "precomputation, or a more efficient "
                    "algorithm."
                ),
                "generated_patch": None,
                "source_tool": (
                    "reposage-performance-checks"
                ),
            }
        )

    return issues


def _count_nested_loops(
    language: str,
    lines: List[str],
) -> int:
    loop_tokens = {
        "Python": (
            "for ",
            "while ",
        ),
        "JavaScript": (
            "for (",
            "for(",
            "while (",
            "while(",
        ),
        "React": (
            "for (",
            "for(",
            ".map(",
        ),
        "TypeScript": (
            "for (",
            "for(",
            "while (",
        ),
        "React TypeScript": (
            "for (",
            "for(",
            ".map(",
        ),
        "Java": (
            "for (",
            "for(",
            "while (",
        ),
        "C": (
            "for (",
            "for(",
            "while (",
        ),
        "C++": (
            "for (",
            "for(",
            "while (",
        ),
        "C#": (
            "for (",
            "foreach (",
            "while (",
        ),
        "Go": (
            "for ",
        ),
        "Rust": (
            "for ",
            "while ",
        ),
        "Kotlin": (
            "for (",
            "while (",
        ),
        "Swift": (
            "for ",
            "while ",
        ),
        "Ruby": (
            ".each do",
            "while ",
            "for ",
        ),
    }

    tokens = loop_tokens.get(
        language,
        (),
    )

    if not tokens:
        return 0

    previous_loop_indent: int | None = None
    nested_count = 0

    for line in lines:
        stripped = line.strip()

        if not stripped:
            continue

        is_loop = any(
            token in stripped
            for token in tokens
        )

        if not is_loop:
            continue

        indentation = len(line) - len(
            line.lstrip()
        )

        if (
            previous_loop_indent is not None
            and indentation
            > previous_loop_indent
        ):
            nested_count += 1

        previous_loop_indent = indentation

    return nested_count


def _make_issue(
    rule: Dict[str, Any],
    language: str,
    file_path: str,
    line_number: int,
    source_tool: str,
) -> IssueDict:
    return {
        "title": rule["title"],
        "severity": rule["severity"],
        "category": rule["category"],
        "file_path": file_path,
        "line_number": line_number,
        "language": language,
        "description": rule["description"],
        "risk": rule.get("risk"),
        "suggested_fix": rule.get(
            "suggested_fix"
        ),
        "generated_patch": None,
        "source_tool": source_tool,
    }


def _deduplicate_issues(
    issues: List[IssueDict],
) -> List[IssueDict]:
    output: List[IssueDict] = []
    seen = set()

    for issue in issues:
        key = (
            issue.get("title"),
            issue.get("file_path"),
            issue.get("line_number"),
            issue.get("source_tool"),
        )

        if key in seen:
            continue

        seen.add(key)
        output.append(issue)

    return output