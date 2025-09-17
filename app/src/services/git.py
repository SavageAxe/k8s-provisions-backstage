import base64
from app.src.api.git import GitAPI
from . import retry


class Git:
    def __init__(self, base_url, token):
        self.api = GitAPI(base_url, token)
        self.last_commit = None


    async def async_init(self):
        last_commit = await self.api.get_last_commit()
        self.last_commit = last_commit["sha"]

    async def modify_file(self, path, commit_message, content):
        await retry(lambda: self.api.modify_file_content(path, commit_message, content))


    async def add_file(self, path, commit_message, content):
        await retry(lambda: self.api.create_new_file(path, commit_message, content))


    async def delete_file(self, path, commit_message):
        await retry(lambda: self.api.delete_file(path, commit_message))


    async def get_file_content(self, path):
        resp = await retry(lambda: self.api.get_file(path))
        enc_git_file = resp["content"]
        git_file = base64.b64decode(enc_git_file).decode("utf-8")
        return git_file


    async def get_changed_files(self, path, since, until):
        commits = await self.api.commits_per_path(path, since, until)

        if not commits:
            return []

        commits = sorted(commits, key=lambda c: c["commit"]["author"]["date"])

        head = commits[-1]["sha"]

        diff = await self.api.compare_commits(self.last_commit, head)

        self.last_commit = head

        return diff["files"]

    async def list_dir(self, path):
        response = await retry(lambda: self.api.list_dir(path))

        files = []
        for file in response:
            files.append((file["name"], file["path"]))

        return files
