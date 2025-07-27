import os
import tempfile
import json
import shutil
import re
from app.src.utils.config import Config
from loguru import logger
from ..utils import resources_config

def is_version(string):
    return string.startswith('schema-') and string.endswith('.json') and re.fullmatch(r"\d+\.\d+\.\d+", string.split('-')[1].rstrip(".json"))

class SchemaLoader:
    def __init__(self):
        self.config = Config.get_instance()
        self.schemas = {}  # {resource: {version: schema_dict}}

    def load_all_schemas(self):
        # Find all resources by env var pattern *_SCHEMAS_REPO_URL
        for key, value in os.environ.items():
            if key.endswith('_SCHEMAS_REPO_URL') and value:
                resource = key[:-len('_SCHEMAS_REPO_URL')].lower()
                self._load_resource_schemas(resource)
        return self.schemas

    def _load_resource_schemas(self, resource):
        config = resources_config.get(resource, {})
        repo_url = config['SCHEMAS_REPO_URL']
        private_key_path = config['SCHEMAS_REPO_PRIVATE_KEY']
        if not repo_url or not private_key_path:
            logger.warning(f"Missing schema repo config for {resource}")
            return
        temp_dir = tempfile.mkdtemp()
        try:
            # Set up SSH key for git
            git_ssh_cmd = f'ssh -i ~/.ssh/new_key -o StrictHostKeyChecking=no'
            os.system(f"GIT_SSH_COMMAND='{git_ssh_cmd}' git clone -v -- {repo_url} {temp_dir}")
            # Look for schema files: schema-<version>.json or .yaml
            temp_dir = f"{temp_dir}/schemas"
            for fname in os.listdir(temp_dir):
                fpath = os.path.join(temp_dir, fname)
                if is_version(fname):
                    version = fname.split('-')[1].rstrip(".json")
                    with open(fpath, 'r') as f:
                        schema = json.load(f)
                    self.schemas.setdefault(resource, {})[version] = schema
                    logger.info(f"Loaded schema for {resource} version {version}")
                else:
                    with open(fpath, 'r') as f:
                        schema = json.load(f)
                    self.schemas[fname] = schema
                    logger.info(f"Loaded {fname}")
        except Exception as e:
            logger.error(f"Failed to load schemas for {resource}: {e}")
        finally:
            shutil.rmtree(temp_dir)

    def get_schema(self, resource, version):
        return self.schemas.get(resource, {}).get(version)


