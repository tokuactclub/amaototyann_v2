"""FastAPI App Factory."""

from fastapi import FastAPI

from amaototyann.config import get_settings
from amaototyann.server.lifespan import lifespan


def create_app() -> FastAPI:
    """FastAPI アプリケーションを作成する."""
    app = FastAPI(
        title="あまおとちゃん",
        version="3.0.0",
        lifespan=lifespan,
    )

    # ルーターの登録
    from amaototyann.server.routes.line import router as line_router
    from amaototyann.server.routes.push import router as push_router
    from amaototyann.server.routes.admin import router as admin_router

    app.include_router(line_router)
    app.include_router(push_router)
    app.include_router(admin_router)

    # デバッグルーターの条件付きマウント
    try:
        settings = get_settings()
        if settings.is_debug:
            from amaototyann.debug.router import router as debug_router
            app.include_router(debug_router, prefix="/debug")
    except Exception:
        pass

    return app


# uvicorn amaototyann.server.app:app で直接起動用
app = create_app()
