"""
Create a GitHub branch, commit validated generated fixes,
and open a draft pull request.
"""

from __future__ import annotations

import re
from urllib.parse import urlparse

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
)
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.core.encryption import decrypt_token
from app.models.models import (
    Analysis,
    GitHubAccount,
    Issue,
    PullRequest,
    Repository,
    User,
)
from app.services.github_service import (
    GitHubAPIError,
    GitHubService,
)


router = APIRouter(
    prefix="/analyses",
    tags=["pull-requests"],
)


def _repository_identity(
    repository: Repository,
) -> tuple[str, str]:
    """
    Extract owner and repository name from full_name or clone_url.
    """
    full_name = (
        repository.full_name
        or ""
    ).strip().strip("/")

    if "/" in full_name:
        owner, name = full_name.split(
            "/",
            1,
        )

        owner = owner.strip()

        name = (
            name.strip()
            .removesuffix(".git")
        )

        if owner and name:
            return owner, name

    parsed = urlparse(
        repository.clone_url
        or ""
    )

    parts = [
        part
        for part in parsed.path.split("/")
        if part
    ]

    if len(parts) == 2:
        owner = parts[0].strip()

        name = (
            parts[1]
            .strip()
            .removesuffix(".git")
        )

        if owner and name:
            return owner, name

    raise HTTPException(
        status_code=400,
        detail=(
            "Could not identify the GitHub "
            "repository owner and name."
        ),
    )


def _validate_patch_for_commit(
    file_path: str,
    patch: str,
) -> str:
    """
    Reject unsafe or malformed AI-generated file content
    before it is committed to GitHub.
    """
    cleaned = (
        patch
        or ""
    ).strip()

    if not cleaned:
        raise HTTPException(
            status_code=400,
            detail=(
                f"The generated patch for "
                f"'{file_path}' is empty."
            ),
        )

    if cleaned == "VALIDATION_REQUIRED":
        raise HTTPException(
            status_code=400,
            detail=(
                f"The generated fix for "
                f"'{file_path}' requires manual validation."
            ),
        )

    if "```" in cleaned:
        raise HTTPException(
            status_code=400,
            detail=(
                f"The generated patch for "
                f"'{file_path}' contains Markdown fences. "
                "Regenerate the fix before creating a pull request."
            ),
        )

    explanation_pattern = re.compile(
        r"(?im)^\s*("
        r"however|"
        r"here is the corrected version|"
        r"alternative implementation|"
        r"explanation|"
        r"side effects|"
        r"improvement"
        r")\s*[:.]?"
    )

    if explanation_pattern.search(
        cleaned
    ):
        raise HTTPException(
            status_code=400,
            detail=(
                f"The generated patch for "
                f"'{file_path}' contains explanatory text. "
                "Regenerate the fix before creating a pull request."
            ),
        )

    lower_path = file_path.lower()

    if lower_path.endswith(".php"):
        _validate_php_patch(
            file_path,
            cleaned,
        )

    elif lower_path.endswith(
        (
            ".html",
            ".htm",
        )
    ):
        if (
            "<html" in cleaned.lower()
            and "</html>" not in cleaned.lower()
        ):
            raise HTTPException(
                status_code=400,
                detail=(
                    f"The generated HTML patch for "
                    f"'{file_path}' appears incomplete."
                ),
            )

    return cleaned


def _validate_php_patch(
    file_path: str,
    patch: str,
) -> None:
    lowered = patch.lower()

    if "<?php" not in lowered:
        raise HTTPException(
            status_code=400,
            detail=(
                f"The generated PHP patch for "
                f"'{file_path}' has no PHP opening tag."
            ),
        )

    forbidden_patterns = {
        "filter_sanitize_string": (
            "uses deprecated FILTER_SANITIZE_STRING"
        ),
        "password_verify($pwd, password_hash(": (
            "hashes the password during every login attempt"
        ),
        "here is the corrected version": (
            "contains explanatory text"
        ),
    }

    for pattern, reason in (
        forbidden_patterns.items()
    ):
        if pattern in lowered:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"The generated patch for "
                    f"'{file_path}' {reason}. "
                    "Regenerate the fix before creating a pull request."
                ),
            )


def _latest_patch_per_file(
    generated_issues: list[Issue],
) -> dict[str, Issue]:
    """
    Generated issues are ordered newest first.
    Keep only the latest patch for each file.
    """
    patches: dict[
        str,
        Issue,
    ] = {}

    for issue in generated_issues:
        normalized_path = (
            issue.file_path
            .replace("\\", "/")
            .lstrip("/")
        )

        if not normalized_path:
            continue

        patches.setdefault(
            normalized_path,
            issue,
        )

    return patches


