"""
Analysis API endpoints.
"""

from __future__ import annotations

import ast
import asyncio
import json
import os
import re
from pathlib import Path
from typing import Any, List, Optional

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    Query,
    WebSocket,
    WebSocketDisconnect,
)
from sqlalchemy.orm import Session

from app.agents.refactoring_agent import (
    RefactoringError,
    generate_refactor,
)
from app.api.deps import get_current_user
from app.core.database import (
    SessionLocal,
    get_db,
)
from app.models.models import (
    Analysis,
    AnalysisStatus,
    GeneratedDocument,
    GeneratedTest,
    Issue,
    Repository,
    User,
)
from app.schemas.schemas import (
    AnalysisCreate,
    AnalysisOut,
    AnalysisStatusOut,
    GeneratedDocumentOut,
    GeneratedTestOut,
    GenerateFixRequest,
    IssueOut,
    IssueUpdate,
)
from app.services.analysis_service import (
    run_analysis,
)
from app.services.clone_service import (
    cleanup_clone,
    clone_repository,
)
from app.services.progress_service import (
    get_progress_events,
    push_progress,
)


router = APIRouter(
    prefix="/analyses",
    tags=["analyses"],
)


IGNORED_TREE_DIRECTORIES = {
    ".git",
    ".github",
    "node_modules",
    "venv",
    ".venv",
    "env",
    "dist",
    "build",
    "coverage",
    "__pycache__",
    ".next",
    ".nuxt",
    "vendor",
    "target",
    ".idea",
    ".vscode",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
}


PYTHON_REQUIREMENT_FILES = {
    "requirements.txt",
    "requirement.txt",
    "requirements-dev.txt",
    "requirements-prod.txt",
}


ENV_CALL_NAMES = {
    "getenv",
}


def _owned_analysis(
    db: Session,
    analysis_id: str,
    current_user: User,
) -> tuple[
    Analysis,
    Repository,
]:
    result = (
        db.query(
            Analysis,
            Repository,
        )
        .join(
            Repository,
            Repository.id
            == Analysis.repository_id,
        )
        .filter(
            Analysis.id
            == analysis_id,
            Repository.owner_id
            == current_user.id,
        )
        .first()
    )

    if not result:
        raise HTTPException(
            status_code=404,
            detail="Analysis not found.",
        )

    analysis, repository = result

    return analysis, repository


def _run_inline(
    analysis_id: str,
    clone_url: str,
) -> None:
    db = SessionLocal()

    try:
        analysis = (
            db.query(Analysis)
            .filter(
                Analysis.id
                == analysis_id
            )
            .first()
        )

        if not analysis:
            return

        def progress_callback(
            status: AnalysisStatus,
            percent: int,
        ) -> None:
            status_value = (
                status.value
                if hasattr(
                    status,
                    "value",
                )
                else str(status)
            )

            push_progress(
                analysis_id,
                status_value,
                percent,
            )

        run_analysis(
            db,
            analysis,
            clone_url=clone_url,
            progress_cb=(
                progress_callback
            ),
        )

    finally:
        db.close()


def _serialize_issue(
    issue: Issue,
) -> IssueOut:
    output = IssueOut.model_validate(
        issue
    )

    output.severity = (
        issue.severity.value
        if hasattr(
            issue.severity,
            "value",
        )
        else str(issue.severity)
    )

    output.category = (
        issue.category.value
        if hasattr(
            issue.category,
            "value",
        )
        else str(issue.category)
    )

    output.status = (
        issue.status.value
        if hasattr(
            issue.status,
            "value",
        )
        else str(issue.status)
    )

    return output


def _normalized_relative_path(
    repository_path: str,
    issue_path: str,
) -> Path:
    normalized = (
        issue_path
        .replace("\\", "/")
        .lstrip("/")
    )

    repository_root = Path(
        repository_path
    ).resolve()

    source_path = (
        repository_root
        / normalized
    ).resolve()

    try:
        source_path.relative_to(
            repository_root
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=(
                "The issue file path is outside "
                "the cloned repository."
            ),
        ) from exc

    return source_path


def _repository_tree(
    repository_path: str,
) -> list[str]:
    tree: list[str] = []

    for (
        root,
        directories,
        files,
    ) in os.walk(repository_path):
        directories[:] = [
            directory
            for directory in directories
            if directory
            not in IGNORED_TREE_DIRECTORIES
        ]

        for file_name in files:
            full_path = os.path.join(
                root,
                file_name,
            )

            relative_path = os.path.relpath(
                full_path,
                repository_path,
            )

            tree.append(
                relative_path.replace(
                    "\\",
                    "/",
                )
            )

    tree.sort()

    return tree


