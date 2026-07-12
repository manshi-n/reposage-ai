"""
Architecture Agent.

Builds a lightweight directory/file map of the repo and asks the LLM to
explain the architecture: layering, entry points, frontend/backend
separation, data flow, and design patterns. Falls back to a rule-based
summary (still useful) if no LLM key is configured.
"""
import os
from typing import Dict, List

from app.analyzers.language_detector import IGNORED_DIRS
from app.services.llm_client import ask

MAX_TREE_ENTRIES = 400

ENTRY_POINT_HINTS = [
    "main.py", "app.py", "manage.py", "index.js", "index.ts", "server.js",
    "server.ts", "main.go", "Program.cs", "Main.java",
]


def _build_file_tree(repo_path: str) -> List[str]:
    entries: List[str] = []
    for root, dirs, files in os.walk(repo_path):
        dirs[:] = [d for d in dirs if d not in IGNORED_DIRS]
        rel_root = os.path.relpath(root, repo_path)
        for f in files:
            entries.append(f if rel_root == "." else os.path.join(rel_root, f))
            if len(entries) >= MAX_TREE_ENTRIES:
                return entries
    return entries


def _find_entry_points(file_tree: List[str]) -> List[str]:
    return [f for f in file_tree if os.path.basename(f) in ENTRY_POINT_HINTS]


def analyze_architecture(repo_path: str, languages: Dict[str, int], frameworks: List[str]) -> str:
    file_tree = _build_file_tree(repo_path)
    entry_points = _find_entry_points(file_tree)

    tree_preview = "\n".join(sorted(file_tree)[:MAX_TREE_ENTRIES])
    lang_summary = ", ".join(f"{lang} ({count} files)" for lang, count in languages.items())
    fw_summary = ", ".join(frameworks) if frameworks else "none detected"

    system_prompt = (
        "You are a senior software architect reviewing an unfamiliar codebase. "
        "Given a file tree, detected languages, and frameworks, explain the "
        "architecture clearly and concisely for a new engineer joining the "
        "project: overall structure, layering, entry points, frontend/backend "
        "separation if any, data flow, and any recognizable design patterns. "
        "Be specific about file/folder names. Keep it under 300 words. "
        "Do not assume that folders are connected simply because they exist in "
        "the same repository. Only claim frontend-backend communication when "
        "direct evidence exists, such as fetch calls, Axios calls, API routes, "
        "form actions, shared URLs, or configuration. If the repository is a "
        "collection of independent exercises, state that clearly. Do not invent "
        "authentication, databases, APIs, or service layers. When evidence is "
        "missing, say that no clear connection was found."
    )
    
    user_prompt = (
        f"Languages: {lang_summary}\n"
        f"Frameworks detected: {fw_summary}\n"
        f"Likely entry points: {', '.join(entry_points) or 'none obviously named'}\n\n"
        f"File tree (truncated):\n{tree_preview}"
    )

    return ask(system_prompt, user_prompt, max_tokens=800)
