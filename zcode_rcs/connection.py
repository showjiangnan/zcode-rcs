import asyncio
import json
from contextlib import suppress

from fastapi import WebSocket


class Connection:
    """A bounded transport queue. Closing never creates an offline business queue."""

    def __init__(self, ws: WebSocket, maximum: int):
        self.ws = ws
        self.maximum = maximum
        self.queue: asyncio.Queue[bytes | str] = asyncio.Queue(maxsize=512)
        self.bytes = 0
        self.closed = False
        self.on_watermark = None
        self.saturated = False
        self.task = asyncio.create_task(self._send())

    async def send(self, value: dict | bytes):
        if self.closed:
            raise ConnectionError("CONNECTION_CLOSED")
        payload = json.dumps(value, separators=(",", ":"), ensure_ascii=False) if isinstance(value, dict) else value
        size = len(payload.encode()) if isinstance(payload, str) else len(payload)
        if self.bytes + size > self.maximum or self.queue.full():
            await self.close(1013, "FLOW_SATURATED")
            raise ConnectionError("FLOW_SATURATED")
        self.bytes += size
        self.queue.put_nowait(payload)
        if self.bytes >= self.maximum // 2 and not self.saturated:
            self.saturated = True
            if self.on_watermark:
                await self.on_watermark("saturated")

    async def _send(self):
        try:
            while True:
                payload = await self.queue.get()
                if isinstance(payload, bytes):
                    await self.ws.send_bytes(payload)
                    self.bytes -= len(payload)
                else:
                    await self.ws.send_text(payload)
                    self.bytes -= len(payload.encode())
                if self.saturated and self.bytes < self.maximum // 4:
                    self.saturated = False
                    if self.on_watermark:
                        await self.on_watermark("drained")
        except (Exception, asyncio.CancelledError):
            self.closed = True
            with suppress(Exception):
                await self.ws.close(code=1011)

    async def close(self, code=1000, reason=""):
        self.closed = True
        with suppress(Exception):
            await self.ws.close(code=code, reason=reason)
        if self.task is not asyncio.current_task():
            self.task.cancel()
            with suppress(asyncio.CancelledError):
                await self.task
        while not self.queue.empty():
            self.queue.get_nowait()
        self.bytes = 0
