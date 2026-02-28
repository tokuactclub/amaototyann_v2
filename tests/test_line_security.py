"""LINE HMAC 署名検証のテスト.

security.py の verify_line_signature 関数を FastAPI の
テストクライアント経由で検証する。
"""

from __future__ import annotations

import base64
import hashlib
import hmac

import httpx
import pytest
from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse

from amaototyann.platforms.line.security import verify_line_signature

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _compute_signature(body: bytes, secret: str) -> str:
    """LINE 仕様に従い HMAC-SHA256 署名を Base64 エンコードで返す."""
    digest = hmac.new(secret.encode(), body, hashlib.sha256).digest()
    return base64.b64encode(digest).decode()


# ---------------------------------------------------------------------------
# 軽量テスト用アプリ
# ---------------------------------------------------------------------------


def _build_security_test_app(secret: str) -> FastAPI:
    """verify_line_signature を呼ぶだけのミニ FastAPI アプリ."""
    app = FastAPI()

    @app.post("/verify")
    async def _verify(request: Request) -> PlainTextResponse:
        await verify_line_signature(request, secret)
        return PlainTextResponse("ok")

    return app


# ---------------------------------------------------------------------------
# 単体レベル: verify_line_signature の直接テスト
# ---------------------------------------------------------------------------


class TestVerifyLineSignatureUnit:
    """FastAPI Request を直接モックして verify_line_signature をテストする."""

    async def _call(
        self,
        body: bytes,
        signature: str,
        secret: str,
    ) -> bytes:
        """モックの Request を組み立てて verify_line_signature を呼ぶ."""
        from unittest.mock import AsyncMock, MagicMock

        request = MagicMock()
        request.body = AsyncMock(return_value=body)
        request.headers = {"x-line-signature": signature}
        return await verify_line_signature(request, secret)

    async def test_valid_signature_returns_body(self) -> None:
        secret = "my_channel_secret"
        body = b'{"events":[]}'
        signature = _compute_signature(body, secret)

        result = await self._call(body, signature, secret)

        assert result == body

    async def test_invalid_signature_raises_403(self) -> None:
        from fastapi import HTTPException

        secret = "my_channel_secret"
        body = b'{"events":[]}'

        with pytest.raises(HTTPException) as exc_info:
            await self._call(body, "BADSIG==", secret)

        assert exc_info.value.status_code == 403
        assert "Invalid signature" in exc_info.value.detail

    async def test_missing_signature_raises_403(self) -> None:
        from unittest.mock import AsyncMock, MagicMock

        from fastapi import HTTPException

        request = MagicMock()
        request.body = AsyncMock(return_value=b'{"events":[]}')
        request.headers = {}  # x-line-signature 欠落

        with pytest.raises(HTTPException) as exc_info:
            await verify_line_signature(request, "secret")

        assert exc_info.value.status_code == 403
        assert "Missing signature" in exc_info.value.detail

    async def test_empty_body_valid_signature(self) -> None:
        """空のボディでも署名が一致すれば通過する."""
        secret = "secret"
        body = b""
        signature = _compute_signature(body, secret)

        result = await self._call(body, signature, secret)

        assert result == body

    async def test_wrong_secret_raises_403(self) -> None:
        """署名は正しく生成されているが、検証に使う secret が異なる場合は 403."""
        from fastapi import HTTPException

        body = b'{"events":[]}'
        signature = _compute_signature(body, "correct_secret")

        with pytest.raises(HTTPException) as exc_info:
            await self._call(body, signature, "wrong_secret")

        assert exc_info.value.status_code == 403

    async def test_body_tampered_after_signing_raises_403(self) -> None:
        """署名後にボディを改ざんすると検証失敗する."""
        from fastapi import HTTPException

        secret = "secret"
        original_body = b'{"events":[]}'
        signature = _compute_signature(original_body, secret)
        tampered_body = b'{"events":["injected"]}'

        with pytest.raises(HTTPException) as exc_info:
            await self._call(tampered_body, signature, secret)

        assert exc_info.value.status_code == 403


