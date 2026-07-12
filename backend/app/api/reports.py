"""
Download repository analysis reports in PDF, Markdown, JSON, CSV or HTML.
"""

from __future__ import annotations

import csv
import io
import json
from html import escape
from typing import Iterable

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.models import (
    Analysis,
    Issue,
    Repository,
    User,
)


router = APIRouter(
    prefix="/reports",
    tags=["reports"],
)


SUPPORTED_FORMATS = {
    "pdf",
    "md",
    "markdown",
    "json",
    "csv",
    "html",
}


def _get_owned_analysis(
    analysis_id: str,
    db: Session,
    current_user: User,
) -> tuple[Analysis, Repository]:
    analysis = (
        db.query(Analysis)
        .filter(Analysis.id == analysis_id)
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
            Repository.id == analysis.repository_id,
            Repository.owner_id == current_user.id,
        )
        .first()
    )

    if not repository:
        raise HTTPException(
            status_code=404,
            detail="Analysis not found.",
        )

    return analysis, repository


def _enum_value(value: object) -> str:
    return str(
        getattr(value, "value", value)
    )


def _safe_file_name(value: str) -> str:
    safe_name = "".join(
        character
        if character.isalnum()
        or character in {"-", "_"}
        else "-"
        for character in value
    )

    return safe_name.strip("-") or "repository"


def _download_response(
    content: bytes,
    media_type: str,
    repository_name: str,
    extension: str,
) -> Response:
    safe_name = _safe_file_name(
        repository_name
    )

    filename = (
        f"reposage-{safe_name}-report."
        f"{extension}"
    )

    return Response(
        content=content,
        media_type=media_type,
        headers={
            "Content-Disposition": (
                f'attachment; filename="{filename}"'
            ),
            "Access-Control-Expose-Headers": (
                "Content-Disposition"
            ),
        },
    )