def _language_for_path(
    files_by_language: dict[
        str,
        list[str],
    ],
    file_path: str,
) -> str | None:
    normalized = file_path.replace(
        "\\",
        "/",
    )

    for language, paths in (
        files_by_language.items()
    ):
        for candidate in paths:
            if (
                candidate.replace(
                    "\\",
                    "/",
                )
                == normalized
            ):
                return language

    return None


def _detect_python_routes(
    repository_path: str,
) -> list[
    dict[str, Any]
]:
    """
    Detect Flask, FastAPI and similar decorator-based Python routes.
    """

    routes: list[
        dict[str, Any]
    ] = []

    repository_root = Path(
        repository_path
    )

    for path in repository_root.rglob(
        "*.py"
    ):
        if any(
            part
            in IGNORED_TREE_DIRECTORIES
            for part in path.parts
        ):
            continue

        try:
            source = path.read_text(
                encoding="utf-8",
                errors="ignore",
            )

            tree = ast.parse(source)

        except (
            OSError,
            SyntaxError,
        ):
            continue

        relative_path = str(
            path.relative_to(
                repository_root
            )
        ).replace(
            "\\",
            "/",
        )

        for node in ast.walk(tree):
            if not isinstance(
                node,
                (
                    ast.FunctionDef,
                    ast.AsyncFunctionDef,
                ),
            ):
                continue

            for decorator in (
                node.decorator_list
            ):
                if not isinstance(
                    decorator,
                    ast.Call,
                ):
                    continue

                function = decorator.func

                if not isinstance(
                    function,
                    ast.Attribute,
                ):
                    continue

                decorator_name = (
                    function.attr.lower()
                )

                if decorator_name not in {
                    "route",
                    "get",
                    "post",
                    "put",
                    "patch",
                    "delete",
                    "options",
                    "head",
                }:
                    continue

                if (
                    not decorator.args
                    or not isinstance(
                        decorator.args[0],
                        ast.Constant,
                    )
                    or not isinstance(
                        decorator.args[0].value,
                        str,
                    )
                ):
                    continue

                route_path = (
                    decorator.args[0].value
                )

                methods = [
                    decorator_name.upper()
                ]

                if decorator_name == "route":
                    methods = ["GET"]

                    for keyword in (
                        decorator.keywords
                    ):
                        if (
                            keyword.arg
                            != "methods"
                        ):
                            continue

                        if not isinstance(
                            keyword.value,
                            (
                                ast.List,
                                ast.Tuple,
                                ast.Set,
                            ),
                        ):
                            continue

                        parsed_methods = [
                            str(
                                element.value
                            ).upper()
                            for element in (
                                keyword.value.elts
                            )
                            if isinstance(
                                element,
                                ast.Constant,
                            )
                            and isinstance(
                                element.value,
                                str,
                            )
                        ]

                        if parsed_methods:
                            methods = (
                                parsed_methods
                            )

                route_kind = (
                    "page or application route"
                )

                routes.append(
                    {
                        "path": route_path,
                        "methods": methods,
                        "handler": node.name,
                        "file_path": (
                            relative_path
                        ),
                        "line_number": (
                            node.lineno
                        ),
                        "route_kind": (
                            route_kind
                        ),
                    }
                )

    return _deduplicate_dicts(
        routes,
        keys=(
            "path",
            "handler",
            "file_path",
            "line_number",
        ),
    )