# ---------------------------------------------------------------------------
# 統合レベル: ASGI 経由での HTTP リクエストテスト
# ---------------------------------------------------------------------------


class TestVerifyLineSignatureHttp:
    """httpx.AsyncClient で HTTP リクエストを投げて署名検証をテストする."""

    _SECRET = "http_test_secret"

    @pytest.fixture
    def app(self) -> FastAPI:
        return _build_security_test_app(self._SECRET)

    async def test_valid_signature_returns_200(self, app: FastAPI) -> None:
        body = b'{"events":[],"destination":"U123"}'
        signature = _compute_signature(body, self._SECRET)

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/verify",
                content=body,
                headers={
                    "Content-Type": "application/json",
                    "x-line-signature": signature,
                },
            )

        assert response.status_code == 200
        assert response.text == "ok"

    async def test_invalid_signature_returns_403(self, app: FastAPI) -> None:
        body = b'{"events":[],"destination":"U123"}'

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/verify",
                content=body,
                headers={
                    "Content-Type": "application/json",
                    "x-line-signature": "INVALIDSIGNATURE==",
                },
            )

        assert response.status_code == 403

    async def test_missing_signature_header_returns_403(self, app: FastAPI) -> None:
        body = b'{"events":[]}'

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/verify",
                content=body,
                headers={"Content-Type": "application/json"},
            )

        assert response.status_code == 403

    async def test_different_secret_returns_403(self, app: FastAPI) -> None:
        """同じボディでも別の secret で生成した署名は拒否される."""
        body = b'{"events":[]}'
        wrong_signature = _compute_signature(body, "completely_different_secret")

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/verify",
                content=body,
                headers={
                    "Content-Type": "application/json",
                    "x-line-signature": wrong_signature,
                },
            )

        assert response.status_code == 403

    async def test_correct_signature_with_json_body(self, app: FastAPI) -> None:
        """典型的な LINE Webhook ボディで正しく検証される."""
        body = (
            b'{"destination":"Uxxxxx","events":[{"type":"message","replyToken":"tok",'
            b'"source":{"groupId":"G1","type":"group"},'
            b'"message":{"type":"text","text":"hello"}}]}'
        )
        signature = _compute_signature(body, self._SECRET)

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/verify",
                content=body,
                headers={
                    "Content-Type": "application/json",
                    "x-line-signature": signature,
                },
            )

        assert response.status_code == 200

    async def test_empty_string_signature_returns_403(self, app: FastAPI) -> None:
        """空文字列の署名ヘッダーは拒否される."""
        body = b'{"events":[]}'

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/verify",
                content=body,
                headers={
                    "Content-Type": "application/json",
                    "x-line-signature": "",
                },
            )

        # 空文字は "Missing signature" として扱われる
        assert response.status_code == 403


# ---------------------------------------------------------------------------
# 署名生成ロジック自体の検証
# ---------------------------------------------------------------------------


class TestSignatureComputation:
    """_compute_signature ヘルパーが LINE 仕様と一致することを確認する."""

    def test_known_vector(self) -> None:
        """既知の入力に対する HMAC-SHA256 出力を検証する."""
        secret = "secret"
        body = b"body"
        # python で直接計算した期待値
        expected = base64.b64encode(hmac.new(b"secret", b"body", hashlib.sha256).digest()).decode()
        assert _compute_signature(body, secret) == expected

    def test_different_bodies_produce_different_signatures(self) -> None:
        secret = "same_secret"
        sig1 = _compute_signature(b"body_one", secret)
        sig2 = _compute_signature(b"body_two", secret)
        assert sig1 != sig2

    def test_different_secrets_produce_different_signatures(self) -> None:
        body = b"same_body"
        sig1 = _compute_signature(body, "secret_one")
        sig2 = _compute_signature(body, "secret_two")
        assert sig1 != sig2

    def test_signature_is_base64_encoded(self) -> None:
        sig = _compute_signature(b"data", "key")
        # Base64 デコードが成功すれば正しく Base64 エンコードされている
        decoded = base64.b64decode(sig)
        assert len(decoded) == 32  # SHA-256 は 32 バイト
