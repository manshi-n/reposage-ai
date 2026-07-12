"""
Repository language and framework detection.

Counts supported source files, lines of code, files grouped by language,
frameworks, and dependency manifests. Generated folders and vendor
directories are ignored.
"""

from __future__ import annotations

import json
import os
from collections import Counter
from dataclasses import dataclass, field
from typing import Dict, List


EXTENSION_LANGUAGE_MAP = {
    ".py": "Python",
    ".js": "JavaScript",
    ".mjs": "JavaScript",
    ".cjs": "JavaScript",
    ".jsx": "React",
    ".ts": "TypeScript",
    ".tsx": "React TypeScript",
    ".java": "Java",
    ".go": "Go",
    ".rb": "Ruby",
    ".php": "PHP",
    ".html": "HTML",
    ".htm": "HTML",
    ".css": "CSS",
    ".scss": "SCSS",
    ".sass": "Sass",
    ".less": "Less",
    ".cs": "C#",
    ".cpp": "C++",
    ".cc": "C++",
    ".cxx": "C++",
    ".c": "C",
    ".h": "C/C++ Header",
    ".hpp": "C/C++ Header",
    ".rs": "Rust",
    ".kt": "Kotlin",
    ".kts": "Kotlin",
    ".swift": "Swift",
    ".sh": "Shell",
    ".sql": "SQL",
    ".vue": "Vue",
    ".svelte": "Svelte",
}


IGNORED_DIRS = {
    ".git",
    ".github",
    "node_modules",
    "venv",
    ".venv",
    "__pycache__",
    "dist",
    "build",
    ".next",
    ".nuxt",
    "target",
    "vendor",
    "coverage",
    ".coverage",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".idea",
    ".vscode",
    "bin",
    "obj",
}


DEPENDENCY_MANIFESTS = {
    # Node.js
    "package.json": "Node.js",
    "package-lock.json": "Node.js",
    "yarn.lock": "Node.js",
    "pnpm-lock.yaml": "Node.js",

    # Python
    "requirements.txt": "Python",
    "requirement.txt": "Python",
    "requirements-dev.txt": "Python",
    "requirements-prod.txt": "Python",
    "pyproject.toml": "Python",
    "Pipfile": "Python",
    "Pipfile.lock": "Python",
    "poetry.lock": "Python",

    # PHP
    "composer.json": "PHP",
    "composer.lock": "PHP",

    # Java / Kotlin
    "pom.xml": "Java",
    "build.gradle": "Java/Kotlin",
    "build.gradle.kts": "Kotlin",

    # Go
    "go.mod": "Go",
    "go.sum": "Go",

    # Rust
    "Cargo.toml": "Rust",
    "Cargo.lock": "Rust",

    # Ruby
    "Gemfile": "Ruby",
    "Gemfile.lock": "Ruby",

    # Swift
    "Package.swift": "Swift",
}


FRAMEWORK_SIGNATURES = {
    "manage.py": "Django",
    "flask.py": "Flask",
    "next.config.js": "Next.js",
    "next.config.mjs": "Next.js",
    "next.config.ts": "Next.js",
    "vite.config.js": "Vite",
    "vite.config.ts": "Vite",
    "angular.json": "Angular",
    "vue.config.js": "Vue",
    "svelte.config.js": "Svelte",
    "docker-compose.yml": "Docker Compose",
    "docker-compose.yaml": "Docker Compose",
    "Dockerfile": "Docker",
    "pom.xml": "Maven",
    "go.mod": "Go Modules",
    "Gemfile": "Ruby/Bundler",
    "Cargo.toml": "Cargo",
}


@dataclass
class RepoStats:
    file_count: int = 0
    lines_of_code: int = 0
    languages: Counter = field(
        default_factory=Counter
    )
    language_lines: Counter = field(
        default_factory=Counter
    )
    frameworks: List[str] = field(
        default_factory=list
    )
    files_by_language: Dict[
        str,
        List[str],
    ] = field(default_factory=dict)
    dependency_manifests: List[str] = field(
        default_factory=list
    )


def detect_languages(
    repo_path: str,
    max_files: int = 5000,
) -> RepoStats:
    stats = RepoStats()

    for root, dirs, files in os.walk(
        repo_path
    ):
        dirs[:] = [
            directory
            for directory in dirs
            if directory not in IGNORED_DIRS
        ]

        for file_name in files:
            if stats.file_count >= max_files:
                break

            full_path = os.path.join(
                root,
                file_name,
            )

            relative_path = os.path.relpath(
                full_path,
                repo_path,
            )

            if _is_dependency_manifest(
                file_name
            ):
                stats.dependency_manifests.append(
                    relative_path
                )

            framework = FRAMEWORK_SIGNATURES.get(
                file_name
            )

            if (
                framework
                and framework
                not in stats.frameworks
            ):
                stats.frameworks.append(
                    framework
                )

            if file_name == "package.json":
                stats.frameworks.extend(
                    _sniff_package_json(
                        full_path
                    )
                )

            extension = os.path.splitext(
                file_name
            )[1].lower()

            language = (
                EXTENSION_LANGUAGE_MAP.get(
                    extension
                )
            )

            if not language:
                continue

            try:
                with open(
                    full_path,
                    "r",
                    encoding="utf-8",
                    errors="ignore",
                ) as source_file:
                    line_count = sum(
                        1
                        for _ in source_file
                    )
            except OSError:
                continue

            stats.file_count += 1
            stats.lines_of_code += line_count
            stats.languages[language] += 1
            stats.language_lines[
                language
            ] += line_count

            stats.files_by_language.setdefault(
                language,
                [],
            ).append(relative_path)

    stats.frameworks = sorted(
        set(stats.frameworks)
    )

    stats.dependency_manifests = sorted(
        set(stats.dependency_manifests)
    )

    return stats


def _is_dependency_manifest(
    file_name: str,
) -> bool:
    if file_name in DEPENDENCY_MANIFESTS:
        return True

    return file_name.endswith(
        ".csproj"
    )


def _sniff_package_json(
    path: str,
) -> List[str]:
    found: List[str] = []

    try:
        with open(
            path,
            "r",
            encoding="utf-8",
            errors="ignore",
        ) as package_file:
            data = json.load(package_file)

    except (
        OSError,
        ValueError,
        TypeError,
    ):
        return found

    dependencies = {
        **data.get("dependencies", {}),
        **data.get(
            "devDependencies",
            {},
        ),
    }

    checks = {
        "react": "React",
        "react-dom": "React",
        "vue": "Vue",
        "express": "Express",
        "next": "Next.js",
        "@nestjs/core": "NestJS",
        "svelte": "Svelte",
        "tailwindcss": "Tailwind CSS",
        "fastify": "Fastify",
        "vite": "Vite",
        "@angular/core": "Angular",
        "electron": "Electron",
    }

    for dependency, label in checks.items():
        if dependency in dependencies:
            found.append(label)

    return found