def _detect_environment_variables(
    repository_path: str,
) -> list[
    dict[str, Any]
]:
    variables: list[
        dict[str, Any]
    ] = []

    repository_root = Path(
        repository_path
    )

    for path in repository_root.rglob(
        "*.py"
    ):
        if any(
            part
            in IGNORED_TREE_DIRECTORIES
            for part in path.parts
        ):
            continue

        try:
            source = path.read_text(
                encoding="utf-8",
                errors="ignore",
            )

            tree = ast.parse(source)

        except (
            OSError,
            SyntaxError,
        ):
            continue

        relative_path = str(
            path.relative_to(
                repository_root
            )
        ).replace(
            "\\",
            "/",
        )

        for node in ast.walk(tree):
            if not isinstance(
                node,
                ast.Call,
            ):
                continue

            variable_name: str | None = (
                None
            )

            default_value: Any = None

            if isinstance(
                node.func,
                ast.Attribute,
            ):
                attribute = (
                    node.func.attr
                )

                if (
                    attribute == "get"
                    and isinstance(
                        node.func.value,
                        ast.Attribute,
                    )
                    and node.func.value.attr
                    == "environ"
                ):
                    variable_name = (
                        _constant_string(
                            node.args[0]
                        )
                        if node.args
                        else None
                    )

                    if len(node.args) > 1:
                        default_value = (
                            _constant_value(
                                node.args[1]
                            )
                        )

                elif (
                    attribute
                    in ENV_CALL_NAMES
                ):
                    variable_name = (
                        _constant_string(
                            node.args[0]
                        )
                        if node.args
                        else None
                    )

                    if len(node.args) > 1:
                        default_value = (
                            _constant_value(
                                node.args[1]
                            )
                        )

            if not variable_name:
                continue

            variables.append(
                {
                    "name": variable_name,
                    "default": (
                        default_value
                    ),
                    "file_path": (
                        relative_path
                    ),
                    "line_number": (
                        getattr(
                            node,
                            "lineno",
                            None,
                        )
                    ),
                }
            )

    return _deduplicate_dicts(
        variables,
        keys=(
            "name",
            "file_path",
            "line_number",
        ),
    )


def _read_verified_dependencies(
    repository_path: str,
    manifest_paths: list[str],
) -> list[
    dict[str, Any]
]:
    dependencies: list[
        dict[str, Any]
    ] = []

    for relative_path in (
        manifest_paths
    ):
        normalized_path = (
            relative_path.replace(
                "\\",
                "/",
            )
        )

        full_path = (
            Path(repository_path)
            / normalized_path
        )

        file_name = (
            full_path.name
        )

        if (
            file_name
            in PYTHON_REQUIREMENT_FILES
        ):
            dependencies.extend(
                _read_python_requirements(
                    full_path,
                    normalized_path,
                )
            )

        elif file_name == "package.json":
            dependencies.extend(
                _read_package_json(
                    full_path,
                    normalized_path,
                )
            )

        elif file_name == "composer.json":
            dependencies.extend(
                _read_composer_json(
                    full_path,
                    normalized_path,
                )
            )

    return _deduplicate_dicts(
        dependencies,
        keys=(
            "name",
            "version",
            "ecosystem",
            "manifest",
        ),
    )


def _read_python_requirements(
    full_path: Path,
    relative_path: str,
) -> list[
    dict[str, Any]
]:
    dependencies: list[
        dict[str, Any]
    ] = []

    try:
        lines = full_path.read_text(
            encoding="utf-8",
            errors="ignore",
        ).splitlines()

    except OSError:
        return dependencies

    for raw_line in lines:
        line = raw_line.strip()

        if (
            not line
            or line.startswith("#")
            or line.startswith("-")
        ):
            continue

        name = line
        version: str | None = None

        match = re.match(
            r"^([A-Za-z0-9_.-]+)"
            r"\s*(==|~=|>=|<=|>|<)?"
            r"\s*(.*)$",
            line,
        )

        if match:
            name = match.group(1)

            operator = (
                match.group(2)
                or ""
            )

            remainder = (
                match.group(3)
                or ""
            ).strip()

            if operator and remainder:
                version = (
                    operator
                    + remainder
                )

        dependencies.append(
            {
                "name": name,
                "version": version,
                "ecosystem": "Python",
                "manifest": (
                    relative_path
                ),
            }
        )

    return dependencies


def _read_package_json(
    full_path: Path,
    relative_path: str,
) -> list[
    dict[str, Any]
]:
    try:
        payload = json.loads(
            full_path.read_text(
                encoding="utf-8",
                errors="ignore",
            )
        )

    except (
        OSError,
        ValueError,
        TypeError,
    ):
        return []

    dependency_maps = {
        "production": payload.get(
            "dependencies",
            {},
        ),
        "development": payload.get(
            "devDependencies",
            {},
        ),
    }

    dependencies: list[
        dict[str, Any]
    ] = []

    for scope, values in (
        dependency_maps.items()
    ):
        if not isinstance(
            values,
            dict,
        ):
            continue

        for name, version in (
            values.items()
        ):
            dependencies.append(
                {
                    "name": str(name),
                    "version": (
                        str(version)
                        if version
                        is not None
                        else None
                    ),
                    "ecosystem": (
                        "Node.js"
                    ),
                    "manifest": (
                        relative_path
                    ),
                    "scope": scope,
                }
            )

    return dependencies


