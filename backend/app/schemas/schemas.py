"""
Pydantic (v2) schemas used by the API layer.
"""
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, EmailStr


# ---------- Auth ----------
class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: Optional[str] = None


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    email: EmailStr
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


# ---------- Repositories ----------
class RepositoryConnect(BaseModel):
    full_name: Optional[str] = None  # "owner/repo" if using GitHub OAuth
    clone_url: str  # https URL, required for public-repo mode
    is_private: bool = False
    default_branch: str = "main"


class RepositoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    name: str
    full_name: str
    clone_url: str
    is_private: bool
    default_branch: str
    created_at: datetime


# ---------- Analyses ----------
class AnalysisCreate(BaseModel):
    repository_id: str
    branch: str = "main"
    max_files: int = 2000
    languages: Optional[List[str]] = None
    depth: str = "standard"  # quick | standard | deep
    generate_tests: bool = True
    generate_docs: bool = True
    scan_dependencies: bool = True
    modules: List[str] = [
        "bugs", "security", "performance", "architecture", "quality", "docs", "tests",
    ]


class AnalysisStatusOut(BaseModel):
    id: str
    status: str
    progress_percent: int
    error_message: Optional[str] = None


class ScoreBreakdown(BaseModel):
    overall_score: Optional[int]
    security_score: Optional[int]
    maintainability_score: Optional[int]
    performance_score: Optional[int]
    documentation_score: Optional[int]
    testing_score: Optional[int]
    architecture_score: Optional[int]

class AnalysisOut(BaseModel):
    model_config = ConfigDict(
        from_attributes=True
    )

    id: str
    repository_id: str

    repository_full_name: Optional[
        str
    ] = None

    repository_clone_url: Optional[
        str
    ] = None

    branch: str
    status: str
    progress_percent: int

    file_count: Optional[int]
    lines_of_code: Optional[int]
    languages: Optional[str]
    architecture_summary: Optional[str]

    overall_score: Optional[int]
    security_score: Optional[int]
    maintainability_score: Optional[int]
    performance_score: Optional[int]
    documentation_score: Optional[int]
    testing_score: Optional[int]
    architecture_score: Optional[int]

    created_at: datetime
    completed_at: Optional[datetime]



# ---------- Issues ----------
class IssueOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    title: str
    severity: str
    category: str
    file_path: str
    line_number: Optional[int]
    language: Optional[str]
    description: Optional[str]
    risk: Optional[str]
    suggested_fix: Optional[str]
    generated_patch: Optional[str]
    source_tool: str
    status: str


class IssueUpdate(BaseModel):
    status: str  # resolved | false_positive | open


class GenerateFixRequest(BaseModel):
    issue_id: str


# ---------- Tests / Docs ----------
class GeneratedTestOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    target_file: str
    framework: str
    file_name: str
    content: str


class GeneratedDocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    doc_type: str
    title: str
    content: str


# ---------- Chat ----------
class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None


class ChatMessageOut(BaseModel):
    role: str
    content: str
    referenced_files: Optional[str] = None
    created_at: datetime


class ChatResponse(BaseModel):
    session_id: str
    answer: str
    referenced_files: List[str] = []
