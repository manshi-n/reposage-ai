"""
Repository analysis orchestration.

Pipeline:

clone
-> detect languages
-> static analysis
-> dependency analysis
-> build RAG index
-> AI architecture review
-> scoring
-> persist issues
-> cleanup
"""

from __future__ import annotations

import os
import traceback
from datetime import datetime
from typing import Callable, Optional

from sqlalchemy.orm import Session

from app.agents.architecture_agent import (
    analyze_architecture,
)
from app.analyzers.css_analyzer import (
    analyze_css,
)
from app.analyzers.dependency_analyzer import (
    analyze_dependencies,
)
from app.analyzers.html_analyzer import (
    analyze_html,
)
from app.analyzers.js_analyzer import (
    analyze_javascript,
)
from app.analyzers.language_detector import (
    detect_languages,
)
from app.analyzers.multi_language_analyzer import (
    analyze_language_files,
)
from app.analyzers.php_analyzer import (
    analyze_php,
)
from app.analyzers.python_analyzer import (
    analyze_python,
)
from app.analyzers.security_analyzer import (
    scan_for_security_patterns,
)
from app.models.models import (
    Analysis,
    AnalysisStatus,
    Issue,
)
from app.services.clone_service import (
    CloneError,
    cleanup_clone,
    clone_repository,
)
from app.services.rag_service import (
    index_repository,
)
from app.services.scoring_service import (
    compute_scores,
)


ProgressCallback = Optional[
    Callable[
        [AnalysisStatus, int],
        None,
    ]
]


DEDICATED_ANALYZER_LANGUAGES = {
    "Python",
    "JavaScript",
    "TypeScript",
    "React",
    "React TypeScript",
    "PHP",
    "HTML",
    "CSS",
    "SCSS",
}


def _set_status(
    db: Session,
    analysis: Analysis,
    status: AnalysisStatus,
    percent: int,
    progress_callback: ProgressCallback,
) -> None:
    analysis.status = status
    analysis.progress_percent = percent

    db.add(analysis)
    db.commit()

    if progress_callback:
        progress_callback(
            status,
            percent,
        )