def _read_composer_json(
    full_path: Path,
    relative_path: str,
) -> list[
    dict[str, Any]
]:
    try:
        payload = json.loads(
            full_path.read_text(
                encoding="utf-8",
                errors="ignore",
            )
        )

    except (
        OSError,
        ValueError,
        TypeError,
    ):
        return []

    dependency_maps = {
        "production": payload.get(
            "require",
            {},
        ),
        "development": payload.get(
            "require-dev",
            {},
        ),
    }

    dependencies: list[
        dict[str, Any]
    ] = []

    for scope, values in (
        dependency_maps.items()
    ):
        if not isinstance(
            values,
            dict,
        ):
            continue

        for name, version in (
            values.items()
        ):
            dependencies.append(
                {
                    "name": str(name),
                    "version": (
                        str(version)
                        if version
                        is not None
                        else None
                    ),
                    "ecosystem": "PHP",
                    "manifest": (
                        relative_path
                    ),
                    "scope": scope,
                }
            )

    return dependencies


def _constant_string(
    node: ast.AST,
) -> str | None:
    if (
        isinstance(
            node,
            ast.Constant,
        )
        and isinstance(
            node.value,
            str,
        )
    ):
        return node.value

    return None


def _constant_value(
    node: ast.AST,
) -> Any:
    if isinstance(
        node,
        ast.Constant,
    ):
        return node.value

    return None


def _deduplicate_dicts(
    values: list[
        dict[str, Any]
    ],
    keys: tuple[str, ...],
) -> list[
    dict[str, Any]
]:
    result: list[
        dict[str, Any]
    ] = []

    seen = set()

    for value in values:
        key = tuple(
            json.dumps(
                value.get(field),
                sort_keys=True,
                default=str,
            )
            for field in keys
        )

        if key in seen:
            continue

        seen.add(key)
        result.append(value)

    return result


@router.post(
    "",
    response_model=AnalysisStatusOut,
)
def create_analysis(
    payload: AnalysisCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        get_current_user
    ),
):
    repository = (
        db.query(Repository)
        .filter(
            Repository.id
            == payload.repository_id,
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

    branch = (
        payload.branch.strip()
        if payload.branch
        and payload.branch.strip()
        else repository.default_branch
        or "main"
    )

    analysis = Analysis(
        repository_id=(
            repository.id
        ),
        branch=branch,
        modules_enabled=",".join(
            payload.modules
        ),
        status=(
            AnalysisStatus.PENDING
        ),
        progress_percent=0,
    )

    db.add(analysis)
    db.commit()
    db.refresh(analysis)

    try:
        from app.workers.tasks import (
            run_analysis_task,
        )

        run_analysis_task.delay(
            analysis.id
        )

    except Exception:
        background_tasks.add_task(
            _run_inline,
            analysis.id,
            repository.clone_url,
        )

    return AnalysisStatusOut(
        id=analysis.id,
        status=analysis.status.value,
        progress_percent=0,
    )


@router.get(
    "/{analysis_id}/status",
    response_model=AnalysisStatusOut,
)
def get_status(
    analysis_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        get_current_user
    ),
):
    analysis, _repository = (
        _owned_analysis(
            db,
            analysis_id,
            current_user,
        )
    )

    status_value = (
        analysis.status.value
        if hasattr(
            analysis.status,
            "value",
        )
        else str(analysis.status)
    )

    return AnalysisStatusOut(
        id=analysis.id,
        status=status_value,
        progress_percent=(
            analysis.progress_percent
            or 0
        ),
        error_message=(
            analysis.error_message
        ),
    )


@router.get(
    "/{analysis_id}",
    response_model=AnalysisOut,
)
def get_analysis(
    analysis_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        get_current_user
    ),
):
    analysis, repository = (
        _owned_analysis(
            db,
            analysis_id,
            current_user,
        )
    )

    output = AnalysisOut.model_validate(
        analysis
    )

    output.status = (
        analysis.status.value
        if hasattr(
            analysis.status,
            "value",
        )
        else str(analysis.status)
    )

    output.repository_full_name = (
        repository.full_name
    )

    output.repository_clone_url = (
        repository.clone_url
    )

    return output


