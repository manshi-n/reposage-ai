"""
Secure GitHub repository cloning with source-only size validation.
"""

from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path
from urllib.parse import urlparse

import git

from app.core.config import settings


class CloneError(Exception):
    """Raised when a repository cannot be cloned or safely analyzed."""


ALLOWED_SCHEMES = {
    "https",
}


ALLOWED_HOSTS = {
    "github.com",
    "www.github.com",
}


IGNORED_DIRECTORIES = {
    ".git",
    ".github",
    ".idea",
    ".vscode",
    ".next",
    ".nuxt",
    ".cache",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "__pycache__",
    "node_modules",
    "vendor",
    "venv",
    ".venv",
    "env",
    ".env",
    "dist",
    "build",
    "coverage",
    ".coverage",
    "target",
    "bin",
    "obj",
    "out",
}


IGNORED_FILE_NAMES = {
    ".DS_Store",
    "Thumbs.db",
}


IGNORED_EXTENSIONS = {
    # Python / compiled files
    ".pyc",
    ".pyo",
    ".class",
    ".o",
    ".obj",
    ".so",
    ".dll",
    ".dylib",
    ".exe",
    ".bin",

    # Git internals
    ".pack",
    ".idx",

    # Images
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".webp",
    ".bmp",
    ".ico",
    ".svg",
    ".tiff",
    ".tif",
    ".avif",

    # Video and audio
    ".mp4",
    ".mov",
    ".avi",
    ".mkv",
    ".webm",
    ".mp3",
    ".wav",
    ".ogg",
    ".flac",
    ".m4a",

    # Fonts
    ".ttf",
    ".otf",
    ".woff",
    ".woff2",
    ".eot",

    # Archives
    ".zip",
    ".tar",
    ".gz",
    ".tgz",
    ".rar",
    ".7z",

    # Documents and binary data
    ".pdf",
    ".doc",
    ".docx",
    ".xls",
    ".xlsx",
    ".ppt",
    ".pptx",
    ".db",
    ".sqlite",
    ".sqlite3",
}


def validate_repo_url(
    clone_url: str,
) -> None:
    parsed = urlparse(
        clone_url.strip()
    )

    if (
        parsed.scheme.lower()
        not in ALLOWED_SCHEMES
    ):
        raise CloneError(
            "Only HTTPS GitHub repository URLs are allowed."
        )

    hostname = (
        parsed.hostname
        or ""
    ).lower()

    if hostname not in ALLOWED_HOSTS:
        raise CloneError(
            "Only github.com repository URLs are supported."
        )

    path_parts = [
        part
        for part in parsed.path.split("/")
        if part
    ]

    if len(path_parts) != 2:
        raise CloneError(
            "Use the repository root URL in "
            "https://github.com/owner/repository form."
        )

    owner = path_parts[0].strip()

    repository = (
        path_parts[1]
        .strip()
        .removesuffix(".git")
    )

    if not owner or not repository:
        raise CloneError(
            "Invalid GitHub repository owner or name."
        )


def _check_no_symlinks(
    path: str,
) -> None:
    for root, dirs, files in os.walk(
        path,
        topdown=True,
    ):
        dirs[:] = [
            directory
            for directory in dirs
            if directory
            not in IGNORED_DIRECTORIES
        ]

        for name in [
            *dirs,
            *files,
        ]:
            full_path = os.path.join(
                root,
                name,
            )

            if os.path.islink(
                full_path
            ):
                relative_path = os.path.relpath(
                    full_path,
                    path,
                )

                raise CloneError(
                    "Symlink detected in repository; "
                    f"refusing to analyze: {relative_path}"
                )


def _should_ignore_file(
    file_name: str,
) -> bool:
    if file_name in IGNORED_FILE_NAMES:
        return True

    extension = (
        Path(file_name)
        .suffix
        .lower()
    )

    return extension in IGNORED_EXTENSIONS

def _enforce_size_limits(
    path: str,
) -> None:
    total_source_size = 0
    source_file_count = 0

    max_file_bytes = (
        settings.MAX_FILE_SIZE_KB
        * 1024
    )

    max_repo_bytes = (
        settings.MAX_REPO_SIZE_MB
        * 1024
        * 1024
    )

    for root, dirs, files in os.walk(
        path,
        topdown=True,
    ):
        dirs[:] = [
            directory
            for directory in dirs
            if directory
            not in IGNORED_DIRECTORIES
        ]

        for file_name in files:
            if _should_ignore_file(
                file_name
            ):
                continue

            full_path = os.path.join(
                root,
                file_name,
            )

            relative_path = os.path.relpath(
                full_path,
                path,
            )

            try:
                size = os.path.getsize(
                    full_path
                )
            except OSError:
                continue

            # Only source/analyzable files are counted.
            if size > max_file_bytes:
                raise CloneError(
                    "Source file exceeds maximum size limit: "
                    f"{relative_path}"
                )

            total_source_size += size
            source_file_count += 1

            if (
                source_file_count
                > settings.MAX_FILES
            ):
                raise CloneError(
                    "Repository exceeds maximum "
                    "allowed analyzable file count."
                )

            if (
                total_source_size
                > max_repo_bytes
            ):
                raise CloneError(
                    "Repository exceeds maximum "
                    "allowed analyzed source size."
                )


def clone_repository(
    clone_url: str,
    branch: str = "main",
) -> str:
    validate_repo_url(
        clone_url
    )

    os.makedirs(
        settings.CLONE_TMP_DIR,
        exist_ok=True,
    )

    container_directory = tempfile.mkdtemp(
        prefix="repo_",
        dir=settings.CLONE_TMP_DIR,
    )

    repository_directory = os.path.join(
        container_directory,
        "source",
    )

    try:
        git.Repo.clone_from(
            clone_url,
            repository_directory,
            branch=branch,
            depth=1,
            single_branch=True,
            no_tags=True,
        )

    except git.GitCommandError as exc:
        shutil.rmtree(
            container_directory,
            ignore_errors=True,
        )

        raise CloneError(
            f"Failed to clone repository: {exc}"
        ) from exc

    try:
        _check_no_symlinks(
            repository_directory
        )

        _enforce_size_limits(
            repository_directory
        )

    except CloneError:
        shutil.rmtree(
            container_directory,
            ignore_errors=True,
        )
        raise

    return repository_directory


def cleanup_clone(
    path: str,
) -> None:
    """
    Remove both the source folder and its temporary parent directory.
    """
    resolved_path = Path(
        path
    ).resolve()

    parent = resolved_path.parent

    if (
        resolved_path.name == "source"
        and parent.name.startswith(
            "repo_"
        )
    ):
        shutil.rmtree(
            parent,
            ignore_errors=True,
        )
        return

    shutil.rmtree(
        resolved_path,
        ignore_errors=True,
    )