@router.get("/{analysis_id}")
def download_report(
    analysis_id: str,
    format: str = Query(
        default="pdf",
        description=(
            "Report format: pdf, md, markdown, "
            "json, csv or html"
        ),
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(
        get_current_user
    ),
):
    normalized_format = (
        format.strip().lower()
    )

    if normalized_format not in SUPPORTED_FORMATS:
        raise HTTPException(
            status_code=400,
            detail=(
                "Unsupported report format. "
                "Use pdf, md, markdown, json, "
                "csv or html."
            ),
        )

    analysis, repository = (
        _get_owned_analysis(
            analysis_id,
            db,
            current_user,
        )
    )

    issues = (
        db.query(Issue)
        .filter(
            Issue.analysis_id == analysis_id
        )
        .order_by(
            Issue.created_at.asc()
        )
        .all()
    )

    if normalized_format == "json":
        return _render_json_report(
            repository,
            analysis,
            issues,
        )

    if normalized_format == "csv":
        return _render_csv_report(
            repository,
            issues,
        )

    markdown = _render_markdown(
        repository.full_name,
        analysis,
        issues,
    )

    if normalized_format in {
        "md",
        "markdown",
    }:
        return _download_response(
            content=markdown.encode("utf-8"),
            media_type=(
                "text/markdown; charset=utf-8"
            ),
            repository_name=repository.name,
            extension="md",
        )

    if normalized_format == "html":
        return _render_html_report(
            repository,
            markdown,
        )

    return _render_pdf_report(
        repository,
        analysis,
        issues,
    )


def _render_json_report(
    repository: Repository,
    analysis: Analysis,
    issues: Iterable[Issue],
) -> Response:
    payload = {
        "repository": {
            "id": repository.id,
            "name": repository.name,
            "full_name": repository.full_name,
            "clone_url": repository.clone_url,
            "default_branch": (
                repository.default_branch
            ),
        },
        "analysis": {
            "id": analysis.id,
            "branch": analysis.branch,
            "status": _enum_value(
                analysis.status
            ),
            "file_count": analysis.file_count,
            "lines_of_code": (
                analysis.lines_of_code
            ),
            "languages": analysis.languages,
            "architecture_summary": (
                analysis.architecture_summary
            ),
        },
        "scores": {
            "overall": analysis.overall_score,
            "security": (
                analysis.security_score
            ),
            "maintainability": (
                analysis.maintainability_score
            ),
            "performance": (
                analysis.performance_score
            ),
            "documentation": (
                analysis.documentation_score
            ),
            "testing": analysis.testing_score,
            "architecture": (
                analysis.architecture_score
            ),
        },
        "issues": [
            {
                "id": issue.id,
                "title": issue.title,
                "severity": _enum_value(
                    issue.severity
                ),
                "category": _enum_value(
                    issue.category
                ),
                "file_path": issue.file_path,
                "line_number": (
                    issue.line_number
                ),
                "language": issue.language,
                "description": (
                    issue.description
                ),
                "risk": issue.risk,
                "suggested_fix": (
                    issue.suggested_fix
                ),
                "source_tool": (
                    issue.source_tool
                ),
                "status": _enum_value(
                    issue.status
                ),
            }
            for issue in issues
        ],
    }

    return _download_response(
        content=json.dumps(
            payload,
            indent=2,
            ensure_ascii=False,
        ).encode("utf-8"),
        media_type=(
            "application/json; charset=utf-8"
        ),
        repository_name=repository.name,
        extension="json",
    )


def _render_csv_report(
    repository: Repository,
    issues: Iterable[Issue],
) -> Response:
    buffer = io.StringIO(
        newline=""
    )

    writer = csv.writer(buffer)

    writer.writerow(
        [
            "title",
            "severity",
            "category",
            "file_path",
            "line_number",
            "language",
            "source_tool",
            "status",
            "description",
            "suggested_fix",
        ]
    )

    for issue in issues:
        writer.writerow(
            [
                issue.title,
                _enum_value(
                    issue.severity
                ),
                _enum_value(
                    issue.category
                ),
                issue.file_path,
                issue.line_number or "",
                issue.language or "",
                issue.source_tool or "",
                _enum_value(
                    issue.status
                ),
                issue.description or "",
                issue.suggested_fix or "",
            ]
        )

    return _download_response(
        content=buffer.getvalue().encode(
            "utf-8-sig"
        ),
        media_type=(
            "text/csv; charset=utf-8"
        ),
        repository_name=repository.name,
        extension="csv",
    )


def _render_markdown(
    repository_name: str,
    analysis: Analysis,
    issues: Iterable[Issue],
) -> str:
    issue_list = list(issues)

    lines = [
        (
            "# RepoSage AI Report — "
            f"{repository_name}"
        ),
        "",
        "## Repository summary",
        "",
        f"- **Branch:** `{analysis.branch}`",
        (
            "- **Status:** "
            f"{_enum_value(analysis.status)}"
        ),
        (
            "- **Files scanned:** "
            f"{analysis.file_count or 0}"
        ),
        (
            "- **Lines of code:** "
            f"{analysis.lines_of_code or 0}"
        ),
        (
            "- **Languages:** "
            f"{analysis.languages or 'Unknown'}"
        ),
        (
            "- **Total findings:** "
            f"{len(issue_list)}"
        ),
        "",
        "## Scores",
        "",
        "| Category | Score |",
        "|---|---:|",
        (
            "| Overall | "
            f"{analysis.overall_score or 0} |"
        ),
        (
            "| Security | "
            f"{analysis.security_score or 0} |"
        ),
        (
            "| Maintainability | "
            f"{analysis.maintainability_score or 0} |"
        ),
        (
            "| Performance | "
            f"{analysis.performance_score or 0} |"
        ),
        (
            "| Documentation | "
            f"{analysis.documentation_score or 0} |"
        ),
        (
            "| Testing | "
            f"{analysis.testing_score or 0} |"
        ),
        (
            "| Architecture | "
            f"{analysis.architecture_score or 0} |"
        ),
        "",
        "## Architecture summary",
        "",
        (
            analysis.architecture_summary
            or "_Not generated._"
        ),
        "",
        "## Findings",
        "",
    ]

    if not issue_list:
        lines.append(
            "No issues were detected."
        )

    for index, issue in enumerate(
        issue_list,
        start=1,
    ):
        location = issue.file_path

        if issue.line_number:
            location += (
                f":{issue.line_number}"
            )

        lines.extend(
            [
                (
                    f"### {index}. "
                    f"{issue.title}"
                ),
                "",
                (
                    "- **Severity:** "
                    f"{_enum_value(issue.severity)}"
                ),
                (
                    "- **Category:** "
                    f"{_enum_value(issue.category)}"
                ),
                (
                    "- **Location:** "
                    f"`{location}`"
                ),
                (
                    "- **Source:** "
                    f"{issue.source_tool or 'unknown'}"
                ),
                (
                    "- **Status:** "
                    f"{_enum_value(issue.status)}"
                ),
                "",
                (
                    issue.description
                    or "No description provided."
                ),
                "",
                "**Suggested fix:**",
                "",
                (
                    issue.suggested_fix
                    or "No suggested fix provided."
                ),
                "",
            ]
        )

    return "\n".join(lines)


def _render_html_report(
    repository: Repository,
    markdown: str,
) -> Response:
    try:
        import markdown2
    except ImportError as exc:
        raise HTTPException(
            status_code=500,
            detail=(
                "HTML report generation "
                "requires markdown2."
            ),
        ) from exc

    rendered = markdown2.markdown(
        markdown,
        extras=[
            "tables",
            "fenced-code-blocks",
        ],
    )

    html = f"""
    <!doctype html>
    <html lang="en">
      <head>
        <meta charset="utf-8">
        <meta
          name="viewport"
          content="width=device-width,initial-scale=1"
        >
        <title>
          RepoSage report — {escape(repository.full_name)}
        </title>
        <style>
          body {{
            max-width: 960px;
            margin: 40px auto;
            padding: 0 24px;
            color: #1f2937;
            font-family: Arial, sans-serif;
            line-height: 1.65;
          }}

          table {{
            width: 100%;
            border-collapse: collapse;
          }}

          th, td {{
            border: 1px solid #d1d5db;
            padding: 8px 10px;
            text-align: left;
          }}

          code {{
            background: #f3f4f6;
            padding: 2px 5px;
            border-radius: 4px;
          }}
        </style>
      </head>
      <body>
        {rendered}
      </body>
    </html>
    """

    return _download_response(
        content=html.encode("utf-8"),
        media_type=(
            "text/html; charset=utf-8"
        ),
        repository_name=repository.name,
        extension="html",
    )


def _render_pdf_report(
    repository: Repository,
    analysis: Analysis,
    issues: Iterable[Issue],
) -> Response:
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import (
            ParagraphStyle,
            getSampleStyleSheet,
        )
        from reportlab.lib.units import mm
        from reportlab.platypus import (
            PageBreak,
            Paragraph,
            SimpleDocTemplate,
            Spacer,
            Table,
            TableStyle,
        )
    except ImportError as exc:
        raise HTTPException(
            status_code=500,
            detail=(
                "PDF generation requires "
                "the reportlab package."
            ),
        ) from exc

    issue_list = list(issues)
    buffer = io.BytesIO()

    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
        title=(
            f"RepoSage report — "
            f"{repository.full_name}"
        ),
    )

    styles = getSampleStyleSheet()

    small_style = ParagraphStyle(
        "Small",
        parent=styles["BodyText"],
        fontSize=8.5,
        leading=11,
    )

    story = [
        Paragraph(
            (
                "RepoSage AI Report — "
                f"{escape(repository.full_name)}"
            ),
            styles["Title"],
        ),
        Spacer(1, 10),
        Paragraph(
            (
                f"Branch: {escape(analysis.branch or 'unknown')}"
                f" &nbsp;&nbsp; | &nbsp;&nbsp; "
                f"Files: {analysis.file_count or 0}"
                f" &nbsp;&nbsp; | &nbsp;&nbsp; "
                f"Lines: {analysis.lines_of_code or 0}"
            ),
            styles["BodyText"],
        ),
        Spacer(1, 14),
    ]

    score_data = [
        ["Category", "Score"],
        [
            "Overall",
            analysis.overall_score or 0,
        ],
        [
            "Security",
            analysis.security_score or 0,
        ],
        [
            "Maintainability",
            (
                analysis.maintainability_score
                or 0
            ),
        ],
        [
            "Performance",
            analysis.performance_score or 0,
        ],
        [
            "Documentation",
            (
                analysis.documentation_score
                or 0
            ),
        ],
        [
            "Testing",
            analysis.testing_score or 0,
        ],
        [
            "Architecture",
            analysis.architecture_score or 0,
        ],
    ]

    score_table = Table(
        score_data,
        colWidths=[
            70 * mm,
            30 * mm,
        ],
    )

    score_table.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, 0),
                    colors.HexColor("#111827"),
                ),
                (
                    "TEXTCOLOR",
                    (0, 0),
                    (-1, 0),
                    colors.white,
                ),
                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.4,
                    colors.HexColor("#d1d5db"),
                ),
                (
                    "PADDING",
                    (0, 0),
                    (-1, -1),
                    7,
                ),
            ]
        )
    )

    story.extend(
        [
            score_table,
            Spacer(1, 18),
            Paragraph(
                "Architecture summary",
                styles["Heading2"],
            ),
            Paragraph(
                escape(
                    analysis.architecture_summary
                    or "Not generated."
                ).replace(
                    "\n",
                    "<br/>",
                ),
                styles["BodyText"],
            ),
            PageBreak(),
            Paragraph(
                "Findings",
                styles["Heading1"],
            ),
            Spacer(1, 8),
        ]
    )

    if not issue_list:
        story.append(
            Paragraph(
                "No issues were detected.",
                styles["BodyText"],
            )
        )

    for index, issue in enumerate(
        issue_list[:200],
        start=1,
    ):
        location = issue.file_path

        if issue.line_number:
            location += (
                f":{issue.line_number}"
            )

        story.extend(
            [
                Paragraph(
                    (
                        f"{index}. "
                        f"{escape(issue.title)}"
                    ),
                    styles["Heading3"],
                ),
                Paragraph(
                    (
                        f"<b>Severity:</b> "
                        f"{escape(_enum_value(issue.severity))}"
                        f"<br/><b>Category:</b> "
                        f"{escape(_enum_value(issue.category))}"
                        f"<br/><b>Location:</b> "
                        f"{escape(location)}"
                    ),
                    small_style,
                ),
                Spacer(1, 4),
                Paragraph(
                    escape(
                        issue.description
                        or "No description provided."
                    ),
                    styles["BodyText"],
                ),
                Spacer(1, 4),
                Paragraph(
                    (
                        "<b>Suggested fix:</b> "
                        f"{escape(issue.suggested_fix or 'None')}"
                    ),
                    styles["BodyText"],
                ),
                Spacer(1, 12),
            ]
        )

    document.build(story)

    return _download_response(
        content=buffer.getvalue(),
        media_type="application/pdf",
        repository_name=repository.name,
        extension="pdf",
    )