from .generator import RouterGenerator

def generate_router(app):
    return RouterGenerator(app).router