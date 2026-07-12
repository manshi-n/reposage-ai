"""Authentication endpoints for email/password and GitHub OAuth."""
import json
import secrets
from urllib.parse import urlencode

import redis
from fastapi import APIRouter, Cookie, Depends, HTTPException
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.database import get_db
from app.core.encryption import encrypt_token
from app.core.security import create_access_token, hash_password, verify_password
from app.models.models import GitHubAccount, User
from app.schemas.schemas import TokenOut, UserCreate, UserLogin, UserOut
from app.services.github_service import GitHubService

router = APIRouter(prefix="/auth", tags=["auth"])


class GitHubTicketIn(BaseModel):
    ticket: str


def _redis_client() -> redis.Redis:
    return redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)


@router.post("/signup", response_model=TokenOut)
def signup(payload: UserCreate, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(status_code=400, detail="An account with this email already exists.")

    user = User(
        email=payload.email,
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token(subject=user.id)
    return TokenOut(access_token=token, user=UserOut.model_validate(user))


@router.post("/login", response_model=TokenOut)
def login(payload: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not user.hashed_password or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect email or password.")

    token = create_access_token(subject=user.id)
    return TokenOut(access_token=token, user=UserOut.model_validate(user))


@router.get("/github/start")
def github_oauth_start() -> RedirectResponse:
    """Start OAuth on the backend so state and redirect URI cannot be spoofed by the UI."""
    if not settings.GITHUB_CLIENT_ID or not settings.GITHUB_CLIENT_SECRET:
        raise HTTPException(status_code=503, detail="GitHub OAuth is not configured.")

    state = secrets.token_urlsafe(32)
    params = {
        "client_id": settings.GITHUB_CLIENT_ID,
        "redirect_uri": settings.GITHUB_OAUTH_CALLBACK_URL,
        "scope": "read:user user:email repo",
        "state": state,
        "allow_signup": "true",
    }
    response = RedirectResponse(
        f"https://github.com/login/oauth/authorize?{urlencode(params)}",
        status_code=302,
    )
    response.set_cookie(
        "github_oauth_state",
        state,
        max_age=600,
        httponly=True,
        secure=(settings.ENV == "production" or settings.ENVIRONMENT == "production"),
        samesite="lax",
        path="/",
    )
    return response


@router.get("/github/callback")
async def github_oauth_callback(
    code: str,
    state: str,
    github_oauth_state: str | None = Cookie(default=None),
    db: Session = Depends(get_db),
) -> RedirectResponse:
    """Validate GitHub's callback, link/create the user, then issue a one-time login ticket."""
    if not github_oauth_state or not secrets.compare_digest(state, github_oauth_state):
        raise HTTPException(status_code=400, detail="Invalid or expired GitHub OAuth state.")

    try:
        access_token = await GitHubService().exchange_code_for_token(code)
        gh = GitHubService(access_token=access_token)
        profile = await gh.get_authenticated_user()
        email = profile.get("email") or await gh.get_primary_verified_email()
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"GitHub authentication failed: {exc}") from exc

    if not email:
        raise HTTPException(status_code=400, detail="GitHub did not provide a verified email address.")

    user = db.query(User).filter(User.email == email).first()
    if not user:
        user = User(
            email=email,
            full_name=profile.get("name") or profile.get("login"),
            avatar_url=profile.get("avatar_url"),
        )
        db.add(user)
        db.flush()
    else:
        user.full_name = user.full_name or profile.get("name") or profile.get("login")
        user.avatar_url = profile.get("avatar_url") or user.avatar_url

    github_account = db.query(GitHubAccount).filter(GitHubAccount.user_id == user.id).first()
    encrypted_token = encrypt_token(access_token)
    if not github_account:
        github_account = GitHubAccount(
            user_id=user.id,
            github_username=profile["login"],
            access_token_encrypted=encrypted_token,
            scopes="read:user,user:email,repo",
        )
        db.add(github_account)
    else:
        github_account.github_username = profile["login"]
        github_account.access_token_encrypted = encrypted_token
        github_account.scopes = "read:user,user:email,repo"

    db.commit()
    db.refresh(user)

    ticket = secrets.token_urlsafe(32)
    payload = {
        "access_token": create_access_token(subject=user.id),
        "user": UserOut.model_validate(user).model_dump(mode="json"),
    }
    try:
        _redis_client().setex(f"oauth_ticket:{ticket}", 60, json.dumps(payload))
    except redis.RedisError as exc:
        raise HTTPException(status_code=503, detail="Login session service is unavailable.") from exc

    response = RedirectResponse(
        f"{settings.GITHUB_FRONTEND_CALLBACK_URL}?ticket={ticket}",
        status_code=302,
    )
    response.delete_cookie("github_oauth_state", path="/")
    return response


@router.post("/github/exchange", response_model=TokenOut)
def exchange_github_ticket(payload: GitHubTicketIn):
    """Exchange a short-lived, single-use ticket for the application's JWT."""
    key = f"oauth_ticket:{payload.ticket}"
    client = _redis_client()
    try:
        raw = client.getdel(key)
    except redis.RedisError as exc:
        raise HTTPException(status_code=503, detail="Login session service is unavailable.") from exc
    if not raw:
        raise HTTPException(status_code=400, detail="GitHub login ticket is invalid or expired.")
    return TokenOut.model_validate(json.loads(raw))


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)):
    return UserOut.model_validate(current_user)


@router.post("/logout")
def logout():
    return {"detail": "Logged out."}
