"""
Code chunking for repository chat (RAG).

Full Tree-sitter grammars give the most accurate function/class boundaries
(see the spec's parsing section) but require per-language compiled
grammars. To keep this repo runnable with zero native build steps, the
default chunker here uses simple, well-tested heuristics (regex on
`def`/`class`/`function` boundaries) and chunks anything else by fixed
line windows. Swap `chunk_file` internally for a Tree-sitter-backed
implementation when you add compiled grammars for your target languages.
"""
import os
import re
from dataclasses import dataclass
from typing import List

FUNCTION_BOUNDARY_PATTERNS = [
    re.compile(r"^\s*(def|class)\s+\w+"),                 # Python
    re.compile(r"^\s*(export\s+)?(async\s+)?function\s+\w+"),  # JS/TS
    re.compile(r"^\s*(export\s+)?(default\s+)?class\s+\w+"),   # JS/TS
    re.compile(r"^\s*(public|private|protected)?\s*\w[\w<>\[\]]*\s+\w+\s*\("),  # Java/C#
]

FALLBACK_WINDOW_LINES = 60


@dataclass
class CodeChunk:
    file_path: str
    start_line: int
    end_line: int
    content: str


def _is_boundary(line: str) -> bool:
    return any(p.match(line) for p in FUNCTION_BOUNDARY_PATTERNS)


def chunk_file(repo_path: str, rel_path: str) -> List[CodeChunk]:
    full_path = os.path.join(repo_path, rel_path)
    try:
        with open(full_path, "r", encoding="utf-8", errors="ignore") as fh:
            lines = fh.readlines()
    except OSError:
        return []

    boundaries = [i for i, line in enumerate(lines) if _is_boundary(line)]

    chunks: List[CodeChunk] = []
    if boundaries:
        boundaries.append(len(lines))
        for start, end in zip(boundaries, boundaries[1:]):
            content = "".join(lines[start:end]).strip()
            if content:
                chunks.append(CodeChunk(rel_path, start + 1, end, content))
    else:
        for i in range(0, len(lines), FALLBACK_WINDOW_LINES):
            content = "".join(lines[i:i + FALLBACK_WINDOW_LINES]).strip()
            if content:
                chunks.append(CodeChunk(rel_path, i + 1, min(i + FALLBACK_WINDOW_LINES, len(lines)), content))

    return chunks


def chunk_repository(repo_path: str, files: List[str]) -> List[CodeChunk]:
    all_chunks: List[CodeChunk] = []
    for rel_path in files:
        all_chunks.extend(chunk_file(repo_path, rel_path))
    return all_chunks