@router.get(
    "/{analysis_id}/issues",
    response_model=List[IssueOut],
)
def get_issues(
    analysis_id: str,
    severity: Optional[str] = Query(
        default=None
    ),
    category: Optional[str] = Query(
        default=None
    ),
    file_path: Optional[str] = Query(
        default=None
    ),
    language: Optional[str] = Query(
        default=None
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(
        get_current_user
    ),
):
    _owned_analysis(
        db,
        analysis_id,
        current_user,
    )

    query = (
        db.query(Issue)
        .filter(
            Issue.analysis_id
            == analysis_id
        )
    )

    if severity:
        query = query.filter(
            Issue.severity
            == severity
        )

    if category:
        query = query.filter(
            Issue.category
            == category
        )

    if file_path:
        query = query.filter(
            Issue.file_path
            == file_path
        )

    if language:
        query = query.filter(
            Issue.language
            == language
        )

    issues = (
        query
        .order_by(
            Issue.created_at.asc()
        )
        .all()
    )

    return [
        _serialize_issue(issue)
        for issue in issues
    ]


@router.patch(
    "/{analysis_id}/issues/{issue_id}",
    response_model=IssueOut,
)
def update_issue(
    analysis_id: str,
    issue_id: str,
    payload: IssueUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        get_current_user
    ),
):
    _owned_analysis(
        db,
        analysis_id,
        current_user,
    )

    issue = (
        db.query(Issue)
        .filter(
            Issue.id == issue_id,
            Issue.analysis_id
            == analysis_id,
        )
        .first()
    )

    if not issue:
        raise HTTPException(
            status_code=404,
            detail="Issue not found.",
        )

    issue.status = payload.status

    db.add(issue)
    db.commit()
    db.refresh(issue)

    return _serialize_issue(
        issue
    )


@router.post(
    "/{analysis_id}/generate-fix"
)
def generate_fix(
    analysis_id: str,
    payload: GenerateFixRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        get_current_user
    ),
):
    analysis, repository = (
        _owned_analysis(
            db,
            analysis_id,
            current_user,
        )
    )

    issue = (
        db.query(Issue)
        .filter(
            Issue.id
            == payload.issue_id,
            Issue.analysis_id
            == analysis.id,
        )
        .first()
    )

    if not issue:
        raise HTTPException(
            status_code=404,
            detail="Issue not found.",
        )

    repository_path = clone_repository(
        repository.clone_url,
        branch=analysis.branch,
    )

    try:
        source_path = (
            _normalized_relative_path(
                repository_path,
                issue.file_path,
            )
        )

        if not source_path.exists():
            raise HTTPException(
                status_code=404,
                detail=(
                    "The source file for this "
                    "issue was not found."
                ),
            )

        if not source_path.is_file():
            raise HTTPException(
                status_code=400,
                detail=(
                    "The issue path does not "
                    "point to a source file."
                ),
            )

        original_code = (
            source_path.read_text(
                encoding="utf-8",
                errors="ignore",
            )
        )

        try:
            result = generate_refactor(
                issue.file_path,
                original_code,
                issue.description
                or issue.title,
                issue.language
                or "",
            )

        except RefactoringError as exc:
            raise HTTPException(
                status_code=422,
                detail=(
                    "The generated fix was "
                    "rejected during validation: "
                    f"{exc}"
                ),
            ) from exc

        issue.suggested_fix = (
            result["explanation"]
        )

        issue.generated_patch = (
            result["improved_code"]
        )

        db.add(issue)
        db.commit()
        db.refresh(issue)

        return result

    finally:
        cleanup_clone(
            repository_path
        )


