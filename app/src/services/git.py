import asyncio
import base64

from app.src.api.git import GitAPI, GitError


class Git:
    def __init__(self, base_url, token):
        self.api = GitAPI(base_url, token)


    async def modify_values(self, region, namespace, name, resource, values):
        path = f'/{region}/{namespace}/{name}.yaml'
        commit_message = f"Modify {name} {resource}'s values file on {region=} on {namespace=}"
        await self.api.modify_file_content(path, commit_message ,values)


    async def add_values(self, region, namespace, name, resource, values):
        path = f'/{region}/{namespace}/{name}.yaml'
        commit_message = f"Add {name} {resource}'s values file on {region=} on {namespace=}"
        await self.api.create_new_file(path, commit_message ,values)


    async def delete_values(self, region, namespace, name, resource):
        path = f'/{region}/{namespace}/{name}.yaml'
        commit_message = f"Delete {name} {resource}'s values file on {region=} on {namespace=}"
        await self.api.delete_file(path, commit_message)


    async def get_file_content(self, path):
        resp = await self.api.get_file(path)
        enc_git_file = resp["content"]
        git_file = base64.b64decode(enc_git_file).decode("utf-8")
        return git_file


    async def get_changed_files(self, path, since, until):
        commits = await self.api.commits_per_path(path, since, until)
        if not commits:
            return []

        changed_files = []

        for commit in commits:
            sha = commit['sha']
            commit = await self.api.get_commit(sha)
            for file in commit['files']:
                filename = file['filename']
                if filename.startswith(path.lstrip("/")) and filename not in changed_files:
                    changed_files.append(filename)

        return changed_files

    async def list_dir(self, path):
        response = await self.api.list_dir(path)

        files = []
        for file in response:
            files.append((file["name"], file["path"]))

        return files