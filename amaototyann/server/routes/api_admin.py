"""管理 API ルーター (Web 管理画面用)."""

import hashlib
import hmac
import logging
import secrets
from typing import Any

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request
from fastapi.responses import JSONResponse

from amaototyann.config import get_settings
from amaototyann.core.commands import (
    add_practice,
    add_reminder,
    delete_event,
    finish_event,
    get_all_reminders,
)
from amaototyann.models.bot import BotInfo
from amaototyann.models.schedule import PracticeCreate, ReminderCreate
from amaototyann.models.settings import PracticeDefault

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin")

_SESSION_COOKIE = "session_token"
_SESSION_SECRET = b"amaototyann-session-v1"


def _derive_session_token(password: str) -> str:
    """パスワードから HMAC ベースのセッショントークンを導出する."""
    return hmac.new(_SESSION_SECRET, password.encode(), hashlib.sha256).hexdigest()


def _require_sheets_client(request: Request):
    """sheets_client が初期化済みであることを確認し、未初期化なら 503 を返す."""
    client = request.app.state.sheets_client
    if client is None:
        raise HTTPException(status_code=503, detail="SheetsClient not initialized")
    return client


def _result_to_json(result, *, status_code: int = 200, log_prefix: str = "") -> JSONResponse:
    """CommandResult をチェックし、エラーなら HTTPException を送出、成功なら JSONResponse を返す."""
    if result.error:
        if log_prefix:
            logger.error("%s error: %s", log_prefix, result.error)
        raise HTTPException(status_code=500, detail=result.error)
    return JSONResponse({"ok": True, "message": result.text}, status_code=status_code)


# ---------------------------------------------------------------------------
# 認証ヘルパー
# ---------------------------------------------------------------------------


async def require_admin(
    session_token: str | None = Cookie(default=None, alias=_SESSION_COOKIE),
) -> None:
    """管理者権限を検証する依存関係.

    settings.admin_password が None の場合はデバッグモードとして全アクセスを許可する。
    それ以外は Cookie の session_token を secrets.compare_digest で比較する。
    """
    settings = get_settings()
    if settings.admin_password is None:
        logger.debug("admin_password not configured — allowing access (debug mode)")
        return

    expected = _derive_session_token(settings.admin_password)
    if session_token is None or not secrets.compare_digest(session_token, expected):
        raise HTTPException(status_code=401, detail="Unauthorized")


# 認証依存関係をまとめたリスト (各エンドポイントの dependencies に渡す)
_AUTH = [Depends(require_admin)]


# ---------------------------------------------------------------------------
# 認証エンドポイント (認証不要)
# ---------------------------------------------------------------------------


@router.post("/login")
async def login(body: dict[str, Any]) -> JSONResponse:
    """ログインエンドポイント.

    JSON {"token": "..."} を受け取り、settings.admin_password と比較する。
    一致した場合は HttpOnly Cookie を発行する。
    admin_password が未設定の場合はデバッグモードとして常に成功する。
    """
    settings = get_settings()
    token: str = body.get("token", "")

    if settings.admin_password is None:
        logger.debug("admin_password not configured — login always succeeds (debug mode)")
        cookie_value = "debug"
    elif not token or not secrets.compare_digest(token, settings.admin_password):
        logger.warning("Login failed: invalid token")
        raise HTTPException(status_code=401, detail="Invalid token")
    else:
        cookie_value = _derive_session_token(settings.admin_password)

    logger.info("Admin login successful")
    response = JSONResponse({"ok": True})
    response.set_cookie(
        key=_SESSION_COOKIE,
        value=cookie_value,
        httponly=True,
        samesite="lax",
        max_age=86400,  # 24 hours
    )
    return response


@router.post("/logout")
async def logout() -> JSONResponse:
    """ログアウトエンドポイント.

    session_token Cookie を削除して返す。
    """
    response = JSONResponse({"ok": True})
    response.delete_cookie(key=_SESSION_COOKIE)
    logger.info("Admin logout")
    return response


# ---------------------------------------------------------------------------
# 認証確認エンドポイント
# ---------------------------------------------------------------------------


@router.get("/me", dependencies=_AUTH)
async def me() -> dict[str, bool]:
    """認証状態確認エンドポイント.

    フロントエンドが認証済みかどうかを確認するために使用する。
    require_admin 依存関係が通れば {"authenticated": true} を返す。
    """
    return {"authenticated": True}


