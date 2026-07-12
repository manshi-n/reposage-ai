"""
Multi-language AI test-generation agent.

Generated tests are returned as text. They are not executed automatically,
so every result is explicitly described as AI-generated and unverified.
"""

from __future__ import annotations

import os
import re
from typing import Optional

from app.services.llm_client import ask


LANGUAGE_FRAMEWORK_MAP = {
    "Python": "pytest",
    "JavaScript": "Vitest",
    "React": "Vitest + React Testing Library",
    "TypeScript": "Vitest",
    "React TypeScript": (
        "Vitest + React Testing Library"
    ),
    "Java": "JUnit 5",
    "C": "Unity Test Framework",
    "C++": "GoogleTest",
    "C/C++ Header": "GoogleTest",
    "Go": "Go testing package",
    "Ruby": "RSpec",
    "PHP": "PHPUnit",
    "C#": "xUnit",
    "Rust": "Rust built-in tests",
    "Kotlin": "JUnit 5",
    "Swift": "XCTest",
    "HTML": "Playwright Test",
    "CSS": "Playwright Test",
    "SCSS": "Playwright Test",
    "Vue": "Vitest + Vue Test Utils",
    "Svelte": (
        "Vitest + Testing Library"
    ),
    "Shell": "Bats",
    "SQL": "database integration tests",
}


def suggested_framework(
    language: str,
    file_path: str,
) -> str:
    normalized_path = file_path.lower()

    if any(
        part in normalized_path
        for part in (
            "controller",
            "route",
            "api",
            "endpoint",
        )
    ):
        if language in {
            "JavaScript",
            "TypeScript",
        }:
            return "Supertest + Vitest"

        if language == "Python":
            return (
                "pytest + framework test client"
            )

        if language == "Java":
            return "JUnit 5 + MockMvc"

        if language == "PHP":
            return "PHPUnit HTTP tests"

    return LANGUAGE_FRAMEWORK_MAP.get(
        language,
        "language-appropriate unit tests",
    )


def generate_test_file(
    target_file: str,
    source_code: str,
    language: str,
) -> Optional[dict]:
    framework = suggested_framework(
        language,
        target_file,
    )

    base_name = os.path.splitext(
        os.path.basename(target_file)
    )[0]

    if language in {
        "HTML",
        "CSS",
        "SCSS",
    }:
        system_prompt = _playwright_prompt()
    else:
        system_prompt = (
            f"You are an expert {language} test engineer. "
            f"Generate one complete runnable test file using {framework}. "
            "Base every assertion on code that exists in the supplied file. "
            "Do not invent exported functions, routes, classes, variables, "
            "elements, IDs, dependencies, or behavior. Include normal behavior "
            "and meaningful edge cases. Include failure behavior only when the "
            "source contains behavior that can fail. Output only source code. "
            "Do not use Markdown fences or explanations."
        )

    user_prompt = (
        f"Language: {language}\n"
        f"Framework: {framework}\n"
        f"File under test: {target_file}\n\n"
        "Complete source file:\n"
        f"{source_code[:14000]}"
    )

    content = ask(
        system_prompt,
        user_prompt,
        max_tokens=3000,
    )

    content = _clean_generated_content(
        content
    )

    if not content:
        return None

    file_name = _test_file_name(
        language,
        base_name,
    )

    return {
        "target_file": target_file,
        "framework": framework,
        "file_name": file_name,
        "content": content,
    }


def _playwright_prompt() -> str:
    return (
        "You are an expert Playwright Test engineer. Generate one complete "
        "TypeScript Playwright test file for the supplied HTML or CSS file.\n\n"
        "Mandatory syntax rules:\n"
        "- Import with: import { test, expect } from '@playwright/test';\n"
        "- Use page.locator(). Never use page.querySelector().\n"
        "- Every asynchronous Playwright assertion must start with await.\n"
        "- Always write await expect(locator).toHaveCSS(property, value).\n"
        "- Never write expect(locator).toHaveCSS without await.\n"
        "- Use await expect(locator).toBeVisible(), toHaveText(), "
        "toHaveAttribute(), and toHaveCount().\n"
        "- Use expect(value) without await only for normal JavaScript values.\n"
        "- Use locator.boundingBox() when geometry must be checked.\n"
        "- Always check boundingBox() for null before reading width, height, "
        "x, y, top, or bottom.\n"
        "- Do not use file:// URLs.\n"
        "- Define const BASE_URL = process.env.TEST_BASE_URL || "
        "'http://127.0.0.1:4173';\n"
        "- Navigate using `${BASE_URL}/relative/path`.\n"
        "- Do not navigate to external websites during a test.\n"
        "- Do not invent elements, text, IDs, classes, links, or behavior.\n"
        "- Do not create tests for non-existent pages just to test failures.\n"
        "- Only assert styles and values visible in the supplied source.\n"
        "- Use await expect(page).toHaveTitle(...) for document titles.\n"
        "- CSS assertions must use computed browser values, such as rgb(...) "
        "instead of named colors.\n"
        "- For font-weight, prefer computed numeric values such as 700.\n"
        "- Avoid asserting shorthand properties such as margin or border when "
        "individual computed properties are more reliable.\n"
        "- Output source code only, with no Markdown fences."
    )


def _test_file_name(
    language: str,
    base_name: str,
) -> str:
    mapping = {
        "Python": f"test_{base_name}.py",
        "JavaScript": (
            f"{base_name}.test.js"
        ),
        "React": (
            f"{base_name}.test.jsx"
        ),
        "TypeScript": (
            f"{base_name}.test.ts"
        ),
        "React TypeScript": (
            f"{base_name}.test.tsx"
        ),
        "Java": (
            f"{base_name}Test.java"
        ),
        "C": (
            f"test_{base_name}.c"
        ),
        "C++": (
            f"{base_name}Test.cpp"
        ),
        "C/C++ Header": (
            f"{base_name}Test.cpp"
        ),
        "Go": (
            f"{base_name}_test.go"
        ),
        "PHP": (
            f"{base_name.capitalize()}Test.php"
        ),
        "C#": (
            f"{base_name}Tests.cs"
        ),
        "Rust": (
            f"{base_name}_test.rs"
        ),
        "Kotlin": (
            f"{base_name}Test.kt"
        ),
        "Swift": (
            f"{base_name}Tests.swift"
        ),
        "Ruby": (
            f"{base_name}_spec.rb"
        ),
        "HTML": (
            f"{base_name}.spec.ts"
        ),
        "CSS": (
            f"{base_name}.spec.ts"
        ),
        "SCSS": (
            f"{base_name}.spec.ts"
        ),
        "Vue": (
            f"{base_name}.spec.ts"
        ),
        "Svelte": (
            f"{base_name}.spec.ts"
        ),
        "Shell": (
            f"{base_name}.bats"
        ),
        "SQL": (
            f"test_{base_name}.sql"
        ),
    }

    return mapping.get(
        language,
        f"{base_name}.test.txt",
    )


def _clean_generated_content(
    content: str,
) -> str:
    cleaned = content.strip()

    cleaned = re.sub(
        r"^\s*```[a-zA-Z0-9_+#.-]*\s*",
        "",
        cleaned,
        count=1,
    )

    cleaned = re.sub(
        r"\s*```\s*$",
        "",
        cleaned,
        count=1,
    )

    return cleaned.strip()