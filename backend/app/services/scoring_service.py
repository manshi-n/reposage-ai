"""
Transparent repository scoring.

A category can be unavailable when RepoSage has insufficient evidence.
Unavailable scores are stored as None and excluded from the overall score.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, List, Optional


SEVERITY_PENALTY = {
    "critical": 25,
    "high": 12,
    "medium": 5,
    "low": 2,
    "info": 0,
}


CATEGORY_TO_SCORE_KEY = {
    "security": "security_score",
    "bug": "maintainability_score",
    "performance": "performance_score",
    "architecture": "architecture_score",
    "code_quality": "maintainability_score",
    "documentation": "documentation_score",
    "testing": "testing_score",
}


OVERALL_WEIGHTS = {
    "security_score": 0.30,
    "maintainability_score": 0.20,
    "performance_score": 0.15,
    "documentation_score": 0.10,
    "testing_score": 0.15,
    "architecture_score": 0.10,
}


def compute_scores(
    issues: List[Dict[str, Any]],
    has_tests: bool,
    has_docs: bool,
    supported_categories: set[str],
) -> Dict[str, Optional[int]]:
    scores: Dict[
        str,
        Optional[int],
    ] = {
        score_key: (
            100
            if score_key
            in supported_categories
            else None
        )
        for score_key
        in OVERALL_WEIGHTS
    }

    penalties: Dict[
        str,
        int,
    ] = defaultdict(int)

    for issue in issues:
        category = str(
            issue.get(
                "category",
                "",
            )
        )

        severity = str(
            issue.get(
                "severity",
                "info",
            )
        )

        score_key = (
            CATEGORY_TO_SCORE_KEY.get(
                category
            )
        )

        if (
            not score_key
            or scores.get(
                score_key
            )
            is None
        ):
            continue

        penalties[score_key] += (
            SEVERITY_PENALTY.get(
                severity,
                0,
            )
        )

    for score_key, penalty in (
        penalties.items()
    ):
        if scores.get(
            score_key
        ) is None:
            continue

        scores[score_key] = max(
            0,
            100 - penalty,
        )

    if (
        scores.get(
            "testing_score"
        )
        is not None
        and not has_tests
    ):
        scores["testing_score"] = min(
            scores["testing_score"] or 100,
            40,
        )

    if (
        scores.get(
            "documentation_score"
        )
        is not None
        and not has_docs
    ):
        scores[
            "documentation_score"
        ] = min(
            scores[
                "documentation_score"
            ]
            or 100,
            45,
        )

    available_scores = {
        key: value
        for key, value in scores.items()
        if value is not None
    }

    if not available_scores:
        scores["overall_score"] = None
        return scores

    total_weight = sum(
        OVERALL_WEIGHTS[key]
        for key in available_scores
    )

    weighted_total = sum(
        value
        * OVERALL_WEIGHTS[key]
        for key, value
        in available_scores.items()
    )

    scores["overall_score"] = round(
        weighted_total
        / total_weight
    )

    return scores