"""LINE Webhook ルーター."""

import logging

from fastapi import APIRouter, HTTPException, Request

from amaototyann.platforms.line.webhook_handler import handle_line_webhook

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/lineWebhook/{bot_id}")
@router.post("/lineWebhook/{bot_id}/")
async def line_webhook(bot_id: int, request: Request):
    """LINE の Webhook を受け取るエンドポイント.

    末尾スラッシュあり・なし両方を受け付ける
    (redirect_slashes=False のため両パスを明示登録)。
    """
    logger.info("Received LINE webhook for bot %d", bot_id)
    try:
        bot_store = request.app.state.bot_store
        group_store = request.app.state.group_store
        return await handle_line_webhook(request, bot_id, bot_store, group_store)
    except HTTPException:
        raise
    except KeyError as err:
        raise HTTPException(status_code=404, detail=f"Bot not found: {bot_id}") from err
    except Exception as err:
        logger.exception("LINE webhook error")
        raise HTTPException(status_code=500, detail="Internal server error") from err
