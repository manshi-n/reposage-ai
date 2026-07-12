"""
Repository-aware chat endpoint. See services/rag_service.py for the
retrieval + LLM pipeline.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.models import ChatMessage, ChatSession, Repository, User
from app.schemas.schemas import ChatRequest, ChatResponse
from app.services.rag_service import answer_question

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/{repository_id}", response_model=ChatResponse)
def chat_with_repository(
    repository_id: str,
    payload: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    repo = (
        db.query(Repository)
        .filter(Repository.id == repository_id, Repository.owner_id == current_user.id)
        .first()
    )
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found.")

    session = None
    if payload.session_id:
        session = (
            db.query(ChatSession)
            .filter(
                ChatSession.id == payload.session_id,
                ChatSession.user_id == current_user.id,
            )
            .first()
        )
        if not session:
            raise HTTPException(status_code=404, detail="Chat session not found.")
    else:
        session = ChatSession(repository_id=repository_id, user_id=current_user.id)
        db.add(session)
        db.commit()
        db.refresh(session)

    db.add(ChatMessage(session_id=session.id, role="user", content=payload.message))

    answer, referenced_files = answer_question(repository_id, payload.message)

    db.add(ChatMessage(
        session_id=session.id, role="assistant", content=answer,
        referenced_files=",".join(referenced_files),
    ))
    db.commit()

    return ChatResponse(session_id=session.id, answer=answer, referenced_files=referenced_files)