from .provision import ProvisionRouter

def get_provision_router(schemas_cache):
    return ProvisionRouter(schemas_cache).router