"""
GitHub OAuth and REST API helpers.
"""

from __future__ import annotations

import base64
from typing import Any, Dict, List, Optional
from urllib.parse import quote

import httpx

from app.core.config import settings


GITHUB_API_URL = "https://api.github.com"
GITHUB_API_VERSION = "2022-11-28"


class GitHubAPIError(Exception):
    """Raised when GitHub rejects a request."""


class GitHubService:
    def __init__(
        self,
        access_token: Optional[str] = None,
    ):
        self.access_token = access_token

    def _headers(self) -> Dict[str, str]:
        headers = {
            "Accept": (
                "application/vnd.github+json"
            ),
            "X-GitHub-Api-Version": (
                GITHUB_API_VERSION
            ),
            "User-Agent": "RepoSage-AI",
        }

        if self.access_token:
            headers["Authorization"] = (
                f"Bearer {self.access_token}"
            )

        return headers

    async def _request(
        self,
        method: str,
        url: str,
        **kwargs: Any,
    ) -> httpx.Response:
        async with httpx.AsyncClient(
            timeout=45.0,
            follow_redirects=True,
        ) as client:
            response = await client.request(
                method,
                url,
                headers=self._headers(),
                **kwargs,
            )

        if response.is_error:
            try:
                payload = response.json()
                message = (
                    payload.get("message")
                    or payload.get(
                        "error_description"
                    )
                    or str(payload)
                )
            except ValueError:
                message = response.text

            raise GitHubAPIError(
                f"GitHub API returned "
                f"{response.status_code}: "
                f"{message}"
            )

        return response

    async def exchange_code_for_token(
        self,
        code: str,
    ) -> str:
        if (
            not settings.GITHUB_CLIENT_ID
            or not settings.GITHUB_CLIENT_SECRET
        ):
            raise GitHubAPIError(
                "GitHub OAuth is not configured."
            )

        async with httpx.AsyncClient(
            timeout=30.0
        ) as client:
            response = await client.post(
                (
                    "https://github.com/login/"
                    "oauth/access_token"
                ),
                headers={
                    "Accept": "application/json",
                    "User-Agent": (
                        "RepoSage-AI"
                    ),
                },
                data={
                    "client_id": (
                        settings.GITHUB_CLIENT_ID
                    ),
                    "client_secret": (
                        settings.GITHUB_CLIENT_SECRET
                    ),
                    "code": code,
                    "redirect_uri": (
                        settings
                        .GITHUB_OAUTH_CALLBACK_URL
                    ),
                },
            )

        payload = response.json()

        token = payload.get(
            "access_token"
        )

        if not token:
            raise GitHubAPIError(
                payload.get(
                    "error_description"
                )
                or payload.get("error")
                or "GitHub OAuth failed."
            )

        return token

    async def get_authenticated_user(
        self,
    ) -> Dict[str, Any]:
        response = await self._request(
            "GET",
            f"{GITHUB_API_URL}/user",
        )

        return response.json()

    async def get_primary_verified_email(
        self,
    ) -> Optional[str]:
        response = await self._request(
            "GET",
            f"{GITHUB_API_URL}/user/emails",
        )

        emails = response.json()

        primary = next(
            (
                item.get("email")
                for item in emails
                if item.get("primary")
                and item.get("verified")
            ),
            None,
        )

        if primary:
            return primary

        return next(
            (
                item.get("email")
                for item in emails
                if item.get("verified")
            ),
            None,
        )

    async def list_user_repos(
        self,
    ) -> List[Dict[str, Any]]:
        response = await self._request(
            "GET",
            f"{GITHUB_API_URL}/user/repos",
            params={
                "per_page": 100,
                "sort": "updated",
                "affiliation": (
                    "owner,collaborator,"
                    "organization_member"
                ),
            },
        )

        return response.json()

    async def get_repository(
        self,
        owner: str,
        repository: str,
    ) -> Dict[str, Any]:
        response = await self._request(
            "GET",
            self._repo_url(
                owner,
                repository,
            ),
        )

        return response.json()

    async def get_branch(
        self,
        owner: str,
        repository: str,
        branch: str,
    ) -> Dict[str, Any]:
        response = await self._request(
            "GET",
            (
                f"{self._repo_url(owner, repository)}"
                f"/branches/{quote(branch, safe='')}"
            ),
        )

        return response.json()

    async def branch_exists(
        self,
        owner: str,
        repository: str,
        branch: str,
    ) -> bool:
        url = (
            f"{self._repo_url(owner, repository)}"
            f"/branches/{quote(branch, safe='')}"
        )

        async with httpx.AsyncClient(
            timeout=30.0
        ) as client:
            response = await client.get(
                url,
                headers=self._headers(),
            )

        if response.status_code == 404:
            return False

        if response.is_error:
            raise GitHubAPIError(
                f"Could not check branch: "
                f"{response.text}"
            )

        return True

    async def create_branch(
        self,
        owner: str,
        repository: str,
        branch: str,
        from_branch: str,
    ) -> Dict[str, Any]:
        base = await self.get_branch(
            owner,
            repository,
            from_branch,
        )

        commit_sha = (
            base.get("commit", {})
            .get("sha")
        )

        if not commit_sha:
            raise GitHubAPIError(
                "Could not determine the base "
                "branch commit."
            )

        response = await self._request(
            "POST",
            (
                f"{self._repo_url(owner, repository)}"
                "/git/refs"
            ),
            json={
                "ref": f"refs/heads/{branch}",
                "sha": commit_sha,
            },
        )

        return response.json()

    async def get_file(
        self,
        owner: str,
        repository: str,
        path: str,
        ref: str,
    ) -> Dict[str, Any]:
        encoded_path = quote(
            path.replace("\\", "/"),
            safe="/",
        )

        response = await self._request(
            "GET",
            (
                f"{self._repo_url(owner, repository)}"
                f"/contents/{encoded_path}"
            ),
            params={
                "ref": ref,
            },
        )

        return response.json()

    async def update_file(
        self,
        owner: str,
        repository: str,
        path: str,
        branch: str,
        content: str,
        message: str,
    ) -> Dict[str, Any]:
        existing = await self.get_file(
            owner,
            repository,
            path,
            branch,
        )

        current_sha = existing.get(
            "sha"
        )

        if not current_sha:
            raise GitHubAPIError(
                f"Could not find the current SHA "
                f"for '{path}'."
            )

        encoded_content = base64.b64encode(
            content.encode("utf-8")
        ).decode("ascii")

        encoded_path = quote(
            path.replace("\\", "/"),
            safe="/",
        )

        response = await self._request(
            "PUT",
            (
                f"{self._repo_url(owner, repository)}"
                f"/contents/{encoded_path}"
            ),
            json={
                "message": message,
                "content": encoded_content,
                "sha": current_sha,
                "branch": branch,
            },
        )

        return response.json()

    async def create_pull_request(
        self,
        owner: str,
        repo: str,
        title: str,
        head: str,
        base: str,
        body: str,
        draft: bool = True,
    ) -> Dict[str, Any]:
        response = await self._request(
            "POST",
            (
                f"{self._repo_url(owner, repo)}"
                "/pulls"
            ),
            json={
                "title": title,
                "head": head,
                "base": base,
                "body": body,
                "draft": draft,
            },
        )

        return response.json()

    @staticmethod
    def _repo_url(
        owner: str,
        repository: str,
    ) -> str:
        return (
            f"{GITHUB_API_URL}/repos/"
            f"{quote(owner)}/"
            f"{quote(repository)}"
        )