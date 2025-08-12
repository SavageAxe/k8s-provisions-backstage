from app.src.api.git import GitAPI


class Git:
    def __init__(self, base_url, token):
        self.api = GitAPI(base_url, token)


    async def modify_values(self, region, namespace, name, resource, values):
        path = f'/{region}/{namespace}/{name}.yaml'
        commit_message = f"Modify {name} {resource}'s values file on {region=} on {namespace=}"
        await self.api.modify_file_content(path, commit_message ,values)