# ---------------------------------------------------------------------------
# 練習予定エンドポイント
# ---------------------------------------------------------------------------


@router.get("/practice", dependencies=_AUTH)
async def get_practice(request: Request) -> JSONResponse:
    """練習予定一覧を取得する.

    Google Sheets から生の練習予定データをリストとして返す。
    """
    sheets_client = _require_sheets_client(request)
    try:
        events = await sheets_client.get_practice_events()
        return JSONResponse(events)
    except Exception as err:
        logger.exception("get_practice error")
        raise HTTPException(status_code=500, detail="Internal server error") from err


@router.post("/practice", status_code=201, dependencies=_AUTH)
async def post_practice(request: Request, body: PracticeCreate) -> JSONResponse:
    """練習予定を追加する."""
    result = await add_practice(
        request.app.state.sheets_client,
        date=body.date,
        place=body.place,
        start_time=body.start_time,
        end_time=body.end_time,
        memo=body.memo,
    )
    return _result_to_json(result, status_code=201, log_prefix="add_practice")


@router.delete("/practice/{event_id}", dependencies=_AUTH)
async def delete_practice(request: Request, event_id: str) -> JSONResponse:
    """練習予定を削除する."""
    result = await delete_event(request.app.state.sheets_client, event_id)
    return _result_to_json(result, log_prefix="delete_practice")


# ---------------------------------------------------------------------------
# リマインダーエンドポイント
# ---------------------------------------------------------------------------


@router.get("/reminder", dependencies=_AUTH)
async def get_reminder(request: Request) -> JSONResponse:
    """全リマインダーを取得する (フィルタなし)."""
    result = await get_all_reminders(request.app.state.sheets_client)
    if result.error:
        logger.error("get_all_reminders error: %s", result.error)
        raise HTTPException(status_code=500, detail=result.error)
    return JSONResponse(result.events or [])


@router.post("/reminder", status_code=201, dependencies=_AUTH)
async def post_reminder(request: Request, body: ReminderCreate) -> JSONResponse:
    """リマインダーを追加する."""
    result = await add_reminder(
        request.app.state.sheets_client,
        deadline=body.deadline,
        role=body.role,
        task=body.task,
        person=body.person,
        memo=body.memo,
        remind_date=body.remind_date,
    )
    return _result_to_json(result, status_code=201, log_prefix="add_reminder")


@router.post("/reminder/{event_id}/finish", dependencies=_AUTH)
async def finish_reminder(request: Request, event_id: str) -> JSONResponse:
    """リマインダーを完了済みにする."""
    result = await finish_event(request.app.state.sheets_client, event_id)
    return _result_to_json(result, log_prefix="finish_event")


@router.delete("/reminder/{event_id}", dependencies=_AUTH)
async def delete_reminder(request: Request, event_id: str) -> JSONResponse:
    """リマインダーを削除する."""
    result = await delete_event(request.app.state.sheets_client, event_id)
    return _result_to_json(result, log_prefix="delete_reminder")


# ---------------------------------------------------------------------------
# Bot 設定エンドポイント
# ---------------------------------------------------------------------------


@router.get("/bots", dependencies=_AUTH)
async def get_bots(request: Request) -> JSONResponse:
    """全 Bot 情報を取得する."""
    bots = await request.app.state.bot_store.list_all()
    return JSONResponse([bot.model_dump() for bot in bots])


@router.put("/bots", dependencies=_AUTH)
async def put_bots(request: Request, body: list[dict[str, Any]]) -> JSONResponse:
    """Bot 情報を更新し、Google Sheets と bot_store を同期する."""
    try:
        sheets_client = _require_sheets_client(request)
        bot_store = request.app.state.bot_store

        if not await sheets_client.set_bot_info(body):
            raise HTTPException(status_code=500, detail="Failed to update bot info in Sheets")

        # Sheets から最新情報を再取得して bot_store をリロード
        new_bot_data = await sheets_client.get_bot_info()
        if new_bot_data:
            new_bots = [
                BotInfo(
                    id=int(row[0]),
                    bot_name=row[1],
                    channel_access_token=row[2],
                    channel_secret=row[3],
                    gpt_webhook_url=row[4] or None,
                    in_group=row[5].upper() == "TRUE",
                )
                for row in new_bot_data
            ]
            await bot_store.load(new_bots)
            logger.info("bot_store reloaded with %d bots", len(new_bots))
        else:
            logger.warning("get_bot_info returned empty after set_bot_info")

        return JSONResponse({"ok": True})
    except HTTPException:
        raise
    except Exception as err:
        logger.exception("put_bots error")
        raise HTTPException(status_code=500, detail="Internal server error") from err


