"""Offline tests for the Telegram backend using a fake Telethon client."""
from __future__ import annotations

import asyncio
import json

import pytest

from client import (
    INDEX_MARKER,
    LEGACY_INDEX_HEADER,
    StorageUnavailable,
    TelegramStorage,
)


class FakeTypes:
    class InputMessagesFilterPinned:
        pass

    class DocumentAttributeFilename:
        def __init__(self, name):
            self.name = name

    class MessageMediaDocument:
        pass


class FakeMessage:
    def __init__(self, mid, text="", raw=None, document=False):
        self.id = mid
        self.text = text
        self.raw = raw
        self.document = document


class FakeClient:
    def __init__(self):
        self.messages = {}
        self.pinned = []
        self.searchable = []
        self.next_id = 100
        self.pin_ok = True
        self.fail_reads = False

    def is_connected(self):
        return True

    async def disconnect(self):
        pass

    async def get_messages(self, channel, ids=None, filter=None, limit=None):
        if self.fail_reads:
            raise ConnectionError("network down")
        if filter is not None:
            return [self.messages[i] for i in self.pinned if i in self.messages]
        return self.messages.get(ids)

    async def iter_messages(self, channel, search=None, limit=None):
        if self.fail_reads:
            raise ConnectionError("network down")
        for msg in self.searchable:
            yield msg

    async def download_media(self, msg, file=bytes):
        return msg.raw

    async def send_file(self, channel, payload, **kwargs):
        self.next_id += 1
        msg = FakeMessage(self.next_id, text=kwargs.get("caption", ""), raw=payload, document=True)
        self.messages[msg.id] = msg
        self.searchable.insert(0, msg)
        return msg

    async def send_message(self, channel, text):
        self.next_id += 1
        msg = FakeMessage(self.next_id, text=text)
        self.messages[msg.id] = msg
        self.searchable.insert(0, msg)
        return msg

    async def pin_message(self, channel, message_id):
        if not self.pin_ok:
            raise PermissionError("not allowed to pin")
        self.pinned.append(message_id)

    async def delete_messages(self, channel, message_id):
        self.messages.pop(message_id, None)
        self.pinned = [i for i in self.pinned if i != message_id]
        self.searchable = [m for m in self.searchable if m.id != message_id]

    async def edit_message(self, channel, message_id, text):
        if message_id not in self.messages:
            raise ValueError("message gone")
        self.messages[message_id].text = text


@pytest.fixture
def telegram():
    storage = TelegramStorage(credentials={
        "api_id": 1,
        "api_hash": "hash",
        "session": "session",
        "channel_id": -100,
        "index_message_id": 4,
    })
    storage.client = FakeClient()
    storage._telethon = (object, object, FakeTypes)

    async def noop_connect():
        return None

    storage.connect = noop_connect
    return storage


def run(coro):
    return asyncio.run(coro)


def test_reads_legacy_fixed_message_index(telegram):
    index = {"projects": {"1234": {"name": "Legacy"}}}
    telegram.client.messages[4] = FakeMessage(
        4, text=LEGACY_INDEX_HEADER + json.dumps(index, indent=2)
    )

    async def read():
        async with telegram.session():
            return await telegram.get_index()

    assert run(read()) == index


def test_writes_pinned_json_document_and_reads_it_back(telegram):
    index = {"projects": {"1234": {"name": "Big " * 5000}}}

    async def write_then_read():
        async with telegram.session():
            await telegram.update_index(index)
            return await telegram.get_index()

    assert run(write_then_read()) == index
    assert telegram.client.pinned, "index document should be pinned"
    assert any(msg.document for msg in telegram.client.messages.values())


def test_falls_back_to_locator_message_when_pin_fails(telegram):
    telegram.client.pin_ok = False
    index = {"projects": {"9": {"name": "No pin rights"}}}

    async def write_then_read():
        async with telegram.session():
            await telegram.update_index(index)
            return await telegram.get_index()

    assert run(write_then_read()) == index
    assert any("LOCATOR" in (msg.text or "") for msg in telegram.client.messages.values())


def test_failed_lookup_raises_instead_of_returning_empty_index(telegram):
    telegram.client.fail_reads = True

    async def read():
        async with telegram.session():
            return await telegram.get_index()

    with pytest.raises(StorageUnavailable, match="Could not"):
        run(read())


def test_gv_edit_and_read(telegram):
    async def scenario():
        async with telegram.session():
            mid = await telegram.store_gv("score", "9001")
            assert await telegram.get_gv(mid) == "9001"
            mid2 = await telegram.store_gv("score", 'a "quoted" value', mid)
            assert mid2 == mid
            assert await telegram.get_gv(mid) == 'a "quoted" value'
            assert len(telegram.client.messages) == 1  # edited, not duplicated

    run(scenario())


def test_unconfigured_telegram_raises_on_connect(telegram):
    telegram.session_str = None
    # Restore the real connect() so the configuration check runs.
    telegram.connect = type(telegram).connect.__get__(telegram)

    async def connect():
        async with telegram.session():
            pass

    with pytest.raises(StorageUnavailable, match="Missing Telegram settings"):
        run(connect())
