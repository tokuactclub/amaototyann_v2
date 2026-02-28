"""Tests for amaototyann.store.memory — BotStore and GroupStore."""

import asyncio

import pytest

from amaototyann.models.bot import BotInfo, GroupInfo
from amaototyann.store.memory import BotStore, GroupStore

# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------


def make_bot(bot_id: int = 1, *, name: str = "TestBot") -> BotInfo:
    return BotInfo(
        id=bot_id,
        bot_name=name,
        channel_access_token=f"token-{bot_id}",
        channel_secret=f"secret-{bot_id}",
        gpt_webhook_url=f"https://example.com/gpt/{bot_id}",
        in_group=False,
    )


def make_group(group_id: str = "G001", name: str = "TestGroup") -> GroupInfo:
    return GroupInfo(id=group_id, group_name=name)


# ---------------------------------------------------------------------------
# BotStore — basic operations
# ---------------------------------------------------------------------------


class TestBotStoreLoad:
    async def test_load_populates_store(self) -> None:
        store = BotStore()
        bots = [make_bot(1), make_bot(2)]
        await store.load(bots)
        result = await store.list_all()
        assert len(result) == 2

    async def test_load_with_empty_list_clears_store(self) -> None:
        store = BotStore()
        await store.load([make_bot(1)])
        await store.load([])
        result = await store.list_all()
        assert result == []

    async def test_load_resets_dirty_flag(self) -> None:
        store = BotStore()
        await store.load([make_bot(1)])
        await store.update(1, in_group=True)
        assert store.is_dirty is True
        await store.load([make_bot(1)])
        assert store.is_dirty is False

    async def test_load_overwrites_previous_data(self) -> None:
        store = BotStore()
        await store.load([make_bot(1, name="OldBot")])
        await store.load([make_bot(1, name="NewBot")])
        bot = await store.get(1)
        assert bot.bot_name == "NewBot"


class TestBotStoreGet:
    async def test_get_existing_bot(self) -> None:
        store = BotStore()
        await store.load([make_bot(42)])
        bot = await store.get(42)
        assert bot.id == 42

    async def test_get_missing_bot_raises_key_error(self) -> None:
        store = BotStore()
        await store.load([])
        with pytest.raises(KeyError, match="Bot not found: 99"):
            await store.get(99)

    async def test_get_returns_correct_instance(self) -> None:
        store = BotStore()
        bots = [make_bot(1, name="Alpha"), make_bot(2, name="Beta")]
        await store.load(bots)
        assert (await store.get(1)).bot_name == "Alpha"
        assert (await store.get(2)).bot_name == "Beta"


class TestBotStoreListAll:
    async def test_list_all_empty_store(self) -> None:
        store = BotStore()
        result = await store.list_all()
        assert result == []

    async def test_list_all_returns_all_bots(self) -> None:
        store = BotStore()
        await store.load([make_bot(1), make_bot(2), make_bot(3)])
        result = await store.list_all()
        ids = {b.id for b in result}
        assert ids == {1, 2, 3}


class TestBotStoreUpdate:
    async def test_update_existing_field(self) -> None:
        store = BotStore()
        await store.load([make_bot(1)])
        updated = await store.update(1, in_group=True)
        assert updated.in_group is True

    async def test_update_persists_in_store(self) -> None:
        store = BotStore()
        await store.load([make_bot(1)])
        await store.update(1, bot_name="Renamed")
        bot = await store.get(1)
        assert bot.bot_name == "Renamed"

    async def test_update_sets_dirty_flag(self) -> None:
        store = BotStore()
        await store.load([make_bot(1)])
        assert store.is_dirty is False
        await store.update(1, in_group=True)
        assert store.is_dirty is True

    async def test_update_missing_bot_raises_key_error(self) -> None:
        store = BotStore()
        await store.load([])
        with pytest.raises(KeyError, match="Bot not found: 5"):
            await store.update(5, in_group=True)

    async def test_update_multiple_fields(self) -> None:
        store = BotStore()
        await store.load([make_bot(1)])
        updated = await store.update(1, bot_name="NewName", in_group=True)
        assert updated.bot_name == "NewName"
        assert updated.in_group is True


