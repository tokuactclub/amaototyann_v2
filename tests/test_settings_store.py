"""Tests for amaototyann.store.settings.SettingsStore."""

import asyncio

from amaototyann.models.settings import PracticeDefault
from amaototyann.store.settings import SettingsStore

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_defaults(count: int = 3) -> list[PracticeDefault]:
    return [
        PracticeDefault(
            month=i + 1, enabled=True, place=f"場所{i + 1}", start_time="14:00", end_time="17:00"
        )
        for i in range(count)
    ]


# ---------------------------------------------------------------------------
# SettingsStore.load
# ---------------------------------------------------------------------------


class TestSettingsStoreLoad:
    async def test_load_populates_all_data(self) -> None:
        store = SettingsStore()
        await store.load(["Alice", "Bob"], _make_defaults(2), {"key": "value"})
        members = await store.get_members()
        assert members == ["Alice", "Bob"]
        defaults = await store.get_practice_defaults()
        assert len(defaults) == 2
        settings = await store.get_all_settings()
        assert settings == {"key": "value"}

    async def test_load_clears_dirty_flag(self) -> None:
        store = SettingsStore()
        await store.set_members(["test"])
        assert store.is_dirty
        await store.load([], [], {})
        assert not store.is_dirty

    async def test_load_with_empty_values_clears_store(self) -> None:
        store = SettingsStore()
        await store.load(["Alice"], _make_defaults(3), {"k": "v"})
        await store.load([], [], {})
        members = await store.get_members()
        defaults = await store.get_practice_defaults()
        settings = await store.get_all_settings()
        assert members == []
        assert defaults == []
        assert settings == {}

    async def test_load_overwrites_previous_data(self) -> None:
        store = SettingsStore()
        await store.load(["OldMember"], _make_defaults(1), {"old": "data"})
        await store.load(["NewMember"], _make_defaults(2), {"new": "data"})
        members = await store.get_members()
        defaults = await store.get_practice_defaults()
        assert members == ["NewMember"]
        assert len(defaults) == 2


# ---------------------------------------------------------------------------
# SettingsStore — members
# ---------------------------------------------------------------------------


class TestSettingsStoreMembers:
    async def test_get_members_empty_initial(self) -> None:
        store = SettingsStore()
        members = await store.get_members()
        assert members == []

    async def test_set_members_sets_dirty(self) -> None:
        store = SettingsStore()
        await store.set_members(["Alice"])
        assert store.is_dirty
        members = await store.get_members()
        assert members == ["Alice"]

    async def test_set_members_replaces_list(self) -> None:
        store = SettingsStore()
        await store.set_members(["Alice"])
        await store.set_members(["Bob", "Carol"])
        members = await store.get_members()
        assert members == ["Bob", "Carol"]

    async def test_get_members_returns_copy(self) -> None:
        store = SettingsStore()
        await store.load(["Alice", "Bob"], [], {})
        members = await store.get_members()
        members.append("ExternalMutation")
        assert await store.get_members() == ["Alice", "Bob"]

    async def test_set_members_empty_list(self) -> None:
        store = SettingsStore()
        await store.set_members(["Alice"])
        await store.set_members([])
        assert await store.get_members() == []
        assert store.is_dirty


# ---------------------------------------------------------------------------
# SettingsStore — practice defaults
# ---------------------------------------------------------------------------


class TestSettingsStorePracticeDefaults:
    async def test_get_practice_default_by_month(self) -> None:
        store = SettingsStore()
        await store.load([], _make_defaults(12), {})
        d = store.get_practice_default(3)
        assert d is not None
        assert d.month == 3

    async def test_get_practice_default_missing_month(self) -> None:
        store = SettingsStore()
        assert store.get_practice_default(1) is None

    async def test_get_practice_default_returns_correct_place(self) -> None:
        store = SettingsStore()
        await store.load([], _make_defaults(6), {})
        d = store.get_practice_default(4)
        assert d is not None
        assert d.place == "場所4"

    async def test_set_practice_defaults_sets_dirty(self) -> None:
        store = SettingsStore()
        await store.set_practice_defaults(_make_defaults(1))
        assert store.is_dirty

    async def test_get_practice_defaults_returns_all(self) -> None:
        store = SettingsStore()
        await store.load([], _make_defaults(6), {})
        defaults = await store.get_practice_defaults()
        assert len(defaults) == 6

    async def test_get_practice_defaults_returns_copy(self) -> None:
        store = SettingsStore()
        await store.load([], _make_defaults(3), {})
        defaults = await store.get_practice_defaults()
        defaults.clear()
        assert len(await store.get_practice_defaults()) == 3

    async def test_set_practice_defaults_replaces_existing(self) -> None:
        store = SettingsStore()
        await store.set_practice_defaults(_make_defaults(6))
        await store.set_practice_defaults(_make_defaults(2))
        defaults = await store.get_practice_defaults()
        assert len(defaults) == 2

    async def test_get_practice_default_not_found_returns_none(self) -> None:
        store = SettingsStore()
        await store.load([], _make_defaults(3), {})
        assert store.get_practice_default(12) is None


# ---------------------------------------------------------------------------
# SettingsStore — app settings
# ---------------------------------------------------------------------------


