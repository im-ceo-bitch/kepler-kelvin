"""Ephemeral native Telegram thinking indicator. Never persists a status message."""
import asyncio
import logging
from contextlib import asynccontextmanager

log = logging.getLogger('kelvin.thinking')

class Thinking:
    def __init__(self, bot, chat, interval=4.0):
        self.bot, self.chat, self.interval = bot, chat, interval
        self.gate = asyncio.Lock()

    async def _pulse(self, stop):
        while not stop.is_set():
            try:
                await self.bot.send_chat_action(chat_id=self.chat, action='typing', read_timeout=5, write_timeout=5, connect_timeout=5, pool_timeout=5)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                # UI is best-effort; never fail an owner request on status errors.
                retry = getattr(exc, 'retry_after', 0)
                if hasattr(retry, 'total_seconds'):
                    retry = retry.total_seconds()
                delay = max(self.interval, float(retry or 0)) if isinstance(retry, (int, float)) else self.interval
            else:
                delay = self.interval
            try:
                await asyncio.wait_for(stop.wait(), timeout=delay)
            except asyncio.TimeoutError:
                pass

    @asynccontextmanager
    async def show(self, enabled=True):
        if not enabled:
            async def end(): pass
            yield end
            return
        async with self.gate:
            stop = asyncio.Event()
            task = asyncio.create_task(self._pulse(stop))
            async def end():
                stop.set()
                if not task.done(): task.cancel()
                await asyncio.gather(task, return_exceptions=True)
            try:
                yield end
            finally:
                await end()
