"""
Dependency manifest analysis.

This analyzer performs safe manifest checks without installing or executing
repository dependencies.
"""

from __future__ import annotations

import json
import os
import re
import xml.etree.ElementTree as ET
from typing import Any, Dict, List


def analyze_dependencies(
    repo_path: str,
    manifest_paths: List[str],
) -> List[Dict[str, Any]]:
    issues: List[Dict[str, Any]] = []

    for relative_path in manifest_paths:
        file_name = os.path.basename(
            relative_path
        )

        full_path = os.path.join(
            repo_path,
            relative_path,
        )

        if file_name == "package.json":
            issues.extend(
                _analyze_package_json(
                    full_path,
                    relative_path,
                )
            )

        elif file_name in {
            "requirements.txt",
            "requirement.txt",
            "requirements-dev.txt",
            "requirements-prod.txt",
        }:
            issues.extend(
                _analyze_requirements(
                    full_path,
                    relative_path,
                )
            )

        elif file_name == "composer.json":
            issues.extend(
                _analyze_composer(
                    full_path,
                    relative_path,
                )
            )

        elif file_name == "pom.xml":
            issues.extend(
                _analyze_maven(
                    full_path,
                    relative_path,
                )
            )

        elif file_name in {
            "Cargo.toml",
            "go.mod",
            "Gemfile",
            "pyproject.toml",
        }:
            issues.extend(
                _analyze_unpinned_text_manifest(
                    full_path,
                    relative_path,
                )
            )

    return issues


def _analyze_package_json(
    full_path: str,
    relative_path: str,
) -> List[Dict[str, Any]]:
    try:
        with open(
            full_path,
            "r",
            encoding="utf-8",
        ) as package_file:
            data = json.load(package_file)

    except (
        OSError,
        ValueError,
    ):
        return [
            _issue(
                title="Invalid package.json",
                severity="medium",
                file_path=relative_path,
                description=(
                    "The package manifest could not be parsed."
                ),
                suggested_fix=(
                    "Correct the JSON syntax."
                ),
            )
        ]

    issues: List[Dict[str, Any]] = []

    dependencies = {
        **data.get("dependencies", {}),
        **data.get(
            "devDependencies",
            {},
        ),
    }

    for dependency, version in dependencies.items():
        version_text = str(version).strip()

        if version_text in {
            "*",
            "latest",
            "",
        }:
            issues.append(
                _issue(
                    title=(
                        f"Unpinned dependency: {dependency}"
                    ),
                    severity="medium",
                    file_path=relative_path,
                    description=(
                        f"{dependency} uses the version "
                        f"specifier '{version_text or 'empty'}'."
                    ),
                    suggested_fix=(
                        "Pin the dependency to a reviewed "
                        "version or controlled range."
                    ),
                )
            )

    if dependencies and not any(
        os.path.exists(
            os.path.join(
                os.path.dirname(full_path),
                lock_name,
            )
        )
        for lock_name in (
            "package-lock.json",
            "yarn.lock",
            "pnpm-lock.yaml",
        )
    ):
        issues.append(
            _issue(
                title="Node dependency lockfile missing",
                severity="medium",
                file_path=relative_path,
                description=(
                    "The project declares Node dependencies "
                    "but no supported lockfile was found."
                ),
                suggested_fix=(
                    "Generate and commit a package-lock.json, "
                    "yarn.lock, or pnpm-lock.yaml file."
                ),
            )
        )

    return issues

def read_dependencies(
    repo_path: str,
    manifest_paths: list[str],
) -> list[dict]:
    dependencies: list[dict] = []

    for relative_path in manifest_paths:
        full_path = os.path.join(
            repo_path,
            relative_path,
        )

        file_name = os.path.basename(
            relative_path
        )

        if file_name in {
            "requirements.txt",
            "requirement.txt",
            "requirements-dev.txt",
            "requirements-prod.txt",
        }:
            try:
                with open(
                    full_path,
                    "r",
                    encoding="utf-8",
                    errors="ignore",
                ) as manifest_file:
                    lines = manifest_file.readlines()
            except OSError:
                continue

            for line in lines:
                value = line.strip()

                if (
                    not value
                    or value.startswith("#")
                    or value.startswith("-")
                ):
                    continue

                if "==" in value:
                    name, version = value.split(
                        "==",
                        1,
                    )
                else:
                    name = value
                    version = None

                dependencies.append(
                    {
                        "name": name.strip(),
                        "version": (
                            version.strip()
                            if version
                            else None
                        ),
                        "ecosystem": "Python",
                        "manifest": (
                            relative_path
                        ),
                    }
                )

    return dependencies

