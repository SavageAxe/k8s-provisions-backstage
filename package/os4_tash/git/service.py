"""High level helpers wrapping the Git API client."""

from __future__ import annotations

import base64
from typing import Any, Dict, List, Optional

from loguru import logger

from .api import GitAPI

__all__ = ["Git", "logger"]


class Git:
    """High level wrapper around :class:`GitAPI`."""

    def __init__(self, base_url: str, token: str) -> None:
        self.api = GitAPI(base_url, token)
        self.last_commit: Optional[str] = None
        self.logger = logger

    @staticmethod
    def get_logger():
        """Return the shared loguru logger used by the service."""

        return logger

    async def async_init(self) -> None:
        last_commit = await self.api.get_last_commit()
        self.last_commit = last_commit["sha"]
        self.logger.debug("Initialised Git helper with last commit {}", self.last_commit)

    async def modify_file(self, path: str, commit_message: str, content: str) -> None:
        await self.api.modify_file_content(path, commit_message, content)

    async def add_file(self, path: str, commit_message: str, content: str) -> None:
        await self.api.create_new_file(path, commit_message, content)

    async def delete_file(self, path: str, commit_message: str) -> None:
        await self.api.delete_file(path, commit_message)

    async def get_file_content(self, path: str) -> str:
        resp = await self.api.get_file(path)
        enc_git_file = resp["content"]
        git_file = base64.b64decode(enc_git_file).decode("utf-8")
        return git_file

    async def get_changed_files(self, path: str, since: str, until: str) -> List[Dict[str, Any]]:
        commits = await self.api.commits_per_path(path, since, until)

        if not commits:
            self.logger.debug("No commits found for path {} between {} and {}", path, since, until)
            return []

        commits = sorted(commits, key=lambda c: c["commit"]["author"]["date"])

        head = commits[-1]["sha"]

        diff = await self.api.compare_commits(self.last_commit or head, head)

        self.last_commit = head

        files = diff.get("files", [])
        self.logger.debug("Git diff for path {} returned {} files", path, len(files))
        return files

    async def list_dir(self, path: str) -> List[tuple[str, str]]:
        response = await self.api.list_dir(path)

        files: List[tuple[str, str]] = []
        for file in response:
            name = file.get("name")
            file_path = file.get("path")
            if name and file_path:
                files.append((name, file_path))

        return files