class TestBotStoreDirtyFlag:
    async def test_initial_not_dirty(self) -> None:
        store = BotStore()
        assert store.is_dirty is False

    async def test_mark_clean_clears_dirty(self) -> None:
        store = BotStore()
        await store.load([make_bot(1)])
        await store.update(1, in_group=True)
        assert store.is_dirty is True
        await store.mark_clean()
        assert store.is_dirty is False


class TestBotStoreDumpForBackup:
    async def test_dump_for_backup_structure(self) -> None:
        store = BotStore()
        bot = make_bot(7, name="BackupBot")
        await store.load([bot])
        dump = await store.dump_for_backup()
        assert len(dump) == 1
        row = dump[0]
        assert row[0] == 7
        assert row[1] == "BackupBot"
        assert row[2] == "token-7"
        assert row[3] == "secret-7"
        assert row[5] is False

    async def test_dump_empty_store(self) -> None:
        store = BotStore()
        dump = await store.dump_for_backup()
        assert dump == []


# ---------------------------------------------------------------------------
# BotStore — concurrency safety
# ---------------------------------------------------------------------------


class TestBotStoreConcurrency:
    async def test_concurrent_updates_all_succeed(self) -> None:
        store = BotStore()
        await store.load([make_bot(1)])

        async def toggle(flag: bool) -> BotInfo:
            return await store.update(1, in_group=flag)

        # 50 concurrent toggles — all should resolve without deadlock or error
        results = await asyncio.gather(*[toggle(i % 2 == 0) for i in range(50)])
        assert len(results) == 50

    async def test_concurrent_reads_return_consistent_data(self) -> None:
        store = BotStore()
        bots = [make_bot(i) for i in range(1, 11)]
        await store.load(bots)

        results = await asyncio.gather(*[store.get(i) for i in range(1, 11)])
        ids = {b.id for b in results}
        assert ids == set(range(1, 11))

    async def test_concurrent_load_and_get_do_not_deadlock(self) -> None:
        store = BotStore()
        await store.load([make_bot(1)])

        async def reload() -> None:
            await store.load([make_bot(1, name="Reloaded")])

        async def read() -> BotInfo:
            return await store.get(1)

        # Interleave loads and reads
        tasks = [reload() if i % 3 == 0 else read() for i in range(30)]
        await asyncio.gather(*tasks, return_exceptions=True)
        # If we get here without deadlock / exception, test passes

    async def test_concurrent_list_all_is_safe(self) -> None:
        store = BotStore()
        await store.load([make_bot(i) for i in range(1, 6)])

        results = await asyncio.gather(*[store.list_all() for _ in range(20)])
        for r in results:
            assert len(r) == 5


# ---------------------------------------------------------------------------
# GroupStore — basic operations
# ---------------------------------------------------------------------------


class TestGroupStoreLoad:
    async def test_load_initializes_data(self) -> None:
        store = GroupStore()
        await store.load(make_group("G1", "合唱団"))
        info = await store.get()
        assert info.id == "G1"
        assert info.group_name == "合唱団"

    async def test_load_resets_dirty_flag(self) -> None:
        store = GroupStore()
        await store.load(make_group())
        await store.set_group_info("G2", "新グループ")
        assert store.is_dirty is True
        await store.load(make_group())
        assert store.is_dirty is False

    async def test_load_overwrites_previous_data(self) -> None:
        store = GroupStore()
        await store.load(make_group("G1", "Old"))
        await store.load(make_group("G2", "New"))
        info = await store.get()
        assert info.id == "G2"
        assert info.group_name == "New"


class TestGroupStoreGet:
    async def test_get_before_load_raises_value_error(self) -> None:
        store = GroupStore()
        with pytest.raises(ValueError, match="Group info not initialized"):
            await store.get()

    async def test_get_after_load_returns_correct_info(self) -> None:
        store = GroupStore()
        await store.load(make_group("G99", "TestGroup"))
        info = await store.get()
        assert info.id == "G99"
        assert info.group_name == "TestGroup"


