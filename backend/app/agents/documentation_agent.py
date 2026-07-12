"""
Evidence-based documentation generation.

The documentation agent receives verified repository evidence instead of
guessing from folder names alone.
"""

from __future__ import annotations

from typing import Any, Dict, List

from app.services.llm_client import ask


DOC_TYPES = {
    "readme": (
        "a complete README.md containing project purpose, "
        "verified features, repository structure, dependencies, "
        "environment variables, routes, and quick-start instructions"
    ),
    "installation": (
        "step-by-step installation and local setup instructions "
        "based on verified files and dependencies"
    ),
    "env_vars": (
        "environment-variable documentation based only on "
        "verified source-code references and configuration files"
    ),
    "api_docs": (
        "route documentation based only on verified application routes, "
        "clearly distinguishing rendered page routes from JSON API routes"
    ),
    "architecture": (
        "an architecture overview explaining verified modules, "
        "entry points, frameworks, routes, and data flow"
    ),
    "contributing": (
        "a practical CONTRIBUTING.md tailored to the verified repository"
    ),
}


def generate_document(
    doc_type: str,
    repo_name: str,
    repository_url: str,
    languages: List[str],
    frameworks: List[str],
    architecture_summary: str,
    repository_tree: List[str],
    dependency_manifests: List[str],
    verified_dependencies: List[Dict[str, Any]],
    verified_routes: List[Dict[str, Any]],
    verified_env_vars: List[Dict[str, Any]],
) -> Dict[str, str]:
    """
    Generate one documentation artifact from verified repository evidence.
    """

    description = DOC_TYPES.get(
        doc_type,
        "project documentation",
    )

    tree_text = _format_repository_tree(
        repository_tree
    )

    manifest_text = _format_manifests(
        dependency_manifests
    )

    dependency_text = _format_dependencies(
        verified_dependencies
    )

    route_text = _format_routes(
        verified_routes
    )

    environment_text = (
        _format_environment_variables(
            verified_env_vars
        )
    )

    system_prompt = (
        "You are a precise senior technical writer. "
        "Write Markdown documentation using only the verified repository "
        "evidence supplied by the user.\n\n"

        "Mandatory accuracy rules:\n"
        "- Use the exact repository name and repository URL provided.\n"
        "- Never use placeholder owners such as your-username.\n"
        "- Do not invent files, directories, dependencies, environment "
        "variables, APIs, databases, commands, ports, integrations, "
        "frameworks, deployment targets, or application behavior.\n"
        "- Use repository paths exactly as supplied.\n"
        "- Do not claim that two parts of the repository communicate unless "
        "the verified evidence or architecture analysis proves it.\n"
        "- Distinguish browser-rendered application routes from JSON REST APIs.\n"
        "- Do not say there are no routes when verified routes are supplied.\n"
        "- Do not say there are no dependencies when verified dependencies "
        "are supplied.\n"
        "- Do not say there are no environment variables when verified "
        "environment-variable references are supplied.\n"
        "- When a fact is uncertain, label it as uncertain instead of guessing.\n"
        "- Distinguish confirmed facts from recommendations.\n"
        "- Installation commands must match the detected manifests.\n"
        "- If the repository has requirement.txt rather than requirements.txt, "
        "use the exact verified filename requirement.txt.\n"
        "- Do not claim that a command was tested unless execution evidence "
        "was provided.\n"
        "- Do not wrap the full response inside a Markdown code fence.\n"
    )

    user_prompt = (
        f"Documentation type: {doc_type}\n"
        f"Requested output: {description}\n\n"

        f"Repository name: {repo_name}\n"
        f"Repository URL: {repository_url}\n"

        "Detected languages:\n"
        f"{_format_simple_list(languages)}\n\n"

        "Detected frameworks and tools:\n"
        f"{_format_simple_list(frameworks)}\n\n"

        "Dependency manifests:\n"
        f"{manifest_text}\n\n"

        "Verified dependencies:\n"
        f"{dependency_text}\n\n"

        "Verified application routes:\n"
        f"{route_text}\n\n"

        "Verified environment-variable references:\n"
        f"{environment_text}\n\n"

        "Verified repository tree:\n"
        f"{tree_text}\n\n"

        "Architecture analysis:\n"
        f"{architecture_summary or 'No architecture summary is available.'}\n\n"

        f"Generate {description}."
    )

    content = ask(
        system_prompt,
        user_prompt,
        max_tokens=3200,
    )

    title_map = {
        "readme": "README",
        "installation": (
            "Installation Guide"
        ),
        "env_vars": (
            "Environment Variables"
        ),
        "api_docs": (
            "Application Routes"
        ),
        "architecture": (
            "Architecture Overview"
        ),
        "contributing": (
            "Contributing Guide"
        ),
    }

    return {
        "doc_type": doc_type,
        "title": title_map.get(
            doc_type,
            doc_type.replace(
                "_",
                " ",
            ).title(),
        ),
        "content": content.strip(),
    }


