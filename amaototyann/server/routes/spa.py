"""SPA 配信ルーター."""

import logging
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import FileResponse, HTMLResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["spa"])

_FRONTEND_DIR = Path(__file__).resolve().parent.parent.parent.parent / "frontend" / "dist"


@router.get("/admin/{path:path}", response_class=HTMLResponse, response_model=None)
async def serve_spa(request: Request, path: str = "") -> FileResponse | HTMLResponse:
    """SPA のエントリーポイントまたは静的ファイルを返す."""
    # Try to serve static file first (e.g., /admin/assets/xxx.js)
    file_path = _FRONTEND_DIR / path
    if path and file_path.is_file():
        return FileResponse(file_path)

    # Serve index.html for all other /admin/* paths (SPA routing)
    index_path = _FRONTEND_DIR / "index.html"
    if index_path.is_file():
        return FileResponse(index_path)

    return HTMLResponse(
        content="<h1>Frontend not built</h1><p>Run: cd frontend && npm run build</p>",
        status_code=503,
    )