class TestGroupStoreGetGroupId:
    async def test_get_group_id_returns_correct_id(self) -> None:
        store = GroupStore()
        await store.load(make_group("GX01", "SomeGroup"))
        gid = await store.get_group_id()
        assert gid == "GX01"

    async def test_get_group_id_before_load_raises(self) -> None:
        store = GroupStore()
        with pytest.raises(ValueError, match="Group info not initialized"):
            await store.get_group_id()


class TestGroupStoreSetGroupInfo:
    async def test_set_group_info_updates_data(self) -> None:
        store = GroupStore()
        await store.set_group_info("G-NEW", "新しいグループ")
        info = await store.get()
        assert info.id == "G-NEW"
        assert info.group_name == "新しいグループ"

    async def test_set_group_info_sets_dirty_flag(self) -> None:
        store = GroupStore()
        assert store.is_dirty is False
        await store.set_group_info("G1", "グループ")
        assert store.is_dirty is True

    async def test_set_group_info_overwrites_loaded_data(self) -> None:
        store = GroupStore()
        await store.load(make_group("G-OLD", "古いグループ"))
        await store.set_group_info("G-NEW", "新しいグループ")
        info = await store.get()
        assert info.id == "G-NEW"


class TestGroupStoreDirtyFlag:
    async def test_initial_not_dirty(self) -> None:
        store = GroupStore()
        assert store.is_dirty is False

    async def test_mark_clean_clears_dirty(self) -> None:
        store = GroupStore()
        await store.set_group_info("G1", "グループ")
        assert store.is_dirty is True
        await store.mark_clean()
        assert store.is_dirty is False


class TestGroupStoreDumpForBackup:
    async def test_dump_returns_correct_dict(self) -> None:
        store = GroupStore()
        await store.load(make_group("DUMP-ID", "ダンプグループ"))
        data = await store.dump_for_backup()
        assert data == {"id": "DUMP-ID", "groupName": "ダンプグループ"}

    async def test_dump_before_load_raises_value_error(self) -> None:
        store = GroupStore()
        with pytest.raises(ValueError, match="Group info not initialized"):
            await store.dump_for_backup()


# ---------------------------------------------------------------------------
# GroupStore — concurrency safety
# ---------------------------------------------------------------------------


class TestGroupStoreConcurrency:
    async def test_concurrent_set_group_info_does_not_deadlock(self) -> None:
        store = GroupStore()

        async def set_info(i: int) -> None:
            await store.set_group_info(f"G{i:04d}", f"グループ{i}")

        await asyncio.gather(*[set_info(i) for i in range(50)])
        # Final state must be one of the written values — just verify it's consistent
        info = await store.get()
        assert info.id.startswith("G")
        assert info.group_name.startswith("グループ")

    async def test_concurrent_get_after_load_is_safe(self) -> None:
        store = GroupStore()
        await store.load(make_group("SAFE-ID", "SafeGroup"))

        results = await asyncio.gather(*[store.get() for _ in range(30)])
        for info in results:
            assert info.id == "SAFE-ID"

    async def test_concurrent_reads_and_writes_no_deadlock(self) -> None:
        store = GroupStore()
        await store.load(make_group("INIT", "初期グループ"))

        async def write(i: int) -> None:
            await store.set_group_info(f"G{i}", f"グループ{i}")

        async def read() -> GroupInfo:
            return await store.get()

        tasks = [write(i) if i % 4 == 0 else read() for i in range(40)]
        await asyncio.gather(*tasks, return_exceptions=True)
        # Reaching here without deadlock is the success condition

    async def test_mark_clean_concurrently_with_dirty_writes(self) -> None:
        store = GroupStore()

        async def dirty_write(i: int) -> None:
            await store.set_group_info(f"G{i}", f"グループ{i}")

        async def clean() -> None:
            await store.mark_clean()

        tasks = [dirty_write(i) if i % 3 != 0 else clean() for i in range(30)]
        await asyncio.gather(*tasks)
        # is_dirty reflects last operation — just ensure no deadlock