def _format_simple_list(
    values: List[str],
) -> str:
    cleaned = sorted(
        {
            str(value).strip()
            for value in values
            if str(value).strip()
        }
    )

    if not cleaned:
        return "- None detected"

    return "\n".join(
        f"- {value}"
        for value in cleaned
    )


def _format_repository_tree(
    repository_tree: List[str],
) -> str:
    if not repository_tree:
        return "- No repository files detected"

    return "\n".join(
        f"- {path}"
        for path in repository_tree[:250]
    )


def _format_manifests(
    dependency_manifests: List[str],
) -> str:
    if not dependency_manifests:
        return "- None detected"

    return "\n".join(
        f"- {path}"
        for path in sorted(
            set(
                dependency_manifests
            )
        )
    )


def _format_dependencies(
    dependencies: List[
        Dict[str, Any]
    ],
) -> str:
    if not dependencies:
        return "- None detected"

    lines: List[str] = []

    for dependency in dependencies:
        name = str(
            dependency.get(
                "name",
                "unknown",
            )
        )

        version = dependency.get(
            "version"
        )

        ecosystem = dependency.get(
            "ecosystem",
            "unknown",
        )

        manifest = dependency.get(
            "manifest",
            "unknown manifest",
        )

        version_text = (
            f"=={version}"
            if version
            else " (version not pinned)"
        )

        lines.append(
            f"- {name}{version_text} "
            f"[{ecosystem}; {manifest}]"
        )

    return "\n".join(lines)


def _format_routes(
    routes: List[
        Dict[str, Any]
    ],
) -> str:
    if not routes:
        return "- No verified application routes detected"

    lines: List[str] = []

    for route in routes:
        methods = route.get(
            "methods",
            ["GET"],
        )

        method_text = ", ".join(
            str(method).upper()
            for method in methods
        )

        path = route.get(
            "path",
            "unknown",
        )

        handler = route.get(
            "handler",
            "unknown handler",
        )

        file_path = route.get(
            "file_path",
            "unknown file",
        )

        line_number = route.get(
            "line_number"
        )

        route_kind = route.get(
            "route_kind",
            "application route",
        )

        location = file_path

        if line_number:
            location += (
                f":{line_number}"
            )

        lines.append(
            f"- {method_text} {path} "
            f"→ {handler} "
            f"({route_kind}; {location})"
        )

    return "\n".join(lines)


def _format_environment_variables(
    environment_variables: List[
        Dict[str, Any]
    ],
) -> str:
    if not environment_variables:
        return (
            "- No verified environment-variable "
            "references detected"
        )

    lines: List[str] = []

    for variable in (
        environment_variables
    ):
        name = variable.get(
            "name",
            "unknown",
        )

        default = variable.get(
            "default"
        )

        file_path = variable.get(
            "file_path",
            "unknown file",
        )

        line_number = variable.get(
            "line_number"
        )

        location = file_path

        if line_number:
            location += (
                f":{line_number}"
            )

        default_text = (
            f"default={default!r}"
            if default is not None
            else "no default detected"
        )

        lines.append(
            f"- {name}: {default_text}; "
            f"referenced at {location}"
        )

    return "\n".join(lines)