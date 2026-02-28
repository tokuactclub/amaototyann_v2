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
    from amaototyann.server.routes.admin import router as admin_router
    from amaototyann.server.routes.api_admin import router as api_admin_router
    from amaototyann.server.routes.line import router as line_router
    from amaototyann.server.routes.push import router as push_router

    app.include_router(line_router)
    app.include_router(push_router)
    app.include_router(admin_router)
    app.include_router(api_admin_router)

    # デバッグルーターの条件付きマウント
    try:
        settings = get_settings()
        if settings.is_debug:
            from amaototyann.debug.router import router as debug_router

            app.include_router(debug_router, prefix="/debug")
    except Exception:
        pass

    # SPA ルーターは最後に登録する(catch-all パターンが API ルートを奪わないように)
    from amaototyann.server.routes.spa import router as spa_router

    app.include_router(spa_router)

    return app


# uvicorn amaototyann.server.app:app で直接起動用
app = create_app()