@router.post(
    "/{analysis_id}/create-pr"
)
async def create_pull_request_endpoint(
    analysis_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        get_current_user
    ),
):
    analysis = (
        db.query(Analysis)
        .join(
            Repository,
            Repository.id
            == Analysis.repository_id,
        )
        .filter(
            Analysis.id == analysis_id,
            Repository.owner_id
            == current_user.id,
        )
        .first()
    )

    if not analysis:
        raise HTTPException(
            status_code=404,
            detail="Analysis not found.",
        )

    repository = (
        db.query(Repository)
        .filter(
            Repository.id
            == analysis.repository_id,
            Repository.owner_id
            == current_user.id,
        )
        .first()
    )

    if not repository:
        raise HTTPException(
            status_code=404,
            detail="Repository not found.",
        )

    existing_pull_request = (
        db.query(PullRequest)
        .filter(
            PullRequest.analysis_id
            == analysis.id,
            PullRequest.status
            == "open",
        )
        .first()
    )

    if existing_pull_request:
        return {
            "pr_url": (
                existing_pull_request
                .github_pr_url
            ),
            "pr_number": (
                existing_pull_request
                .github_pr_number
            ),
        }

    generated_issues = (
        db.query(Issue)
        .filter(
            Issue.analysis_id
            == analysis.id,
            Issue.generated_patch.isnot(
                None
            ),
            Issue.generated_patch != "",
        )
        .order_by(
            Issue.created_at.desc()
        )
        .all()
    )

    if not generated_issues:
        raise HTTPException(
            status_code=400,
            detail=(
                "Generate at least one issue fix "
                "before creating a pull request."
            ),
        )

    patches_by_file = (
        _latest_patch_per_file(
            generated_issues
        )
    )

    if not patches_by_file:
        raise HTTPException(
            status_code=400,
            detail=(
                "No valid generated file patches "
                "were found."
            ),
        )

    validated_patches: dict[
        str,
        str,
    ] = {}

    for file_path, issue in (
        patches_by_file.items()
    ):
        validated_patches[
            file_path
        ] = _validate_patch_for_commit(
            file_path,
            issue.generated_patch
            or "",
        )

    github_account = (
        db.query(GitHubAccount)
        .filter(
            GitHubAccount.user_id
            == current_user.id
        )
        .first()
    )

    if not github_account:
        raise HTTPException(
            status_code=400,
            detail=(
                "Sign in with GitHub before "
                "creating a pull request."
            ),
        )

    try:
        access_token = decrypt_token(
            github_account
            .access_token_encrypted
        )

    except Exception as exc:
        raise HTTPException(
            status_code=401,
            detail=(
                "The saved GitHub authorization "
                "is invalid. Sign in with GitHub again."
            ),
        ) from exc

    owner, repository_name = (
        _repository_identity(
            repository
        )
    )

    github = GitHubService(
        access_token=access_token
    )

    base_branch = (
        analysis.branch
        or repository.default_branch
        or "main"
    )

    branch_name = (
        "reposage-ai/"
        f"fixes-{analysis.id[:8]}"
    )

    try:
        repository_data = (
            await github.get_repository(
                owner,
                repository_name,
            )
        )

        permissions = (
            repository_data.get(
                "permissions"
            )
            or {}
        )

        if not permissions.get("push"):
            raise HTTPException(
                status_code=403,
                detail=(
                    "Your GitHub account does "
                    "not have push permission "
                    "for this repository."
                ),
            )

        base_exists = (
            await github.branch_exists(
                owner,
                repository_name,
                base_branch,
            )
        )

        if not base_exists:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"The base branch "
                    f"'{base_branch}' does not exist."
                ),
            )

        branch_exists = (
            await github.branch_exists(
                owner,
                repository_name,
                branch_name,
            )
        )

        if not branch_exists:
            await github.create_branch(
                owner=owner,
                repository=repository_name,
                branch=branch_name,
                from_branch=base_branch,
            )

        committed_files: list[
            str
        ] = []

        for (
            file_path,
            corrected_content,
        ) in validated_patches.items():
            await github.update_file(
                owner=owner,
                repository=repository_name,
                path=file_path,
                branch=branch_name,
                content=corrected_content,
                message=(
                    "fix: apply RepoSage "
                    f"recommendation for {file_path}"
                ),
            )

            committed_files.append(
                file_path
            )

        if not committed_files:
            raise HTTPException(
                status_code=400,
                detail=(
                    "No validated generated files "
                    "were available to commit."
                ),
            )

        files_markdown = "\n".join(
            f"- `{path}`"
            for path in committed_files
        )

        title = (
            "RepoSage AI: automated "
            f"fixes ({analysis.id[:8]})"
        )

        body = (
            "## RepoSage AI generated fixes\n\n"
            "This draft pull request contains AI-generated "
            "changes selected from a repository analysis.\n\n"
            f"**Analysis ID:** `{analysis.id}`\n\n"
            f"**Base branch:** `{base_branch}`\n\n"
            "### Changed files\n"
            f"{files_markdown}\n\n"
            "### Validation\n"
            "- Generated patches passed RepoSage structural validation.\n"
            "- Markdown fences and explanatory text were rejected.\n"
            "- Deprecated PHP patterns were rejected.\n"
            "- Automated execution of repository tests was not performed.\n\n"
            "### Review warning\n"
            "These changes were generated automatically. "
            "Review and test every file before merging."
        )

        pull_request_data = (
            await github.create_pull_request(
                owner=owner,
                repo=repository_name,
                title=title,
                head=branch_name,
                base=base_branch,
                body=body,
                draft=True,
            )
        )

    except HTTPException:
        raise

    except GitHubAPIError as exc:
        raise HTTPException(
            status_code=502,
            detail=(
                "GitHub rejected the operation: "
                f"{exc}"
            ),
        ) from exc

    pull_request_url = (
        pull_request_data.get(
            "html_url"
        )
    )

    pull_request_number = (
        pull_request_data.get(
            "number"
        )
    )

    if (
        not pull_request_url
        or not pull_request_number
    ):
        raise HTTPException(
            status_code=502,
            detail=(
                "GitHub created an incomplete "
                "pull-request response."
            ),
        )

    pull_request = PullRequest(
        analysis_id=analysis.id,
        github_pr_number=(
            pull_request_number
        ),
        github_pr_url=(
            pull_request_url
        ),
        title=title,
        status="open",
    )

    db.add(pull_request)
    db.commit()
    db.refresh(pull_request)

    return {
        "pr_url": (
            pull_request.github_pr_url
        ),
        "pr_number": (
            pull_request.github_pr_number
        ),
    }