def run_analysis(
    db: Session,
    analysis: Analysis,
    clone_url: str,
    progress_cb: ProgressCallback = None,
) -> None:
    repository_path: str | None = None

    try:
        _set_status(
            db,
            analysis,
            AnalysisStatus.CLONING,
            5,
            progress_cb,
        )

        repository_path = clone_repository(
            clone_url,
            branch=analysis.branch,
        )

        _set_status(
            db,
            analysis,
            AnalysisStatus.DETECTING_LANGUAGES,
            20,
            progress_cb,
        )

        stats = detect_languages(
            repository_path
        )

        analysis.file_count = (
            stats.file_count
        )

        analysis.lines_of_code = (
            stats.lines_of_code
        )

        analysis.languages = ",".join(
            stats.languages.keys()
        )

        _set_status(
            db,
            analysis,
            AnalysisStatus.RUNNING_STATIC_ANALYSIS,
            40,
            progress_cb,
        )

        all_issues: list[dict] = []

        if "Python" in stats.languages:
            all_issues.extend(
                analyze_python(
                    repository_path
                )
            )

        if any(
            language in stats.languages
            for language in (
                "JavaScript",
                "TypeScript",
                "React",
                "React TypeScript",
            )
        ):
            all_issues.extend(
                analyze_javascript(
                    repository_path
                )
            )

        if "PHP" in stats.languages:
            all_issues.extend(
                analyze_php(
                    repository_path,
                    stats.files_by_language.get(
                        "PHP",
                        [],
                    ),
                )
            )

        if "HTML" in stats.languages:
            all_issues.extend(
                analyze_html(
                    repository_path,
                    stats.files_by_language.get(
                        "HTML",
                        [],
                    ),
                )
            )

        css_files = [
            *stats.files_by_language.get(
                "CSS",
                [],
            ),
            *stats.files_by_language.get(
                "SCSS",
                [],
            ),
            *stats.files_by_language.get(
                "Sass",
                [],
            ),
            *stats.files_by_language.get(
                "Less",
                [],
            ),
        ]

        if css_files:
            all_issues.extend(
                analyze_css(
                    repository_path,
                    css_files,
                )
            )

        for language, files in (
            stats.files_by_language.items()
        ):
            all_issues.extend(
                analyze_language_files(
                    repo_path=repository_path,
                    language=language,
                    files=files,
                )
            )

        all_issues.extend(
            analyze_dependencies(
                repository_path,
                stats.dependency_manifests,
            )
        )

        all_issues.extend(
            scan_for_security_patterns(
                repository_path
            )
        )

        all_issues = _deduplicate_issues(
            all_issues
        )

        _set_status(
            db,
            analysis,
            AnalysisStatus.BUILDING_INDEX,
            60,
            progress_cb,
        )

        all_files = [
            file_path
            for language_files
            in stats.files_by_language.values()
            for file_path in language_files
        ]

        index_repository(
            analysis.repository_id,
            repository_path,
            all_files,
        )

        _set_status(
            db,
            analysis,
            AnalysisStatus.RUNNING_AI_REVIEW,
            75,
            progress_cb,
        )

        analysis.architecture_summary = (
            analyze_architecture(
                repository_path,
                dict(stats.languages),
                stats.frameworks,
            )
        )

        has_tests = any(
            _looks_like_test_file(
                file_path
            )
            for file_path in all_files
        )

        has_docs = any(
            os.path.exists(
                os.path.join(
                    repository_path,
                    readme_name,
                )
            )
            for readme_name in (
                "README.md",
                "README.rst",
                "README.txt",
                "readme.md",
            )
        )

        supported_categories = (
            _supported_score_categories(
                stats.languages,
                bool(
                    stats.dependency_manifests
                ),
            )
        )

        scores = compute_scores(
            issues=all_issues,
            has_tests=has_tests,
            has_docs=has_docs,
            supported_categories=(
                supported_categories
            ),
        )

        for key, value in scores.items():
            setattr(
                analysis,
                key,
                value,
            )

        _set_status(
            db,
            analysis,
            AnalysisStatus.GENERATING_REPORT,
            90,
            progress_cb,
        )

        for issue_data in all_issues:
            db.add(
                Issue(
                    analysis_id=analysis.id,
                    **issue_data,
                )
            )

        db.commit()

        analysis.completed_at = (
            datetime.utcnow()
        )

        _set_status(
            db,
            analysis,
            AnalysisStatus.COMPLETE,
            100,
            progress_cb,
        )

    except CloneError as exc:
        analysis.status = (
            AnalysisStatus.FAILED
        )

        analysis.error_message = str(
            exc
        )

        db.add(analysis)
        db.commit()

    except Exception:
        analysis.status = (
            AnalysisStatus.FAILED
        )

        analysis.error_message = (
            traceback.format_exc(
                limit=5
            )
        )

        db.add(analysis)
        db.commit()

    finally:
        if repository_path:
            cleanup_clone(
                repository_path
            )


def _looks_like_test_file(
    file_path: str,
) -> bool:
    normalized = file_path.lower()

    return any(
        token in normalized
        for token in (
            "/tests/",
            "\\tests\\",
            "/test/",
            "\\test\\",
            ".test.",
            ".spec.",
            "_test.",
            "test_",
        )
    )


def _supported_score_categories(
    languages: dict,
    has_dependency_manifest: bool,
) -> set[str]:
    supported = {
        "security_score",
        "maintainability_score",
        "performance_score",
        "documentation_score",
        "testing_score",
        "architecture_score",
    }

    if not languages:
        return {
            "documentation_score",
            "architecture_score",
        }

    if has_dependency_manifest:
        supported.add(
            "security_score"
        )

    return supported


def _deduplicate_issues(
    issues: list[dict],
) -> list[dict]:
    deduplicated: list[dict] = []
    seen = set()

    for issue in issues:
        key = (
            issue.get("title"),
            issue.get("file_path"),
            issue.get("line_number"),
            issue.get("category"),
            issue.get("source_tool"),
        )

        if key in seen:
            continue

        seen.add(key)
        deduplicated.append(issue)

    return deduplicated