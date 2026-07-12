"""
Repository connection and retrieval endpoints.
"""

from __future__ import annotations

from typing import List
from urllib.parse import urlparse

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
)
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.models import (
    Repository,
    User,
)
from app.schemas.schemas import (
    RepositoryConnect,
    RepositoryOut,
)
from app.services.clone_service import (
    CloneError,
    validate_repo_url,
)


router = APIRouter(
    prefix="/repositories",
    tags=["repositories"],
)


def repository_identity(
    clone_url: str,
) -> tuple[str, str]:
    """
    Return repository name and owner/name
    from an approved GitHub URL.
    """
    parsed = urlparse(
        clone_url.strip()
    )

    hostname = (
        parsed.hostname or ""
    ).lower()

    if hostname not in {
        "github.com",
        "www.github.com",
    }:
        raise CloneError(
            "Only GitHub repository URLs "
            "are supported."
        )

    path_parts = [
        part
        for part in parsed.path.split("/")
        if part
    ]

    if len(path_parts) != 2:
        raise CloneError(
            "Use a GitHub repository URL "
            "in owner/repository form."
        )

    owner = path_parts[0].strip()
    repository_name = (
        path_parts[1]
        .strip()
        .removesuffix(".git")
    )

    if (
        not owner
        or not repository_name
    ):
        raise CloneError(
            "Invalid GitHub repository "
            "owner or name."
        )

    return (
        repository_name,
        f"{owner}/{repository_name}",
    )


def normalize_clone_url(
    clone_url: str,
) -> str:
    name, full_name = (
        repository_identity(clone_url)
    )

    owner = full_name.split(
        "/",
        1,
    )[0]

    return (
        f"https://github.com/"
        f"{owner}/{name}"
    )


@router.post(
    "/connect",
    response_model=RepositoryOut,
)
def connect_repository(
    payload: RepositoryConnect,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        get_current_user
    ),
):
    try:
        validate_repo_url(
            payload.clone_url
        )

        name, parsed_full_name = (
            repository_identity(
                payload.clone_url
            )
        )

        normalized_url = (
            normalize_clone_url(
                payload.clone_url
            )
        )

    except CloneError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    existing = (
        db.query(Repository)
        .filter(
            Repository.owner_id
            == current_user.id,
            Repository.full_name
            == parsed_full_name,
        )
        .first()
    )

    if not existing:
        existing = (
            db.query(Repository)
            .filter(
                Repository.owner_id
                == current_user.id,
                Repository.clone_url.in_(
                    [
                        payload.clone_url,
                        normalized_url,
                        f"{normalized_url}.git",
                    ]
                ),
            )
            .first()
        )

    if existing:
        existing.name = name
        existing.full_name = (
            parsed_full_name
        )
        existing.clone_url = (
            normalized_url
        )
        existing.is_private = (
            payload.is_private
        )
        existing.default_branch = (
            payload.default_branch
            or existing.default_branch
            or "main"
        )

        db.commit()
        db.refresh(existing)

        return (
            RepositoryOut.model_validate(
                existing
            )
        )

    repository = Repository(
        owner_id=current_user.id,
        name=name,
        full_name=parsed_full_name,
        clone_url=normalized_url,
        is_private=payload.is_private,
        default_branch=(
            payload.default_branch
            or "main"
        ),
    )

    db.add(repository)
    db.commit()
    db.refresh(repository)

    return RepositoryOut.model_validate(
        repository
    )


@router.get(
    "",
    response_model=List[RepositoryOut],
)
def list_repositories(
    db: Session = Depends(get_db),
    current_user: User = Depends(
        get_current_user
    ),
):
    repositories = (
        db.query(Repository)
        .filter(
            Repository.owner_id
            == current_user.id
        )
        .order_by(
            Repository.created_at.desc()
        )
        .all()
    )

    return [
        RepositoryOut.model_validate(
            repository
        )
        for repository in repositories
    ]


@router.get(
    "/{repository_id}",
    response_model=RepositoryOut,
)
def get_repository(
    repository_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        get_current_user
    ),
):
    repository = (
        db.query(Repository)
        .filter(
            Repository.id
            == repository_id,
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

    return RepositoryOut.model_validate(
        repository
    )