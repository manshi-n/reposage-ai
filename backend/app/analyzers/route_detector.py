from __future__ import annotations

import ast
from pathlib import Path
from typing import Any


def detect_python_routes(
    repo_path: str,
) -> list[dict[str, Any]]:
    routes: list[dict[str, Any]] = []

    for path in Path(repo_path).rglob(
        "*.py"
    ):
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
                repo_path
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

            for decorator in node.decorator_list:
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

                if function.attr not in {
                    "route",
                    "get",
                    "post",
                    "put",
                    "patch",
                    "delete",
                }:
                    continue

                if (
                    not decorator.args
                    or not isinstance(
                        decorator.args[0],
                        ast.Constant,
                    )
                ):
                    continue

                route_path = (
                    decorator.args[0].value
                )

                methods = [
                    function.attr.upper()
                ]

                if function.attr == "route":
                    methods = ["GET"]

                    for keyword in (
                        decorator.keywords
                    ):
                        if (
                            keyword.arg
                            == "methods"
                            and isinstance(
                                keyword.value,
                                (
                                    ast.List,
                                    ast.Tuple,
                                ),
                            )
                        ):
                            methods = [
                                element.value
                                for element
                                in keyword.value.elts
                                if isinstance(
                                    element,
                                    ast.Constant,
                                )
                            ]

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
                    }
                )

    return routes