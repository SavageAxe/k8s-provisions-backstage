from dotenv import load_dotenv
from .config import Config
import os

load_dotenv()
config = Config()

def load_resources_config():
    resources_config = {}
    for key, value in os.environ.items():
        if key.endswith('_VALUES_REPO_URL') and value:
            resource = key[:-len('_VALUES_REPO_URL')].lower()
            resources_config[resource] = config.get_resource_config(resource)
    return resources_config

resources_config = load_resources_config()