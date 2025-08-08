from .provision import ProvisionRouter

def get_provision_router(app):
    return ProvisionRouter(app).router