"""LINE + Discord 統合サーバー (FastAPI)."""
import os
import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse

from amaototyann.src import logger, db_bot, db_group
from amaototyann.src.platforms.line.webhook_handler import (
    react_message_webhook, react_join_webhook, react_leave_webhook,
)
from amaototyann.src.platforms.line.client import LineCommands
from amaototyann.src.core.gas_client import gas_request


# === バックグラウンドタスク ===

async def backup_loop():
    """定期的に DB を GAS にバックアップするループ."""
    while True:
        try:
            res_group, code_group = db_group.backup_to_gas()
            res_bot, code_bot = db_bot.backup_to_gas()
            logger.info(
                "Backup: group=%s(%d) bot=%s(%d)",
                res_group, code_group, res_bot, code_bot,
            )
        except Exception as e:
            logger.error("Backup error: %s", e)
        await asyncio.sleep(60 * 3)


# === Lifespan ===

@asynccontextmanager
async def lifespan(app: FastAPI):
    """アプリケーションのライフサイクル管理."""
    # Startup
    tasks = []

    # Discord client の起動
    discord_token = os.getenv("DISCORD_BOT_TOKEN")
    if discord_token:
        from amaototyann.src.platforms.discord.client import client as discord_client
        task = asyncio.create_task(discord_client.start(discord_token))
        tasks.append(task)
        logger.info("Discord client starting...")
    else:
        logger.warning("DISCORD_BOT_TOKEN is not set. Discord bot will not start.")

    # バックアップループの起動
    backup_task = asyncio.create_task(backup_loop())
    tasks.append(backup_task)
    logger.info("Backup loop started.")

    yield

    # Shutdown
    if discord_token:
        from amaototyann.src.platforms.discord.client import client as discord_client
        if not discord_client.is_closed():
            await discord_client.close()
            logger.info("Discord client closed.")

    for task in tasks:
        task.cancel()


app = FastAPI(lifespan=lifespan)


# === LINE Webhook エンドポイント ===

@app.post("/lineWebhook/{bot_id}")
async def line_webhook(bot_id: int, request: Request):
    """LINE の Webhook を受け取るエンドポイント."""
    logger.info("got LINE webhook for bot %d", bot_id)
    body = await request.json()
    events = body.get("events", [])

    for i, event in enumerate(events):
        if event["type"] == "message" and event["message"]["type"] == "text":
            await react_message_webhook(body, bot_id, i)
        elif event["type"] == "join":
            await react_join_webhook(body, bot_id, i)
        elif event["type"] == "leave":
            await react_leave_webhook(body, bot_id, i)
        else:
            logger.info("not needed to react to this webhook")

    return {"status": "finish"}


# === Push Message エンドポイント ===

@app.post("/pushMessage")
async def push_message(request: Request):
    """外部からコマンドを実行するエンドポイント (LINE / Discord 両対応)."""
    request_json = await request.json()
    cmd = request_json.get("cmd")
    if cmd is None:
        logger.error("No cmd in request")
        return PlainTextResponse("error", status_code=400)

    platform = request_json.get("platform", "line")

    if platform == "discord":
        from amaototyann.src.platforms.discord.client import client as discord_client
        from amaototyann.src.platforms.discord.commands import DiscordCommands
        cmd_name = cmd.lstrip("!")
        matched = [c for c in DiscordCommands.registry if c.text == cmd_name]
        if not matched:
            logger.error("Discord command not found: %s", cmd_name)
            return PlainTextResponse("error", status_code=400)
        discord_cmd = DiscordCommands(bot=discord_client, broadcast_webhook_msg=True)
        await matched[0].process(discord_cmd)
        return PlainTextResponse("finish")
    else:
        # LINE push message
        use_account = [a for a in db_bot.list_rows() if a.get("in_group") is True]
        if not use_account:
            return PlainTextResponse("error: no active bot", status_code=400)
        account = use_account[0]
        target_group_id = db_group.group_id()
        line_cmd = LineCommands(
            channel_access_token=account["channel_access_token"],
            target_group_id=target_group_id,
        )
        result = await line_cmd.process(cmd)
        if result:
            return PlainTextResponse("finish")
        else:
            return PlainTextResponse("error", status_code=400)


# === バックアップエンドポイント ===

@app.get("/backupDatabase")
async def backup_database():
    """データベースを GAS にバックアップするエンドポイント."""
    res_group, code_group = db_group.backup_to_gas()
    res_bot, code_bot = db_bot.backup_to_gas()
    message = f"group info: {res_group} - {code_group}    bot info: {res_bot} - {code_bot}"
    code = 200 if code_group == 200 and code_bot == 200 else 500
    logger.info("%s-%d", message, code)
    return PlainTextResponse(message, status_code=code)


# === ヘルスチェック ===

@app.get("/health")
async def health():
    """ヘルスチェックエンドポイント."""
    discord_status = "not configured"
    discord_token = os.getenv("DISCORD_BOT_TOKEN")
    if discord_token:
        try:
            from amaototyann.src.platforms.discord.client import client as discord_client
            discord_status = "connected" if discord_client.is_ready() else "disconnected"
        except Exception:
            discord_status = "error"
    return {
        "status": "ok",
        "discord": discord_status,
    }


# === ログ表示 ===

@app.get("/")
async def root():
    """app.log を返すエンドポイント."""
    log_path = Path(__file__).parent.parent / "logs" / "app.log"
    if log_path.exists():
        return PlainTextResponse(log_path.read_text(encoding="utf-8"))
    return PlainTextResponse("No logs available")
