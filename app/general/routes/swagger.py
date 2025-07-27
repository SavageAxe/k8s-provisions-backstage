from fastapi import APIRouter
from fastapi.openapi.docs import (
    get_redoc_html,
    get_swagger_ui_html
)
from ..utils import basicSettings
router = APIRouter(include_in_schema=False)


@router.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html():
    return get_swagger_ui_html(
        title="Swagger UI",
        swagger_js_url=f"{basicSettings.SWAGGER_STATIC_FILES}/swagger-ui-bundle.js",
        swagger_css_url=f"{basicSettings.SWAGGER_STATIC_FILES}/swagger-ui.css",
        swagger_favicon_url=f"{basicSettings.SWAGGER_STATIC_FILES}/favicon.ico",
        openapi_url=basicSettings.SWAGGER_OPENAPI_JSON_URL
    )

@router.get("/redoc", include_in_schema=False)
async def redoc_html():
    return get_redoc_html(
        title="ReDoc",
        redoc_js_url=f"{basicSettings.SWAGGER_STATIC_FILES}/redoc.standalone.js",
        redoc_favicon_url=f"{basicSettings.SWAGGER_STATIC_FILES}/favicon.ico",
        openapi_url=basicSettings.SWAGGER_OPENAPI_JSON_URL
    )