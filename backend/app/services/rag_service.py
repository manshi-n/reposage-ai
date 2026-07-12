"""
Repository-aware chat (RAG).

Pipeline (matches the spec): source files -> chunking -> embeddings ->
vector DB -> retrieval -> LLM answer with file/line references.

Uses Chroma as the vector store (local, no separate server process
required) with its bundled default embedding function. Swap
`get_collection`'s embedding_function for OpenAI/Voyage/etc. embeddings
in production if you want higher retrieval quality.
"""
import os
from typing import List, Tuple

import chromadb

from app.core.config import settings
from app.parsers.chunker import CodeChunk, chunk_repository
from app.services.llm_client import ask

os.makedirs(settings.VECTOR_DB_PATH, exist_ok=True)
_chroma_client = chromadb.PersistentClient(path=settings.VECTOR_DB_PATH)


def _collection_name(repository_id: str) -> str:
    return f"repo_{repository_id}".replace("-", "_")


def index_repository(repository_id: str, repo_path: str, files: List[str]) -> int:
    """Chunk every source file and upsert embeddings into the repo's collection."""
    collection = _chroma_client.get_or_create_collection(_collection_name(repository_id))

    chunks: List[CodeChunk] = chunk_repository(repo_path, files)
    if not chunks:
        return 0

    # Chroma upsert is capped per call in practice; batch to be safe.
    batch_size = 200
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i + batch_size]
        collection.upsert(
            ids=[f"{c.file_path}:{c.start_line}-{c.end_line}:{i + j}" for j, c in enumerate(batch)],
            documents=[c.content for c in batch],
            metadatas=[
                {"file_path": c.file_path, "start_line": c.start_line, "end_line": c.end_line}
                for c in batch
            ],
        )
    return len(chunks)


def retrieve_relevant_chunks(repository_id: str, question: str, k: int = 6) -> List[dict]:
    collection = _chroma_client.get_or_create_collection(_collection_name(repository_id))
    if collection.count() == 0:
        return []

    results = collection.query(query_texts=[question], n_results=min(k, collection.count()))
    chunks = []
    for doc, meta in zip(results["documents"][0], results["metadatas"][0]):
        chunks.append({"content": doc, "file_path": meta["file_path"],
                        "start_line": meta["start_line"], "end_line": meta["end_line"]})
    return chunks


def answer_question(repository_id: str, question: str) -> Tuple[str, List[str]]:
    chunks = retrieve_relevant_chunks(repository_id, question)

    if not chunks:
        return (
            "I don't have an index for this repository yet — run an analysis first "
            "so I can chunk and embed the source code before chatting about it.",
            [],
        )

    context_blocks = []
    referenced_files = []
    for c in chunks:
        ref = f"{c['file_path']}:{c['start_line']}-{c['end_line']}"
        referenced_files.append(ref)
        context_blocks.append(f"### {ref}\n```\n{c['content'][:1500]}\n```")

    system_prompt = (
        "You are a repository-aware coding assistant. Answer the developer's "
        "question using ONLY the provided code context. Always cite the "
        "specific file and line range for any claim you make, in the form "
        "`file_path:start-end`. If the context doesn't contain the answer, "
        "say so plainly instead of guessing."
    )
    user_prompt = f"Question: {question}\n\nRelevant code:\n\n" + "\n\n".join(context_blocks)

    answer = ask(system_prompt, user_prompt, max_tokens=1200)
    return answer, referenced_files