# ---------------------------------------------------------------------------
# グループ設定エンドポイント
# ---------------------------------------------------------------------------


@router.get("/group", dependencies=_AUTH)
async def get_group(request: Request) -> JSONResponse:
    """グループ情報を取得する."""
    try:
        info = await request.app.state.group_store.get()
        return JSONResponse(info.model_dump())
    except ValueError as e:
        logger.error("get_group error: %s", e)
        raise HTTPException(status_code=500, detail="Group info not initialized") from e


@router.put("/group", dependencies=_AUTH)
async def put_group(request: Request, body: dict[str, str]) -> JSONResponse:
    """グループ情報を更新し、Google Sheets と group_store を同期する."""
    group_id = body.get("id", "")
    group_name = body.get("groupName", "")

    if not group_id or not group_name:
        raise HTTPException(status_code=422, detail="id and groupName are required")

    try:
        sheets_client = _require_sheets_client(request)
        group_store = request.app.state.group_store

        if not await sheets_client.set_group_info(body):
            raise HTTPException(status_code=500, detail="Failed to update group info in Sheets")

        await group_store.set_group_info(group_id=group_id, group_name=group_name)
        logger.info("group_store updated: %s (%s)", group_name, group_id)

        return JSONResponse({"ok": True})
    except HTTPException:
        raise
    except Exception as err:
        logger.exception("put_group error")
        raise HTTPException(status_code=500, detail="Internal server error") from err


# ---------------------------------------------------------------------------
# 設定エンドポイント
# ---------------------------------------------------------------------------


@router.get("/settings/members", dependencies=_AUTH)
async def get_members(request: Request) -> JSONResponse:
    """メンバー一覧を取得する."""
    members = await request.app.state.settings_store.get_members()
    return JSONResponse(members)


@router.put("/settings/members", dependencies=_AUTH)
async def update_members(request: Request, body: dict[str, Any]) -> JSONResponse:
    """メンバー一覧を更新し、Google Sheets と settings_store を同期する."""
    names = body.get("members", [])
    sheets_client = _require_sheets_client(request)
    if not await sheets_client.set_members(names):
        raise HTTPException(status_code=500, detail="Failed to update members")
    await request.app.state.settings_store.set_members(names)
    return JSONResponse({"ok": True})


@router.get("/settings/practice-defaults", dependencies=_AUTH)
async def get_practice_defaults(request: Request) -> JSONResponse:
    """練習デフォルト設定を取得する."""
    defaults = await request.app.state.settings_store.get_practice_defaults()
    return JSONResponse([d.model_dump() for d in defaults])


@router.put("/settings/practice-defaults", dependencies=_AUTH)
async def update_practice_defaults(request: Request, body: dict[str, Any]) -> JSONResponse:
    """練習デフォルト設定を更新し、Google Sheets と settings_store を同期する."""
    defaults_data = body.get("defaults", [])
    sheets_client = _require_sheets_client(request)
    if not await sheets_client.set_practice_defaults(defaults_data):
        raise HTTPException(status_code=500, detail="Failed to update practice defaults")
    practice_defaults = [PracticeDefault(**d) for d in defaults_data]
    await request.app.state.settings_store.set_practice_defaults(practice_defaults)
    return JSONResponse({"ok": True})


@router.get("/settings/app", dependencies=_AUTH)
async def get_app_settings(request: Request) -> JSONResponse:
    """アプリ設定を取得する."""
    app_settings = await request.app.state.settings_store.get_all_settings()
    return JSONResponse(app_settings)


@router.put("/settings/app", dependencies=_AUTH)
async def update_app_settings(request: Request, body: dict[str, Any]) -> JSONResponse:
    """アプリ設定を更新し、Google Sheets と settings_store を同期する."""
    sheets_client = _require_sheets_client(request)
    for key, value in body.items():
        if not await sheets_client.set_app_setting(key, str(value)):
            raise HTTPException(status_code=500, detail=f"Failed to update setting: {key}")
        await request.app.state.settings_store.set_setting(key, str(value))
    return JSONResponse({"ok": True})
