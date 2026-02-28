"""日本語コマンド変換モジュールのテスト.

converter.py の convert_jp_command 関数が、各種日本語表現を
正しい英語コマンドへ変換することを検証する。
"""

from __future__ import annotations

import pytest

from amaototyann.platforms.line.converter import convert_jp_command


class TestExactMatchCommands:
    """完全一致マッピングのテスト."""

    # --- !youtube ---
    @pytest.mark.parametrize(
        "text",
        ["Youtube", "youtube", "YOUTUBE", "ユーチューブ", "ようつべ"],
    )
    def test_youtube_variants(self, text: str) -> None:
        assert convert_jp_command(text) == "!youtube"

    # --- !instagram ---
    @pytest.mark.parametrize(
        "text",
        [
            "Instagram",
            "instagram",
            "インスタグラム",
            "いんすたぐらむ",
            "インスタ",
            "いんすた",
        ],
    )
    def test_instagram_variants(self, text: str) -> None:
        assert convert_jp_command(text) == "!instagram"

    # --- !twitter ---
    @pytest.mark.parametrize(
        "text",
        [
            "Twitter",
            "twitter",
            "ツイッター",
            "ついったー",
            "X",
            "x",
            "エックス",
            "えっくす",
        ],
    )
    def test_twitter_variants(self, text: str) -> None:
        assert convert_jp_command(text) == "!twitter"

    # --- !homepage ---
    @pytest.mark.parametrize(
        "text",
        ["ホームページ", "HP", "hp", "ほーむぺーじ"],
    )
    def test_homepage_variants(self, text: str) -> None:
        assert convert_jp_command(text) == "!homepage"


class TestPrefixMatchCommands:
    """前方一致マッピングのテスト.

    引き継ぎ資料系は前方一致なので、キーで始まる任意の文字列に一致する。
    """

    @pytest.mark.parametrize(
        "text",
        [
            "引き継ぎ資料",
            "引継ぎ資料",
            "ScrapBox",
            "scrapbox",
            "SCRAPBOX",
            "ひきつぎしりょう",
            "すくらっぷぼっくす",
        ],
    )
    def test_handover_exact_keys(self, text: str) -> None:
        """キーそのものでも前方一致でマッチする."""
        assert convert_jp_command(text) == "!handover"

    @pytest.mark.parametrize(
        "text",
        [
            "引き継ぎ資料はこちら",
            "引継ぎ資料を見てください",
            "ScrapBox の URL",
            "ひきつぎしりょうです",
        ],
    )
    def test_handover_prefix_with_trailing_text(self, text: str) -> None:
        """キーで始まる長い文字列も前方一致でマッチする."""
        assert convert_jp_command(text) == "!handover"


class TestUnknownCommands:
    """変換ルールに該当しない入力はそのまま返される."""

    @pytest.mark.parametrize(
        "text",
        [
            "!help",
            "!practice",
            "こんにちは",
            "おはよう",
            "random text",
            "",
            "123",
        ],
    )
    def test_unknown_returns_original(self, text: str) -> None:
        assert convert_jp_command(text) == text


class TestEdgeCases:
    """エッジケースのテスト."""

    def test_case_insensitive_exact_match(self) -> None:
        """完全一致は大文字小文字を区別しない."""
        assert convert_jp_command("YOUTUBE") == "!youtube"
        assert convert_jp_command("youtube") == "!youtube"
        assert convert_jp_command("YouTube") == "!youtube"

    def test_case_insensitive_prefix_match(self) -> None:
        """前方一致も大文字小文字を区別しない."""
        assert convert_jp_command("SCRAPBOX extra") == "!handover"

    def test_whitespace_only_returns_original(self) -> None:
        """空白のみはマッチしない."""
        result = convert_jp_command("   ")
        assert result == "   "

    def test_partial_key_no_match(self) -> None:
        """キーの途中まで (前方一致のキー以外) はマッチしない."""
        # "インスタ" はキー → マッチする
        assert convert_jp_command("インスタ") == "!instagram"
        # "インス" はキーに登録されていない → そのまま返す
        assert convert_jp_command("インス") == "インス"

    def test_returns_string_type(self) -> None:
        """返り値の型は常に str."""
        result = convert_jp_command("Youtube")
        assert isinstance(result, str)

    def test_exact_match_takes_priority_over_prefix(self) -> None:
        """完全一致辞書が前方一致より先にチェックされる.

        現在の登録内容では両方が重複するケースはないが、
        関数の評価順 (完全一致 → 前方一致) を確認する。
        """
        # "ユーチューブ" は完全一致キー
        assert convert_jp_command("ユーチューブ") == "!youtube"

    def test_command_with_exclamation_mark_unchanged(self) -> None:
        """英語コマンド '!' 付きはそのまま返る."""
        assert convert_jp_command("!help") == "!help"
        assert convert_jp_command("!practice") == "!practice"

    def test_japanese_fullwidth_exclamation_not_converted_by_converter(self) -> None:
        """全角の感嘆符はコンバーター自体では変換しない (呼び出し元が担当)."""
        # convert_jp_command は全角感嘆符の変換を行わない
        result = convert_jp_command("！help")
        assert result == "！help"

    def test_mixed_language_no_match(self) -> None:
        """登録キーを含まない混在文字列はそのまま返る."""
        result = convert_jp_command("Hello World")
        assert result == "Hello World"