class TestSettingsStoreAppSettings:
    async def test_get_setting_default(self) -> None:
        store = SettingsStore()
        assert store.get_setting("missing", "fallback") == "fallback"

    async def test_get_setting_default_empty_string(self) -> None:
        store = SettingsStore()
        assert store.get_setting("missing") == ""

    async def test_set_and_get_setting(self) -> None:
        store = SettingsStore()
        await store.set_setting("key", "value")
        assert store.get_setting("key") == "value"
        assert store.is_dirty

    async def test_set_setting_overwrites_existing(self) -> None:
        store = SettingsStore()
        await store.set_setting("key", "old")
        await store.set_setting("key", "new")
        assert store.get_setting("key") == "new"

    async def test_get_all_settings_returns_all_keys(self) -> None:
        store = SettingsStore()
        await store.load([], [], {"a": "1", "b": "2"})
        settings = await store.get_all_settings()
        assert settings == {"a": "1", "b": "2"}

    async def test_get_all_settings_returns_copy(self) -> None:
        store = SettingsStore()
        await store.load([], [], {"k": "v"})
        settings = await store.get_all_settings()
        settings["extra"] = "mutation"
        assert await store.get_all_settings() == {"k": "v"}

    async def test_multiple_settings_independent(self) -> None:
        store = SettingsStore()
        await store.set_setting("x", "1")
        await store.set_setting("y", "2")
        assert store.get_setting("x") == "1"
        assert store.get_setting("y") == "2"


# ---------------------------------------------------------------------------
# SettingsStore.dump_for_backup
# ---------------------------------------------------------------------------


class TestSettingsStoreDump:
    async def test_dump_for_backup_structure(self) -> None:
        store = SettingsStore()
        await store.load(["Alice"], _make_defaults(1), {"k": "v"})
        dump = await store.dump_for_backup()
        assert dump["members"] == ["Alice"]
        assert len(dump["practiceDefaults"]) == 1
        assert dump["appSettings"] == {"k": "v"}

    async def test_dump_empty_store(self) -> None:
        store = SettingsStore()
        dump = await store.dump_for_backup()
        assert dump == {"members": [], "practiceDefaults": [], "appSettings": {}}

    async def test_dump_practice_defaults_are_dicts(self) -> None:
        store = SettingsStore()
        await store.load([], _make_defaults(2), {})
        dump = await store.dump_for_backup()
        for d in dump["practiceDefaults"]:
            assert isinstance(d, dict)
            assert "month" in d
            assert "enabled" in d

    async def test_dump_contains_all_members(self) -> None:
        store = SettingsStore()
        members = ["Alice", "Bob", "Carol"]
        await store.load(members, [], {})
        dump = await store.dump_for_backup()
        assert dump["members"] == members


# ---------------------------------------------------------------------------
# SettingsStore.mark_clean
# ---------------------------------------------------------------------------


class TestSettingsStoreMarkClean:
    async def test_initial_not_dirty(self) -> None:
        store = SettingsStore()
        assert store.is_dirty is False

    async def test_mark_clean_after_set_members(self) -> None:
        store = SettingsStore()
        await store.set_members(["Alice"])
        assert store.is_dirty
        await store.mark_clean()
        assert not store.is_dirty

    async def test_mark_clean_after_set_setting(self) -> None:
        store = SettingsStore()
        await store.set_setting("k", "v")
        assert store.is_dirty
        await store.mark_clean()
        assert not store.is_dirty

    async def test_mark_clean_after_set_practice_defaults(self) -> None:
        store = SettingsStore()
        await store.set_practice_defaults(_make_defaults(1))
        assert store.is_dirty
        await store.mark_clean()
        assert not store.is_dirty

    async def test_mark_clean_on_already_clean_store(self) -> None:
        store = SettingsStore()
        # Should not raise
        await store.mark_clean()
        assert not store.is_dirty


# ---------------------------------------------------------------------------
# SettingsStore — concurrency safety
# ---------------------------------------------------------------------------


class TestSettingsStoreConcurrency:
    async def test_concurrent_member_updates(self) -> None:
        store = SettingsStore()

        async def update(name: str) -> None:
            await store.set_members([name])

        await asyncio.gather(*[update(f"User{i}") for i in range(50)])
        members = await store.get_members()
        assert len(members) == 1  # Last write wins

    async def test_concurrent_setting_updates(self) -> None:
        store = SettingsStore()

        async def write(i: int) -> None:
            await store.set_setting(f"key{i}", f"val{i}")

        await asyncio.gather(*[write(i) for i in range(20)])
        # All writes should have succeeded — each used a distinct key
        settings = await store.get_all_settings()
        assert len(settings) == 20

    async def test_concurrent_reads_do_not_deadlock(self) -> None:
        store = SettingsStore()
        await store.load(["Alice", "Bob"], _make_defaults(3), {"a": "1"})

        results = await asyncio.gather(*[store.get_members() for _ in range(30)])
        for r in results:
            assert r == ["Alice", "Bob"]

    async def test_concurrent_loads_and_reads_no_deadlock(self) -> None:
        store = SettingsStore()
        await store.load(["Alice"], _make_defaults(1), {})

        async def reload() -> None:
            await store.load(["Reloaded"], _make_defaults(1), {})

        async def read() -> list[str]:
            return await store.get_members()

        tasks = [reload() if i % 3 == 0 else read() for i in range(30)]
        await asyncio.gather(*tasks, return_exceptions=True)
        # Reaching here without deadlock is the success condition

    async def test_concurrent_mark_clean_with_dirty_writes(self) -> None:
        store = SettingsStore()

        async def dirty_write(i: int) -> None:
            await store.set_setting(f"k{i}", f"v{i}")

        async def clean() -> None:
            await store.mark_clean()

        tasks = [dirty_write(i) if i % 3 != 0 else clean() for i in range(30)]
        await asyncio.gather(*tasks)
        # is_dirty reflects last operation — just ensure no deadlock
