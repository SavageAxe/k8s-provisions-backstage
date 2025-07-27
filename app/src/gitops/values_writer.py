import os
import tempfile
import git
import yaml
import shutil

class GitValuesWriter:
    def __init__(self, logger):
        self.logger = logger

    def write_and_commit(self, region, namespace, app_name, yaml_data, repo_url, private_key_path):
        rel_path = f"{region}/{namespace}/{app_name}.yaml"
        temp_dir = tempfile.mkdtemp()
        try:
            git_ssh_cmd = f'ssh -i ~/.ssh/new_key -o StrictHostKeyChecking=no'
            os.environ['GIT_SSH_COMMAND'] = git_ssh_cmd
            repo = git.Repo.clone_from(repo_url, temp_dir)
            file_path = os.path.join(temp_dir, rel_path)
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, 'w') as f:
                yaml.dump(yaml_data, f, default_flow_style=False)
            repo.git.add(rel_path)
            repo.index.commit(f"Provision {app_name} in {region}/{namespace}")
            origin = repo.remote(name="origin")
            origin.push()
            self.logger.info(f"Committed and pushed {rel_path} to {repo_url}")
            return rel_path
        except Exception as e:
            self.logger.error(f"Git write/commit failed: {e}")
            raise
        finally:
            shutil.rmtree(temp_dir) 