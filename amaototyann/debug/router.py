"""デバッグ用 FastAPI ルーター (Flask 廃止)."""

import json
import logging
from pathlib import Path

import httpx
from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from amaototyann.config import get_settings
from amaototyann.server.lifespan import bot_store, group_store

logger = logging.getLogger(__name__)

_BASE_DIR = Path(__file__).parent
_TEMPLATES_DIR = _BASE_DIR / "templates"
_WEBHOOK_TEMPLATES_DIR = _BASE_DIR / "webhook_templates"

router = APIRouter()
templates = Jinja2Templates(directory=str(_TEMPLATES_DIR))


def _get_template_files() -> list[str]:
    """利用可能な Webhook テンプレートファイルを取得する."""
    return [f.name for f in _WEBHOOK_TEMPLATES_DIR.iterdir() if f.suffix == ".json"]


async def _fetch_database_data() -> list[list]:
    """Bot 情報を取得する."""
    try:
        bots = await bot_store.list_all()
        return [[b.id, b.bot_name, b.in_group] for b in bots]
    except Exception as e:
        logger.error("Failed to fetch database data: %s", e)
        return []


@router.get("/", response_class=HTMLResponse)
async def debug_index(request: Request):
    """デバッグ UI のメインページ."""
    database_data = await _fetch_database_data()
    template_files = _get_template_files()
    return templates.TemplateResponse(
        "webhook_sender.html",
        {
            "request": request,
            "response": None,
            "templates": template_files,
            "editable_fields": {},
            "database_data": database_data,
            "bot_ids": [{"id": row[0], "name": row[1]} for row in database_data],
            "request_form": {},
        },
    )


@router.post("/", response_class=HTMLResponse)
async def debug_send_webhook(
    request: Request,
    template: str = Form(...),
    botId: str = Form("1"),
):
    """Webhook テンプレートを送信する."""
    form = await request.form()
    response_data = None
    editable_fields = {}
    webhook_template = {}

    template_files = _get_template_files()
    database_data = await _fetch_database_data()

    # テンプレート読み込み
    template_path = _WEBHOOK_TEMPLATES_DIR / template
    if template_path.exists():
        try:
            webhook_template = json.loads(template_path.read_text(encoding="utf-8"))
            webhook_template["debug"] = True

            if template == "message.json":
                editable_fields = {"message.text": webhook_template["events"][0]["message"]["text"]}
                if "message.text" in form:
                    webhook_template["events"][0]["message"]["text"] = form["message.text"]

            elif template == "join.json":
                try:
                    group_id = await group_store.get_group_id()
                    webhook_template["events"][0]["source"]["groupId"] = group_id
                except Exception:
                    pass

        except Exception as e:
            response_data = {"error": f"Failed to load template: {e}"}

    # Webhook 送信
    if webhook_template and response_data is None:
        try:
            settings = get_settings()
            server_url = settings.server_url
            if not server_url:
                raise ValueError("SERVER_URL is not set")

            url = f"{server_url.rstrip('/')}/lineWebhook/{botId}/"
            async with httpx.AsyncClient(timeout=60) as client:
                res = await client.post(url, json=webhook_template)
            response_data = {
                "status_code": res.status_code,
                "response_body": res.json() if "application/json" in res.headers.get("content-type", "") else res.text,
            }
            database_data = await _fetch_database_data()
        except Exception as e:
            response_data = {"error": f"An error occurred: {e}"}

    return templates.TemplateResponse(
        "webhook_sender.html",
        {
            "request": request,
            "response": response_data,
            "templates": template_files,
            "editable_fields": editable_fields,
            "database_data": database_data,
            "bot_ids": [{"id": row[0], "name": row[1]} for row in database_data],
            "request_form": dict(form),
        },
    )


@router.post("/update_template", response_class=HTMLResponse)
async def update_template(request: Request):
    """テンプレート選択時の動的更新."""
    form = await request.form()
    selected_template = form.get("template", "")
    editable_fields = {}
    database_data = await _fetch_database_data()

    if selected_template:
        template_path = _WEBHOOK_TEMPLATES_DIR / selected_template
        if template_path.exists():
            try:
                webhook_template = json.loads(template_path.read_text(encoding="utf-8"))
                if selected_template == "message.json":
                    editable_fields = {"message.text": webhook_template["events"][0]["message"]["text"]}
            except Exception as e:
                return HTMLResponse(f"<p>Error loading template: {e}</p>")

    return templates.TemplateResponse(
        "update_template.html",
        {
            "request": request,
            "templates": _get_template_files(),
            "editable_fields": editable_fields,
            "bot_ids": [{"id": row[0], "name": row[1]} for row in database_data],
            "request_form": dict(form),
        },
    )
