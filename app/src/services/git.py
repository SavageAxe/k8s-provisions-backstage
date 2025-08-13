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


    async def compare_values(self, region, namespace, name, values):
        path = f'/{region}/{namespace}/{name}.yaml'
        enc_git_values = self.api.get_file(path)["content"]
        git_values = base64.b64decode(enc_git_values).decode("utf-8")
        return git_values == values