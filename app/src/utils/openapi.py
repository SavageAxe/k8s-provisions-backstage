from fastapi.openapi.utils import get_openapi
from ...general.utils import basicSettings

def update_openapi_schema(app, title, description) -> None:
    app.openapi_schema = get_openapi(
        title=title,
        version=basicSettings.OPENAPI_VERSION,
        description=description,
        routes=app.routes,
    )

    return app
