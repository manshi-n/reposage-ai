"""
AI refactoring agent.

The AI must return one complete corrected source file. The response is
strictly parsed and rejected when it contains explanations, Markdown fences,
multiple alternative implementations, or unsafe/incomplete output.
"""

from __future__ import annotations

import re
from typing import Dict

from app.services.llm_client import ask


class RefactoringError(Exception):
    """Raised when an AI-generated fix cannot be safely accepted."""


SECTION_ORDER = (
    "IMPROVED_CODE",
    "EXPLANATION",
    "SIDE_EFFECTS",
    "IMPROVEMENT",
)


def generate_refactor(
    file_path: str,
    original_code: str,
    issue_description: str,
    language: str,
) -> Dict[str, str]:
    system_prompt = _build_system_prompt(
        language=language,
    )

    user_prompt = (
        f"Target file: {file_path}\n"
        f"Language: {language or 'unknown'}\n"
        f"Issue: {issue_description}\n\n"
        "Complete original file:\n"
        "<<<SOURCE_START>>>\n"
        f"{original_code[:20000]}\n"
        "<<<SOURCE_END>>>"
    )

    raw_response = ask(
        system_prompt,
        user_prompt,
        max_tokens=5000,
    )

    parsed = _parse_response(
        raw_response
    )

    improved_code = _clean_code(
        parsed["IMPROVED_CODE"]
    )

    _validate_generated_code(
        file_path=file_path,
        original_code=original_code,
        improved_code=improved_code,
        language=language,
    )

    return {
        "improved_code": improved_code,
        "explanation": (
            parsed["EXPLANATION"].strip()
            or "The detected issue was corrected while preserving unrelated behavior."
        ),
        "side_effects": (
            parsed["SIDE_EFFECTS"].strip()
            or "None known."
        ),
        "estimated_improvement": (
            parsed["IMPROVEMENT"].strip()
            or "Improves safety and maintainability."
        ),
    }


def _build_system_prompt(
    language: str,
) -> str:
    return (
        f"You are a senior {language or 'software'} engineer.\n"
        "Correct only the supplied issue while preserving unrelated behavior.\n\n"

        "Return exactly four sections in this exact order:\n\n"

        "IMPROVED_CODE:\n"
        "Return the COMPLETE corrected content of the target file.\n"
        "Do not return a diff.\n"
        "Do not omit unchanged code.\n"
        "Do not use Markdown code fences.\n"
        "Do not include explanation inside the code.\n"
        "Do not provide multiple alternative implementations.\n\n"

        "EXPLANATION:\n"
        "Explain the change in two to four sentences.\n\n"

        "SIDE_EFFECTS:\n"
        "Describe anything a reviewer should verify, or write None known.\n\n"

        "IMPROVEMENT:\n"
        "Write one short sentence describing the improvement.\n\n"

        "Accuracy rules:\n"
        "- Do not claim syntax, APIs, CSS units, functions, or properties are "
        "invalid unless the supplied issue and source prove it.\n"
        "- Never invent files, imports, dependencies, functions, variables, "
        "routes, elements, database connections, or configuration.\n"
        "- Use modern, non-deprecated APIs.\n"
        "- If the issue cannot be safely corrected from the supplied source, "
        "write VALIDATION_REQUIRED as the entire IMPROVED_CODE section.\n\n"

        "PHP rules:\n"
        "- Never use FILTER_SANITIZE_STRING.\n"
        "- Read request values with null coalescing, such as "
        "$_POST['field'] ?? ''.\n"
        "- Validate values based on their expected format.\n"
        "- Use strict comparisons where appropriate.\n"
        "- Do not call password_hash during every login attempt.\n"
        "- Do not introduce password_hash or password_verify unless the source "
        "already uses stored password hashes or persistence.\n"
        "- For a simple demonstration with plaintext credentials, preserve the "
        "existing comparison and only improve request handling and validation.\n"
        "- Escape untrusted values with htmlspecialchars when rendering them.\n\n"

        "CSS rules:\n"
        "- Modern units including svh, lvh, dvh, svw, lvw, and dvw are valid.\n"
        "- Do not replace valid modern CSS merely because it is unfamiliar.\n"
    )


def _parse_response(
    raw_response: str,
) -> Dict[str, str]:
    result = {
        section: ""
        for section in SECTION_ORDER
    }

    current_section: str | None = None

    for raw_line in raw_response.splitlines():
        normalized = _normalize_heading(
            raw_line
        )

        if normalized in SECTION_ORDER:
            current_section = normalized
            continue

        if current_section:
            result[current_section] += (
                raw_line + "\n"
            )

    if not result["IMPROVED_CODE"].strip():
        raise RefactoringError(
            "The AI response did not contain a valid IMPROVED_CODE section."
        )

    return result


def _normalize_heading(
    line: str,
) -> str:
    normalized = line.strip()

    normalized = re.sub(
        r"^[#*\-\s]+",
        "",
        normalized,
    )

    normalized = re.sub(
        r"[*:\s]+$",
        "",
        normalized,
    )

    return normalized.strip().upper()


def _clean_code(
    content: str,
) -> str:
    cleaned = content.strip()

    cleaned = re.sub(
        r"^\s*```[a-zA-Z0-9_+#.-]*\s*\n?",
        "",
        cleaned,
        count=1,
    )

    cleaned = re.sub(
        r"\n?\s*```\s*$",
        "",
        cleaned,
        count=1,
    )

    cleaned = cleaned.strip()

    if "```" in cleaned:
        raise RefactoringError(
            "Generated code contains an unexpected Markdown code fence."
        )

    if re.search(
        r"(?im)^\s*(however|here is the corrected version|alternative|explanation)\s*[:.]?",
        cleaned,
    ):
        raise RefactoringError(
            "Generated code contains explanatory text or multiple alternatives."
        )

    return cleaned


def _validate_generated_code(
    file_path: str,
    original_code: str,
    improved_code: str,
    language: str,
) -> None:
    if not improved_code:
        raise RefactoringError(
            "The generated patch is empty."
        )

    if improved_code.strip() == "VALIDATION_REQUIRED":
        raise RefactoringError(
            "The AI could not produce a fix with sufficient confidence."
        )

    if len(improved_code) > max(
        len(original_code) * 4,
        len(original_code) + 12000,
    ):
        raise RefactoringError(
            "The generated patch is unexpectedly large."
        )

    normalized_language = (
        language or ""
    ).strip().lower()

    extension = file_path.lower().rsplit(
        ".",
        1,
    )[-1]

    if (
        normalized_language == "php"
        or extension == "php"
    ):
        _validate_php(
            improved_code
        )

    if extension in {
        "html",
        "htm",
    }:
        if (
            "<html" in original_code.lower()
            and "<html" not in improved_code.lower()
        ):
            raise RefactoringError(
                "The generated HTML patch removed the document root."
            )


def _validate_php(
    code: str,
) -> None:
    lowered = code.lower()

    if "<?php" not in lowered:
        raise RefactoringError(
            "The generated PHP patch does not contain a PHP opening tag."
        )

    forbidden_patterns = {
        "filter_sanitize_string": (
            "FILTER_SANITIZE_STRING is deprecated."
        ),
        "password_verify($pwd, password_hash(": (
            "The generated patch hashes the password during every verification."
        ),
        "here is the corrected version": (
            "The generated patch contains explanation text."
        ),
    }

    for pattern, message in (
        forbidden_patterns.items()
    ):
        if pattern in lowered:
            raise RefactoringError(
                message
            )