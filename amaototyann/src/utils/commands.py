"""commandでのユーティリティを定義するモジュール"""
from typing import NamedTuple, Callable, Any


class Command(NamedTuple):
    """各コマンドの情報を格納するクラス"""
    text: str
    description: str
    process: Callable[..., Any]


class CommandRegistry(type):
    """Commandクラスのメタクラス"""
    registry: list[Command] = []

    def __new__(mcs, name, bases, ns):
        """Commandが定義されたときにregistryに登録する処理"""
        cls = super().__new__(mcs, name, bases, dict(ns))
        # クラス定義時に見つかった Command だけで registry を初期化
        cls.registry = [v for v in ns.values() if isinstance(v, Command)]
        return cls
