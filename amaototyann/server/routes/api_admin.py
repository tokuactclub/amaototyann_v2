"""管理 API ルーター (Web 管理画面用)."""

import logging
import secrets
from typing import Any

from fastapi import APIRouter, Cookie, Depends, HTTPException
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
from amaototyann.server.lifespan import bot_store, group_store, sheets_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin")

_SESSION_COOKIE = "session_token"


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

    if session_token is None or not secrets.compare_digest(session_token, settings.admin_password):
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
    """
    settings = get_settings()
    token: str = body.get("token", "")

    if settings.admin_password is None:
        # デバッグモード: パスワード未設定時は常に成功
        logger.debug("admin_password not configured — login always succeeds (debug mode)")
        response = JSONResponse({"ok": True})
        response.set_cookie(
            key=_SESSION_COOKIE,
            value="debug",
            httponly=True,
            samesite="lax",
        )
        return response

    if not token or not secrets.compare_digest(token, settings.admin_password):
        logger.warning("Login failed: invalid token")
        raise HTTPException(status_code=401, detail="Invalid token")

    response = JSONResponse({"ok": True})
    response.set_cookie(
        key=_SESSION_COOKIE,
        value=settings.admin_password,
        httponly=True,
        samesite="lax",
    )
    logger.info("Admin login successful")
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
async def get_practice() -> JSONResponse:
    """練習予定一覧を取得する.

    Google Sheets から生の練習予定データをリストとして返す。
    """
    try:
        if sheets_client is None:
            raise HTTPException(status_code=503, detail="SheetsClient not initialized")
        events = await sheets_client.get_practice_events()
        return JSONResponse(events)
    except HTTPException:
        raise
    except Exception as err:
        logger.exception("get_practice error")
        raise HTTPException(status_code=500, detail="Internal server error") from err


@router.post("/practice", status_code=201, dependencies=_AUTH)
async def post_practice(body: PracticeCreate) -> JSONResponse:
    """練習予定を追加する."""
    result = await add_practice(
        date=body.date,
        place=body.place,
        start_time=body.start_time,
        end_time=body.end_time,
        memo=body.memo,
    )
    if result.error:
        logger.error("add_practice error: %s", result.error)
        raise HTTPException(status_code=500, detail=result.error)
    return JSONResponse({"ok": True, "message": result.text}, status_code=201)


@router.delete("/practice/{event_id}", dependencies=_AUTH)
async def delete_practice(event_id: str) -> JSONResponse:
    """練習予定を削除する."""
    result = await delete_event(event_id)
    if result.error:
        logger.error("delete_practice error: %s", result.error)
        raise HTTPException(status_code=500, detail=result.error)
    return JSONResponse({"ok": True, "message": result.text})


# ---------------------------------------------------------------------------
# リマインダーエンドポイント
# ---------------------------------------------------------------------------


@router.get("/reminder", dependencies=_AUTH)
async def get_reminder() -> JSONResponse:
    """全リマインダーを取得する (フィルタなし)."""
    result = await get_all_reminders()
    if result.error:
        logger.error("get_all_reminders error: %s", result.error)
        raise HTTPException(status_code=500, detail=result.error)
    events = result.events if result.events is not None else []
    return JSONResponse(events)


@router.post("/reminder", status_code=201, dependencies=_AUTH)
async def post_reminder(body: ReminderCreate) -> JSONResponse:
    """リマインダーを追加する."""
    result = await add_reminder(
        deadline=body.deadline,
        role=body.role,
        task=body.task,
        person=body.person,
        memo=body.memo,
        remind_date=body.remind_date,
    )
    if result.error:
        logger.error("add_reminder error: %s", result.error)
        raise HTTPException(status_code=500, detail=result.error)
    return JSONResponse({"ok": True, "message": result.text}, status_code=201)


@router.post("/reminder/{event_id}/finish", dependencies=_AUTH)
async def finish_reminder(event_id: str) -> JSONResponse:
    """リマインダーを完了済みにする."""
    result = await finish_event(event_id)
    if result.error:
        logger.error("finish_event error: %s", result.error)
        raise HTTPException(status_code=500, detail=result.error)
    return JSONResponse({"ok": True, "message": result.text})


@router.delete("/reminder/{event_id}", dependencies=_AUTH)
async def delete_reminder(event_id: str) -> JSONResponse:
    """リマインダーを削除する."""
    result = await delete_event(event_id)
    if result.error:
        logger.error("delete_reminder error: %s", result.error)
        raise HTTPException(status_code=500, detail=result.error)
    return JSONResponse({"ok": True, "message": result.text})


# ---------------------------------------------------------------------------
# Bot 設定エンドポイント
# ---------------------------------------------------------------------------


@router.get("/bots", dependencies=_AUTH)
async def get_bots() -> JSONResponse:
    """全 Bot 情報を取得する."""
    bots = await bot_store.list_all()
    return JSONResponse([bot.model_dump() for bot in bots])


@router.put("/bots", dependencies=_AUTH)
async def put_bots(body: list[dict[str, Any]]) -> JSONResponse:
    """Bot 情報を更新し、Google Sheets と bot_store を同期する."""
    try:
        if sheets_client is None:
            raise HTTPException(status_code=503, detail="SheetsClient not initialized")

        success = await sheets_client.set_bot_info(body)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to update bot info in Sheets")
        logger.info("set_bot_info Sheets response: success=%s", success)

        # Sheets から最新情報を再取得して bot_store をリロード
        new_bot_data = await sheets_client.get_bot_info()
        if new_bot_data:
            new_bots = [
                BotInfo(
                    id=int(row[0]),
                    bot_name=row[1],
                    channel_access_token=row[2],
                    channel_secret=row[3],
                    gpt_webhook_url=row[4],
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
async def get_group() -> JSONResponse:
    """グループ情報を取得する."""
    try:
        info = await group_store.get()
        return JSONResponse(info.model_dump())
    except ValueError as e:
        logger.error("get_group error: %s", e)
        raise HTTPException(status_code=500, detail="Group info not initialized") from e


@router.put("/group", dependencies=_AUTH)
async def put_group(body: dict[str, str]) -> JSONResponse:
    """グループ情報を更新し、Google Sheets と group_store を同期する."""
    group_id = body.get("id", "")
    group_name = body.get("groupName", "")

    if not group_id or not group_name:
        raise HTTPException(status_code=422, detail="id and groupName are required")

    try:
        if sheets_client is None:
            raise HTTPException(status_code=503, detail="SheetsClient not initialized")

        success = await sheets_client.set_group_info(body)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to update group info in Sheets")
        logger.info("set_group_info Sheets response: success=%s", success)

        await group_store.set_group_info(group_id=group_id, group_name=group_name)
        logger.info("group_store updated: %s (%s)", group_name, group_id)

        return JSONResponse({"ok": True})
    except HTTPException:
        raise
    except Exception as err:
        logger.exception("put_group error")
        raise HTTPException(status_code=500, detail="Internal server error") from err
