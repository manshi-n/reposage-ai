"""
SQLAlchemy ORM models.

Mirrors the table list from the project spec: users, github_accounts,
repositories, repository_branches, analyses, issues, generated_tests,
generated_documents, chat_sessions, chat_messages, reports, pull_requests.
"""
import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from app.core.database import Base


def gen_uuid() -> str:
    return str(uuid.uuid4())


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=gen_uuid)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=True)  # null if GitHub-only login
    full_name = Column(String, nullable=True)
    avatar_url = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    github_account = relationship("GitHubAccount", back_populates="user", uselist=False)
    repositories = relationship("Repository", back_populates="owner")


class GitHubAccount(Base):
    __tablename__ = "github_accounts"

    id = Column(String, primary_key=True, default=gen_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    github_username = Column(String, nullable=False)
    access_token_encrypted = Column(Text, nullable=False)
    scopes = Column(String, default="repo,read:user")
    connected_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="github_account")


class Repository(Base):
    __tablename__ = "repositories"

    id = Column(String, primary_key=True, default=gen_uuid)
    owner_id = Column(String, ForeignKey("users.id"), nullable=False)
    name = Column(String, nullable=False)
    full_name = Column(String, nullable=False)  # e.g. "octocat/hello-world"
    clone_url = Column(String, nullable=False)
    is_private = Column(Boolean, default=False)
    default_branch = Column(String, default="main")
    created_at = Column(DateTime, default=datetime.utcnow)

    owner = relationship("User", back_populates="repositories")
    branches = relationship("RepositoryBranch", back_populates="repository")
    analyses = relationship("Analysis", back_populates="repository")


class RepositoryBranch(Base):
    __tablename__ = "repository_branches"

    id = Column(String, primary_key=True, default=gen_uuid)
    repository_id = Column(String, ForeignKey("repositories.id"), nullable=False)
    name = Column(String, nullable=False)

    repository = relationship("Repository", back_populates="branches")


class AnalysisStatus(str, enum.Enum):
    PENDING = "pending"
    CLONING = "cloning"
    DETECTING_LANGUAGES = "detecting_languages"
    RUNNING_STATIC_ANALYSIS = "running_static_analysis"
    BUILDING_INDEX = "building_index"
    RUNNING_AI_REVIEW = "running_ai_review"
    GENERATING_REPORT = "generating_report"
    COMPLETE = "complete"
    FAILED = "failed"


class Analysis(Base):
    __tablename__ = "analyses"

    id = Column(String, primary_key=True, default=gen_uuid)
    repository_id = Column(String, ForeignKey("repositories.id"), nullable=False)
    branch = Column(String, default="main")
    status = Column(Enum(AnalysisStatus), default=AnalysisStatus.PENDING)
    progress_percent = Column(Integer, default=0)

    modules_enabled = Column(String, default="bugs,security,performance,architecture,quality,docs,tests")

    overall_score = Column(Integer, nullable=True)
    security_score = Column(Integer, nullable=True)
    maintainability_score = Column(Integer, nullable=True)
    performance_score = Column(Integer, nullable=True)
    documentation_score = Column(Integer, nullable=True)
    testing_score = Column(Integer, nullable=True)
    architecture_score = Column(Integer, nullable=True)

    file_count = Column(Integer, nullable=True)
    lines_of_code = Column(Integer, nullable=True)
    languages = Column(String, nullable=True)  # comma separated
    architecture_summary = Column(Text, nullable=True)

    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    repository = relationship("Repository", back_populates="analyses")
    issues = relationship("Issue", back_populates="analysis")
    generated_tests = relationship("GeneratedTest", back_populates="analysis")
    generated_documents = relationship("GeneratedDocument", back_populates="analysis")


class Severity(str, enum.Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class IssueCategory(str, enum.Enum):
    BUG = "bug"
    SECURITY = "security"
    PERFORMANCE = "performance"
    ARCHITECTURE = "architecture"
    CODE_QUALITY = "code_quality"
    DOCUMENTATION = "documentation"
    TESTING = "testing"


class IssueStatus(str, enum.Enum):
    OPEN = "open"
    RESOLVED = "resolved"
    FALSE_POSITIVE = "false_positive"


class Issue(Base):
    __tablename__ = "issues"

    id = Column(String, primary_key=True, default=gen_uuid)
    analysis_id = Column(String, ForeignKey("analyses.id"), nullable=False)

    title = Column(String, nullable=False)
    severity = Column(Enum(Severity), nullable=False)
    category = Column(Enum(IssueCategory), nullable=False)
    file_path = Column(String, nullable=False)
    line_number = Column(Integer, nullable=True)
    language = Column(String, nullable=True)

    description = Column(Text, nullable=True)
    risk = Column(Text, nullable=True)
    suggested_fix = Column(Text, nullable=True)
    generated_patch = Column(Text, nullable=True)

    source_tool = Column(String, default="ai")  # e.g. "bandit", "eslint", "ai-agent"
    status = Column(Enum(IssueStatus), default=IssueStatus.OPEN)
    created_at = Column(DateTime, default=datetime.utcnow)

    analysis = relationship("Analysis", back_populates="issues")


class GeneratedTest(Base):
    __tablename__ = "generated_tests"

    id = Column(String, primary_key=True, default=gen_uuid)
    analysis_id = Column(String, ForeignKey("analyses.id"), nullable=False)
    target_file = Column(String, nullable=False)
    framework = Column(String, nullable=False)
    file_name = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    analysis = relationship("Analysis", back_populates="generated_tests")


class GeneratedDocument(Base):
    __tablename__ = "generated_documents"

    id = Column(String, primary_key=True, default=gen_uuid)
    analysis_id = Column(String, ForeignKey("analyses.id"), nullable=False)
    doc_type = Column(String, nullable=False)  # readme, api_docs, architecture, contributing...
    title = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    analysis = relationship("Analysis", back_populates="generated_documents")


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id = Column(String, primary_key=True, default=gen_uuid)
    repository_id = Column(String, ForeignKey("repositories.id"), nullable=False)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    messages = relationship("ChatMessage", back_populates="session")


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(String, primary_key=True, default=gen_uuid)
    session_id = Column(String, ForeignKey("chat_sessions.id"), nullable=False)
    role = Column(String, nullable=False)  # user | assistant
    content = Column(Text, nullable=False)
    referenced_files = Column(Text, nullable=True)  # JSON-encoded list of {file, line}
    created_at = Column(DateTime, default=datetime.utcnow)

    session = relationship("ChatSession", back_populates="messages")


class Report(Base):
    __tablename__ = "reports"

    id = Column(String, primary_key=True, default=gen_uuid)
    analysis_id = Column(String, ForeignKey("analyses.id"), nullable=False)
    format = Column(String, nullable=False)  # pdf, markdown, html, json, csv
    file_path = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class PullRequest(Base):
    __tablename__ = "pull_requests"

    id = Column(String, primary_key=True, default=gen_uuid)
    analysis_id = Column(String, ForeignKey("analyses.id"), nullable=False)
    github_pr_number = Column(Integer, nullable=True)
    github_pr_url = Column(String, nullable=True)
    title = Column(String, nullable=False)
    status = Column(String, default="draft")
    created_at = Column(DateTime, default=datetime.utcnow)
