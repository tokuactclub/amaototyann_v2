"""サーバールートのテスト.

FastAPI のエンドポイントを httpx.AsyncClient + ASGITransport で直接テストする。
lifespan (Discord 起動 / GAS 通信) は null_lifespan で完全にバイパスし、
ストアやサービス層はモックで差し替える。
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

import httpx
import pytest
from fastapi import FastAPI

from amaototyann.models.bot import BotInfo, GroupInfo
from amaototyann.models.settings import PracticeDefault
from amaototyann.server.routes.admin import router as admin_router
from amaototyann.server.routes.api_admin import router as api_admin_router
from amaototyann.server.routes.line import router as line_router
from amaototyann.server.routes.push import router as push_router
from amaototyann.store.memory import BotStore, GroupStore
from amaototyann.store.settings import SettingsStore

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_bot(
    *,
    bot_id: int = 1,
    in_group: bool = True,
    channel_secret: str = "test_secret",
    channel_access_token: str = "test_token",
) -> BotInfo:
    return BotInfo(
        id=bot_id,
        bot_name="TestBot",
        channel_access_token=channel_access_token,
        channel_secret=channel_secret,
        gpt_webhook_url="https://example.com/gpt",
        in_group=in_group,
    )


def _make_group(group_id: str = "Cgroup123") -> GroupInfo:
    return GroupInfo(id=group_id, group_name="テストグループ")


def _sign_body(body: bytes, secret: str) -> str:
    """LINE HMAC-SHA256 署名を生成して Base64 エンコードで返す."""
    digest = hmac.new(secret.encode(), body, hashlib.sha256).digest()
    return base64.b64encode(digest).decode()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@asynccontextmanager
async def _null_lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """lifespan を何もしない空実装に差し替える."""
    yield


def _build_test_app(
    bot_store: BotStore,
    group_store: GroupStore,
    settings_store: SettingsStore | None = None,
    sheets_client=None,
) -> FastAPI:
    """テスト用 FastAPI アプリを組み立てる.

    * null_lifespan でサービス起動をスキップ
    * app.state にストアを注入してルーターが request.app.state 経由で読めるようにする
    """
    app = FastAPI(lifespan=_null_lifespan, redirect_slashes=False)
    app.include_router(admin_router)
    app.include_router(api_admin_router)
    app.include_router(push_router)
    app.include_router(line_router)
    # Set app.state for dependency injection
    app.state.bot_store = bot_store
    app.state.group_store = group_store
    app.state.settings_store = settings_store if settings_store is not None else SettingsStore()
    app.state.sheets_client = sheets_client
    return app


@pytest.fixture
async def stores() -> tuple[BotStore, GroupStore]:
    bot_store = BotStore()
    group_store = GroupStore()
    bot = _make_bot()
    group = _make_group()
    await bot_store.load([bot])
    await group_store.load(group)
    return bot_store, group_store


@pytest.fixture
def test_app(stores: tuple[BotStore, GroupStore]) -> FastAPI:
    bot_store, group_store = stores
    return _build_test_app(bot_store, group_store)


# ---------------------------------------------------------------------------
# /health
# ---------------------------------------------------------------------------


class TestHealthEndpoint:
    async def test_returns_200(self, test_app: FastAPI) -> None:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=test_app), base_url="http://test"
        ) as client:
            response = await client.get("/health")

        assert response.status_code == 200

    async def test_response_has_status_ok(self, test_app: FastAPI) -> None:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=test_app), base_url="http://test"
        ) as client:
            response = await client.get("/health")

        body = response.json()
        assert body["status"] == "ok"

    async def test_response_has_version(self, test_app: FastAPI) -> None:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=test_app), base_url="http://test"
        ) as client:
            response = await client.get("/health")

        body = response.json()
        assert "version" in body
        assert body["version"] == "3.0.0"

    async def test_response_has_discord_field(self, test_app: FastAPI) -> None:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=test_app), base_url="http://test"
        ) as client:
            response = await client.get("/health")

        body = response.json()
        assert "discord" in body

    async def test_discord_not_configured_when_no_token(self, test_app: FastAPI) -> None:
        """DISCORD_BOT_TOKEN が未設定なら 'not configured' を返す."""
        mock_settings = MagicMock()
        mock_settings.discord_bot_token = None

        with patch("amaototyann.server.routes.admin.get_settings", return_value=mock_settings):
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=test_app), base_url="http://test"
            ) as client:
                response = await client.get("/health")

        assert response.json()["discord"] == "not configured"


# ---------------------------------------------------------------------------
# /pushMessage
# ---------------------------------------------------------------------------


class TestPushMessageEndpoint:
    async def test_missing_cmd_returns_400(self, test_app: FastAPI) -> None:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=test_app), base_url="http://test"
        ) as client:
            response = await client.post("/pushMessage", json={})

        assert response.status_code == 400
        assert response.text == "error"

    async def test_line_push_no_active_bot_returns_400(self, test_app: FastAPI) -> None:
        """アクティブな Bot がいない場合は 400 を返す."""
        empty_bot_store = BotStore()
        group_store = GroupStore()
        app = _build_test_app(empty_bot_store, group_store)
        # No patches needed for stores
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/pushMessage", json={"cmd": "!practice", "platform": "line"}
            )

        assert response.status_code == 400

    async def test_line_push_valid_cmd_calls_handler(self, test_app: FastAPI) -> None:
        """有効なコマンドが LineCommandHandler.process に渡される."""
        mock_handler = AsyncMock()
        mock_handler.process = AsyncMock(return_value=True)

        with patch(
            "amaototyann.server.routes.push.LineCommandHandler",
            return_value=mock_handler,
        ):
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=test_app), base_url="http://test"
            ) as client:
                response = await client.post(
                    "/pushMessage", json={"cmd": "!practice", "platform": "line"}
                )

        assert response.status_code == 200
        assert response.text == "finish"
        mock_handler.process.assert_awaited_once_with("!practice")

    async def test_line_push_handler_returns_false_gives_400(self, test_app: FastAPI) -> None:
        """LineCommandHandler.process が False を返すと 400."""
        mock_handler = AsyncMock()
        mock_handler.process = AsyncMock(return_value=False)

        with patch(
            "amaototyann.server.routes.push.LineCommandHandler",
            return_value=mock_handler,
        ):
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=test_app), base_url="http://test"
            ) as client:
                response = await client.post(
                    "/pushMessage", json={"cmd": "!unknown", "platform": "line"}
                )

        assert response.status_code == 400

    async def test_discord_push_no_token_returns_400(self, test_app: FastAPI) -> None:
        mock_settings = MagicMock()
        mock_settings.discord_bot_token = None

        with patch("amaototyann.server.routes.push.get_settings", return_value=mock_settings):
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=test_app), base_url="http://test"
            ) as client:
                response = await client.post(
                    "/pushMessage", json={"cmd": "!practice", "platform": "discord"}
                )

        assert response.status_code == 400

    async def test_discord_push_unknown_cmd_returns_400(self, test_app: FastAPI) -> None:
        mock_settings = MagicMock()
        mock_settings.discord_bot_token = "dummy_token"

        mock_discord_client = MagicMock()

        with (
            patch("amaototyann.server.routes.push.get_settings", return_value=mock_settings),
            patch(
                "amaototyann.platforms.discord.bot.client",
                mock_discord_client,
                create=True,
            ),
        ):
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=test_app), base_url="http://test"
            ) as client:
                response = await client.post(
                    "/pushMessage", json={"cmd": "!unknown_xyz", "platform": "discord"}
                )

        assert response.status_code == 400


# ---------------------------------------------------------------------------
# /lineWebhook/{bot_id}
# ---------------------------------------------------------------------------


class TestLineWebhookEndpoint:
    def _webhook_payload(self, events: list[dict] | None = None) -> bytes:
        payload = {"destination": "U123", "events": events or []}
        return json.dumps(payload).encode()

    async def test_unknown_bot_id_returns_404(self, test_app: FastAPI) -> None:
        """存在しない bot_id は 404."""
        empty_bot_store = BotStore()
        group_store = GroupStore()
        app = _build_test_app(empty_bot_store, group_store)
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/lineWebhook/999",
                content=self._webhook_payload(),
                headers={"Content-Type": "application/json"},
            )

        assert response.status_code == 404

    async def test_debug_mode_skips_signature_check(self, test_app: FastAPI) -> None:
        """デバッグモードでは署名なしでも 200 を返す."""
        body = self._webhook_payload()

        mock_settings = MagicMock()
        mock_settings.is_debug = True
        mock_settings.discord_bot_token = None

        with patch(
            "amaototyann.platforms.line.webhook_handler.get_settings",
            return_value=mock_settings,
        ):
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=test_app), base_url="http://test"
            ) as client:
                response = await client.post(
                    "/lineWebhook/1",
                    content=body,
                    headers={"Content-Type": "application/json"},
                )

        assert response.status_code == 200
        assert response.json() == {"status": "finish"}

    async def test_valid_signature_returns_200(self, test_app: FastAPI) -> None:
        """有効な HMAC 署名でリクエストが通る."""
        secret = "test_secret"
        body = self._webhook_payload()
        signature = _sign_body(body, secret)

        mock_settings = MagicMock()
        mock_settings.is_debug = False
        mock_settings.discord_bot_token = None

        with patch(
            "amaototyann.platforms.line.webhook_handler.get_settings",
            return_value=mock_settings,
        ):
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=test_app), base_url="http://test"
            ) as client:
                response = await client.post(
                    "/lineWebhook/1",
                    content=body,
                    headers={
                        "Content-Type": "application/json",
                        "x-line-signature": signature,
                    },
                )

        assert response.status_code == 200

    async def test_invalid_signature_returns_403(self, test_app: FastAPI) -> None:
        """不正な署名は 403."""
        body = self._webhook_payload()

        mock_settings = MagicMock()
        mock_settings.is_debug = False

        with patch(
            "amaototyann.platforms.line.webhook_handler.get_settings",
            return_value=mock_settings,
        ):
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=test_app), base_url="http://test"
            ) as client:
                response = await client.post(
                    "/lineWebhook/1",
                    content=body,
                    headers={
                        "Content-Type": "application/json",
                        "x-line-signature": "INVALIDSIGNATURE==",
                    },
                )

        assert response.status_code == 403

    async def test_missing_signature_returns_403(self, test_app: FastAPI) -> None:
        """x-line-signature ヘッダーが欠落している場合は 403."""
        body = self._webhook_payload()

        mock_settings = MagicMock()
        mock_settings.is_debug = False

        with patch(
            "amaototyann.platforms.line.webhook_handler.get_settings",
            return_value=mock_settings,
        ):
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=test_app), base_url="http://test"
            ) as client:
                response = await client.post(
                    "/lineWebhook/1",
                    content=body,
                    headers={"Content-Type": "application/json"},
                )

        assert response.status_code == 403

    async def test_message_event_calls_command_handler(self, test_app: FastAPI) -> None:
        """テキストメッセージイベントで LineCommandHandler.process が呼ばれる."""
        body = self._webhook_payload(
            events=[
                {
                    "type": "message",
                    "replyToken": "reply_token_123",
                    "source": {"type": "group", "groupId": "Cgroup123"},
                    "message": {"type": "text", "text": "!help"},
                }
            ]
        )

        mock_settings = MagicMock()
        mock_settings.is_debug = True

        mock_handler = AsyncMock()
        mock_handler.process = AsyncMock(return_value=True)

        with (
            patch(
                "amaototyann.platforms.line.webhook_handler.get_settings",
                return_value=mock_settings,
            ),
            patch(
                "amaototyann.platforms.line.webhook_handler.LineCommandHandler",
                return_value=mock_handler,
            ),
        ):
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=test_app), base_url="http://test"
            ) as client:
                response = await client.post(
                    "/lineWebhook/1",
                    content=body,
                    headers={"Content-Type": "application/json"},
                )

        assert response.status_code == 200
        mock_handler.process.assert_awaited_once_with("!help")

    async def test_non_command_message_does_not_call_handler(self, test_app: FastAPI) -> None:
        """'!' で始まらないメッセージはコマンドハンドラーを呼ばない."""
        body = self._webhook_payload(
            events=[
                {
                    "type": "message",
                    "replyToken": "reply_token_abc",
                    "source": {"type": "group", "groupId": "Cgroup123"},
                    "message": {"type": "text", "text": "こんにちは"},
                }
            ]
        )

        mock_settings = MagicMock()
        mock_settings.is_debug = True

        mock_handler_cls = MagicMock()

        with (
            patch(
                "amaototyann.platforms.line.webhook_handler.get_settings",
                return_value=mock_settings,
            ),
            patch(
                "amaototyann.platforms.line.webhook_handler.LineCommandHandler",
                mock_handler_cls,
            ),
        ):
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=test_app), base_url="http://test"
            ) as client:
                response = await client.post(
                    "/lineWebhook/1",
                    content=body,
                    headers={"Content-Type": "application/json"},
                )

        assert response.status_code == 200
        mock_handler_cls.assert_not_called()


# ---------------------------------------------------------------------------
# /api/admin/settings/*
# ---------------------------------------------------------------------------


def _make_settings_store_with_data() -> SettingsStore:
    """Pre-populated SettingsStore を返すヘルパー."""
    return SettingsStore()


def _make_mock_sheets_client_for_settings() -> AsyncMock:
    """設定エンドポイントで使う sheets_client モックを生成する."""
    mock = AsyncMock()
    mock.set_members = AsyncMock(return_value=True)
    mock.set_practice_defaults = AsyncMock(return_value=True)
    mock.set_app_setting = AsyncMock(return_value=True)
    return mock


class TestSettingsRoutes:
    """Test /api/admin/settings/* endpoints."""

    # -----------------------------------------------------------------------
    # GET /api/admin/settings/members
    # -----------------------------------------------------------------------

    async def test_get_members_returns_200_with_list(self) -> None:
        """認証なし (admin_password=None) で GET /settings/members が 200 を返す."""
        store = SettingsStore()
        await store.load(["Alice", "Bob"], [], {})

        mock_settings = MagicMock()
        mock_settings.admin_password = None  # debug mode — skip auth

        with patch("amaototyann.server.routes.api_admin.get_settings", return_value=mock_settings):
            app = _build_test_app(BotStore(), GroupStore(), settings_store=store)
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.get("/api/admin/settings/members")

        assert response.status_code == 200

    async def test_get_members_without_auth_returns_401(self) -> None:
        """admin_password が設定されているとき、Cookie なしで 401 が返る."""
        mock_settings = MagicMock()
        mock_settings.admin_password = "secret"

        with patch("amaototyann.server.routes.api_admin.get_settings", return_value=mock_settings):
            app = _build_test_app(BotStore(), GroupStore())
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.get("/api/admin/settings/members")

        assert response.status_code == 401

    async def test_get_members_returns_member_list(self) -> None:
        """GET /settings/members はメンバーリストを JSON 配列で返す."""
        store = SettingsStore()
        await store.load(["Alice", "Bob", "Carol"], [], {})

        mock_settings = MagicMock()
        mock_settings.admin_password = None

        with patch("amaototyann.server.routes.api_admin.get_settings", return_value=mock_settings):
            app = _build_test_app(BotStore(), GroupStore(), settings_store=store)
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.get("/api/admin/settings/members")

        assert response.status_code == 200
        assert response.json() == ["Alice", "Bob", "Carol"]

    async def test_get_members_empty_store_returns_empty_list(self) -> None:
        """空の SettingsStore で GET /settings/members は [] を返す."""
        mock_settings = MagicMock()
        mock_settings.admin_password = None

        with patch("amaototyann.server.routes.api_admin.get_settings", return_value=mock_settings):
            app = _build_test_app(BotStore(), GroupStore())
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.get("/api/admin/settings/members")

        assert response.status_code == 200
        assert response.json() == []

    # -----------------------------------------------------------------------
    # PUT /api/admin/settings/members
    # -----------------------------------------------------------------------

    async def test_put_members_without_auth_returns_401(self) -> None:
        """admin_password が設定されているとき、Cookie なしで PUT も 401."""
        mock_settings = MagicMock()
        mock_settings.admin_password = "secret"

        with patch("amaototyann.server.routes.api_admin.get_settings", return_value=mock_settings):
            app = _build_test_app(BotStore(), GroupStore())
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.put(
                    "/api/admin/settings/members", json={"members": ["Alice"]}
                )

        assert response.status_code == 401

    async def test_put_members_updates_store(self) -> None:
        """PUT /settings/members が sheets_client を呼び、store を更新し 200 を返す."""
        store = SettingsStore()
        mock_sheets = _make_mock_sheets_client_for_settings()
        mock_settings = MagicMock()
        mock_settings.admin_password = None

        with patch("amaototyann.server.routes.api_admin.get_settings", return_value=mock_settings):
            app = _build_test_app(
                BotStore(), GroupStore(), settings_store=store, sheets_client=mock_sheets
            )
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.put(
                    "/api/admin/settings/members", json={"members": ["Alice", "Bob"]}
                )

        assert response.status_code == 200
        assert response.json() == {"ok": True}
        mock_sheets.set_members.assert_awaited_once_with(["Alice", "Bob"])
        assert await store.get_members() == ["Alice", "Bob"]

    async def test_put_members_sheets_failure_returns_500(self) -> None:
        """sheets_client.set_members が False を返すと 500 が返る."""
        mock_sheets = AsyncMock()
        mock_sheets.set_members = AsyncMock(return_value=False)
        mock_settings = MagicMock()
        mock_settings.admin_password = None

        with patch("amaototyann.server.routes.api_admin.get_settings", return_value=mock_settings):
            app = _build_test_app(BotStore(), GroupStore(), sheets_client=mock_sheets)
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.put(
                    "/api/admin/settings/members", json={"members": ["Alice"]}
                )

        assert response.status_code == 500

    async def test_put_members_no_sheets_client_returns_503(self) -> None:
        """sheets_client が None のとき 503 が返る."""
        mock_settings = MagicMock()
        mock_settings.admin_password = None

        with patch("amaototyann.server.routes.api_admin.get_settings", return_value=mock_settings):
            app = _build_test_app(BotStore(), GroupStore(), sheets_client=None)
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.put(
                    "/api/admin/settings/members", json={"members": ["Alice"]}
                )

        assert response.status_code == 503

    # -----------------------------------------------------------------------
    # GET /api/admin/settings/practice-defaults
    # -----------------------------------------------------------------------

    async def test_get_practice_defaults_returns_200(self) -> None:
        """GET /settings/practice-defaults が 200 を返す."""
        store = SettingsStore()
        defaults = [
            PracticeDefault(
                month=1, enabled=True, place="場所1", start_time="14:00", end_time="17:00"
            )
        ]
        await store.load([], defaults, {})

        mock_settings = MagicMock()
        mock_settings.admin_password = None

        with patch("amaototyann.server.routes.api_admin.get_settings", return_value=mock_settings):
            app = _build_test_app(BotStore(), GroupStore(), settings_store=store)
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.get("/api/admin/settings/practice-defaults")

        assert response.status_code == 200
        body = response.json()
        assert isinstance(body, list)
        assert len(body) == 1
        assert body[0]["month"] == 1

    async def test_get_practice_defaults_without_auth_returns_401(self) -> None:
        """認証なしで GET /settings/practice-defaults は 401 を返す."""
        mock_settings = MagicMock()
        mock_settings.admin_password = "secret"

        with patch("amaototyann.server.routes.api_admin.get_settings", return_value=mock_settings):
            app = _build_test_app(BotStore(), GroupStore())
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.get("/api/admin/settings/practice-defaults")

        assert response.status_code == 401

    # -----------------------------------------------------------------------
    # PUT /api/admin/settings/practice-defaults
    # -----------------------------------------------------------------------

    async def test_put_practice_defaults_updates_store(self) -> None:
        """PUT /settings/practice-defaults が store を更新し 200 を返す."""
        store = SettingsStore()
        mock_sheets = _make_mock_sheets_client_for_settings()
        mock_settings = MagicMock()
        mock_settings.admin_password = None

        defaults_payload = [
            {
                "month": 1,
                "enabled": True,
                "place": "場所A",
                "start_time": "14:00",
                "end_time": "17:00",
            }
        ]

        with patch("amaototyann.server.routes.api_admin.get_settings", return_value=mock_settings):
            app = _build_test_app(
                BotStore(), GroupStore(), settings_store=store, sheets_client=mock_sheets
            )
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.put(
                    "/api/admin/settings/practice-defaults", json={"defaults": defaults_payload}
                )

        assert response.status_code == 200
        assert response.json() == {"ok": True}
        mock_sheets.set_practice_defaults.assert_awaited_once_with(defaults_payload)
        new_defaults = await store.get_practice_defaults()
        assert len(new_defaults) == 1
        assert new_defaults[0].place == "場所A"

    async def test_put_practice_defaults_sheets_failure_returns_500(self) -> None:
        """sheets_client.set_practice_defaults が False のとき 500 が返る."""
        mock_sheets = AsyncMock()
        mock_sheets.set_practice_defaults = AsyncMock(return_value=False)
        mock_settings = MagicMock()
        mock_settings.admin_password = None

        with patch("amaototyann.server.routes.api_admin.get_settings", return_value=mock_settings):
            app = _build_test_app(BotStore(), GroupStore(), sheets_client=mock_sheets)
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.put(
                    "/api/admin/settings/practice-defaults",
                    json={
                        "defaults": [
                            {
                                "month": 1,
                                "enabled": True,
                                "place": "",
                                "start_time": "14:00",
                                "end_time": "17:00",
                            }
                        ]
                    },
                )

        assert response.status_code == 500

    # -----------------------------------------------------------------------
    # GET /api/admin/settings/app
    # -----------------------------------------------------------------------

    async def test_get_app_settings_returns_200(self) -> None:
        """GET /settings/app が全アプリ設定を返す."""
        store = SettingsStore()
        await store.load([], [], {"remind_hour": "8", "timezone": "Asia/Tokyo"})

        mock_settings = MagicMock()
        mock_settings.admin_password = None

        with patch("amaototyann.server.routes.api_admin.get_settings", return_value=mock_settings):
            app = _build_test_app(BotStore(), GroupStore(), settings_store=store)
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.get("/api/admin/settings/app")

        assert response.status_code == 200
        body = response.json()
        assert body["remind_hour"] == "8"
        assert body["timezone"] == "Asia/Tokyo"

    async def test_get_app_settings_without_auth_returns_401(self) -> None:
        """認証なしで GET /settings/app は 401 を返す."""
        mock_settings = MagicMock()
        mock_settings.admin_password = "secret"

        with patch("amaototyann.server.routes.api_admin.get_settings", return_value=mock_settings):
            app = _build_test_app(BotStore(), GroupStore())
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.get("/api/admin/settings/app")

        assert response.status_code == 401

    # -----------------------------------------------------------------------
    # PUT /api/admin/settings/app
    # -----------------------------------------------------------------------

    async def test_put_app_settings_updates_store(self) -> None:
        """PUT /settings/app が各キーを sheets_client と store に書き込み 200 を返す."""
        store = SettingsStore()
        mock_sheets = _make_mock_sheets_client_for_settings()
        mock_settings = MagicMock()
        mock_settings.admin_password = None

        with patch("amaototyann.server.routes.api_admin.get_settings", return_value=mock_settings):
            app = _build_test_app(
                BotStore(), GroupStore(), settings_store=store, sheets_client=mock_sheets
            )
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.put(
                    "/api/admin/settings/app", json={"remind_hour": "9", "timezone": "Asia/Tokyo"}
                )

        assert response.status_code == 200
        assert response.json() == {"ok": True}
        assert mock_sheets.set_app_setting.await_count == 2
        assert store.get_setting("remind_hour") == "9"
        assert store.get_setting("timezone") == "Asia/Tokyo"

    async def test_put_app_settings_sheets_failure_returns_500(self) -> None:
        """sheets_client.set_app_setting が False のとき 500 が返る."""
        mock_sheets = AsyncMock()
        mock_sheets.set_app_setting = AsyncMock(return_value=False)
        mock_settings = MagicMock()
        mock_settings.admin_password = None

        with patch("amaototyann.server.routes.api_admin.get_settings", return_value=mock_settings):
            app = _build_test_app(BotStore(), GroupStore(), sheets_client=mock_sheets)
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.put("/api/admin/settings/app", json={"remind_hour": "9"})

        assert response.status_code == 500

    async def test_put_app_settings_without_auth_returns_401(self) -> None:
        """認証なしで PUT /settings/app は 401 が返る."""
        mock_settings = MagicMock()
        mock_settings.admin_password = "secret"

        with patch("amaototyann.server.routes.api_admin.get_settings", return_value=mock_settings):
            app = _build_test_app(BotStore(), GroupStore())
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.put("/api/admin/settings/app", json={"remind_hour": "9"})

        assert response.status_code == 401

    async def test_put_app_settings_no_sheets_client_returns_503(self) -> None:
        """sheets_client が None のとき PUT /settings/app は 503 を返す."""
        mock_settings = MagicMock()
        mock_settings.admin_password = None

        with patch("amaototyann.server.routes.api_admin.get_settings", return_value=mock_settings):
            app = _build_test_app(BotStore(), GroupStore(), sheets_client=None)
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.put("/api/admin/settings/app", json={"remind_hour": "9"})

        assert response.status_code == 503
