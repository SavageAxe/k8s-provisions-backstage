from .new_generator import RouterGenerator

def generate_router(app):
    return RouterGenerator(app).router