@router.post(
    "/{analysis_id}/generate-tests",
    response_model=List[
        GeneratedTestOut
    ],
)
def generate_tests(
    analysis_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        get_current_user
    ),
):
    from app.agents.test_generation_agent import (
        generate_test_file,
    )
    from app.analyzers.language_detector import (
        detect_languages,
    )

    analysis, repository = (
        _owned_analysis(
            db,
            analysis_id,
            current_user,
        )
    )

    repository_path = clone_repository(
        repository.clone_url,
        branch=analysis.branch,
    )

    try:
        stats = detect_languages(
            repository_path
        )

        issue_paths = [
            path
            for (path,) in (
                db.query(
                    Issue.file_path
                )
                .filter(
                    Issue.analysis_id
                    == analysis.id
                )
                .distinct()
                .all()
            )
        ]

        candidates: list[
            tuple[
                str,
                str,
            ]
        ] = []

        for issue_path in issue_paths:
            language = (
                _language_for_path(
                    stats.files_by_language,
                    issue_path,
                )
            )

            if language:
                candidate = (
                    language,
                    issue_path,
                )

                if candidate not in candidates:
                    candidates.append(
                        candidate
                    )

        for language, files in (
            stats.files_by_language.items()
        ):
            for relative_path in files:
                normalized = (
                    relative_path.lower()
                )

                if any(
                    marker in normalized
                    for marker in (
                        ".test.",
                        ".spec.",
                        "_test.",
                        "test_",
                        "/tests/",
                        "\\tests\\",
                    )
                ):
                    continue

                candidate = (
                    language,
                    relative_path,
                )

                if candidate not in candidates:
                    candidates.append(
                        candidate
                    )

        candidates = candidates[:6]

        generated_records: list[
            GeneratedTest
        ] = []

        for (
            language,
            relative_path,
        ) in candidates:
            source_path = (
                _normalized_relative_path(
                    repository_path,
                    relative_path,
                )
            )

            if (
                not source_path.exists()
                or not source_path.is_file()
            ):
                continue

            try:
                source = (
                    source_path.read_text(
                        encoding="utf-8",
                        errors="ignore",
                    )
                )

            except OSError:
                continue

            generated_test = (
                generate_test_file(
                    relative_path,
                    source,
                    language,
                )
            )

            if not generated_test:
                continue

            record = GeneratedTest(
                analysis_id=(
                    analysis.id
                ),
                **generated_test,
            )

            db.add(record)

            generated_records.append(
                record
            )

        db.commit()

        for record in generated_records:
            db.refresh(record)

        return [
            GeneratedTestOut.model_validate(
                record
            )
            for record
            in generated_records
        ]

    finally:
        cleanup_clone(
            repository_path
        )


@router.post(
    "/{analysis_id}/generate-docs",
    response_model=List[
        GeneratedDocumentOut
    ],
)
def generate_docs(
    analysis_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        get_current_user
    ),
):
    from app.agents.documentation_agent import (
        DOC_TYPES,
        generate_document,
    )
    from app.analyzers.language_detector import (
        detect_languages,
    )

    analysis, repository = (
        _owned_analysis(
            db,
            analysis_id,
            current_user,
        )
    )

    repository_path = clone_repository(
        repository.clone_url,
        branch=analysis.branch,
    )

    try:
        stats = detect_languages(
            repository_path
        )

        repository_tree = (
            _repository_tree(
                repository_path
            )
        )

        verified_routes = (
            _detect_python_routes(
                repository_path
            )
        )

        verified_env_vars = (
            _detect_environment_variables(
                repository_path
            )
        )

        verified_dependencies = (
            _read_verified_dependencies(
                repository_path,
                stats.dependency_manifests,
            )
        )

        languages = [
            language.strip()
            for language in (
                analysis.languages
                or ""
            ).split(",")
            if language.strip()
        ]

        generated_records: list[
            GeneratedDocument
        ] = []

        for doc_type in DOC_TYPES:
            document = generate_document(
                doc_type=doc_type,
                repo_name=(
                    repository.full_name
                ),
                repository_url=(
                    repository.clone_url
                ),
                languages=languages,
                frameworks=(
                    stats.frameworks
                ),
                architecture_summary=(
                    analysis
                    .architecture_summary
                    or ""
                ),
                repository_tree=(
                    repository_tree
                ),
                dependency_manifests=(
                    stats
                    .dependency_manifests
                ),
                verified_dependencies=(
                    verified_dependencies
                ),
                verified_routes=(
                    verified_routes
                ),
                verified_env_vars=(
                    verified_env_vars
                ),
            )

            record = (
                GeneratedDocument(
                    analysis_id=(
                        analysis.id
                    ),
                    **document,
                )
            )

            db.add(record)

            generated_records.append(
                record
            )

        db.commit()

        for record in generated_records:
            db.refresh(record)

        return [
            GeneratedDocumentOut.model_validate(
                record
            )
            for record
            in generated_records
        ]

    finally:
        cleanup_clone(
            repository_path
        )


@router.websocket(
    "/{analysis_id}/ws"
)
async def analysis_progress_ws(
    websocket: WebSocket,
    analysis_id: str,
):
    await websocket.accept()

    last_sent = 0

    try:
        while True:
            events = get_progress_events(
                analysis_id,
                start_index=last_sent,
            )

            if events:
                for update in events:
                    await websocket.send_text(
                        json.dumps(update)
                    )

                last_sent += len(
                    events
                )

                latest_progress = (
                    events[-1].get(
                        "progress_percent",
                        0,
                    )
                )

                if latest_progress >= 100:
                    break

            await asyncio.sleep(1)

    except WebSocketDisconnect:
        return