def _analyze_requirements(
    full_path: str,
    relative_path: str,
) -> List[Dict[str, Any]]:
    issues: List[Dict[str, Any]] = []

    try:
        with open(
            full_path,
            "r",
            encoding="utf-8",
            errors="ignore",
        ) as requirements_file:
            lines = requirements_file.readlines()

    except OSError:
        return issues

    for line_number, line in enumerate(
        lines,
        start=1,
    ):
        stripped = line.strip()

        if (
            not stripped
            or stripped.startswith("#")
            or stripped.startswith("-")
        ):
            continue

        if not re.search(
            r"(==|~=|>=|<=|>|<)",
            stripped,
        ):
            issues.append(
                _issue(
                    title=(
                        "Unpinned Python dependency"
                    ),
                    severity="low",
                    file_path=relative_path,
                    line_number=line_number,
                    description=(
                        f"'{stripped}' has no version "
                        "constraint."
                    ),
                    suggested_fix=(
                        "Add a reviewed version pin "
                        "or compatible range."
                    ),
                )
            )

    return issues


def _analyze_composer(
    full_path: str,
    relative_path: str,
) -> List[Dict[str, Any]]:
    try:
        with open(
            full_path,
            "r",
            encoding="utf-8",
        ) as composer_file:
            data = json.load(composer_file)

    except (
        OSError,
        ValueError,
    ):
        return [
            _issue(
                title="Invalid composer.json",
                severity="medium",
                file_path=relative_path,
                description=(
                    "The Composer manifest could not be parsed."
                ),
                suggested_fix=(
                    "Correct the JSON syntax."
                ),
            )
        ]

    issues: List[Dict[str, Any]] = []

    requirements = {
        **data.get("require", {}),
        **data.get(
            "require-dev",
            {},
        ),
    }

    for dependency, version in requirements.items():
        if str(version).strip() in {
            "*",
            "dev-master",
            "dev-main",
        }:
            issues.append(
                _issue(
                    title=(
                        f"Unstable Composer dependency: "
                        f"{dependency}"
                    ),
                    severity="medium",
                    file_path=relative_path,
                    description=(
                        f"{dependency} uses '{version}'."
                    ),
                    suggested_fix=(
                        "Use a stable reviewed release."
                    ),
                )
            )

    return issues


def _analyze_maven(
    full_path: str,
    relative_path: str,
) -> List[Dict[str, Any]]:
    try:
        root = ET.parse(
            full_path
        ).getroot()

    except (
        OSError,
        ET.ParseError,
    ):
        return [
            _issue(
                title="Invalid Maven pom.xml",
                severity="medium",
                file_path=relative_path,
                description=(
                    "The Maven manifest could not be parsed."
                ),
                suggested_fix=(
                    "Correct the XML syntax."
                ),
            )
        ]

    issues: List[Dict[str, Any]] = []

    for version_element in root.iter():
        if not version_element.tag.endswith(
            "version"
        ):
            continue

        text = (
            version_element.text or ""
        ).strip()

        if text.upper() in {
            "LATEST",
            "RELEASE",
        }:
            issues.append(
                _issue(
                    title=(
                        "Unstable Maven dependency version"
                    ),
                    severity="medium",
                    file_path=relative_path,
                    description=(
                        f"The manifest uses '{text}'."
                    ),
                    suggested_fix=(
                        "Pin the dependency to a reviewed "
                        "version."
                    ),
                )
            )

    return issues


def _analyze_unpinned_text_manifest(
    full_path: str,
    relative_path: str,
) -> List[Dict[str, Any]]:
    try:
        with open(
            full_path,
            "r",
            encoding="utf-8",
            errors="ignore",
        ) as manifest_file:
            content = manifest_file.read()

    except OSError:
        return []

    issues: List[Dict[str, Any]] = []

    if re.search(
        r'(?i)(version\s*=\s*["\']\*["\']|latest)',
        content,
    ):
        issues.append(
            _issue(
                title="Unpinned dependency version",
                severity="medium",
                file_path=relative_path,
                description=(
                    "The dependency manifest appears to "
                    "use a wildcard or latest version."
                ),
                suggested_fix=(
                    "Use a stable reviewed version."
                ),
            )
        )

    return issues


def _issue(
    title: str,
    severity: str,
    file_path: str,
    description: str,
    suggested_fix: str,
    line_number: int | None = None,
) -> Dict[str, Any]:
    return {
        "title": title,
        "severity": severity,
        "category": "security",
        "file_path": file_path,
        "line_number": line_number,
        "language": "Dependencies",
        "description": description,
        "risk": (
            "Uncontrolled dependency versions can "
            "introduce insecure or unreproducible builds."
        ),
        "suggested_fix": suggested_fix,
        "generated_patch": None,
        "source_tool": (
            "reposage-dependency-checks"
        ),
    }