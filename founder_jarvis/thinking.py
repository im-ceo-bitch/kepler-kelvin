"""Ephemeral native Telegram thinking indicator. Never persists a status message."""
import asyncio
import logging
import secrets
from contextlib import asynccontextmanager

log = logging.getLogger('kelvin.thinking')

class Thinking:
    def __init__(self, bot, chat, interval=4.0):
        self.bot, self.chat, self.interval = bot, chat, interval
        self.gate = asyncio.Lock()

    async def _pulse(self, draft_id, stop):
        native = callable(getattr(self.bot, 'send_message_draft', None))
        while not stop.is_set():
            try:
                if native:
                    # Empty text asks Telegram to render its own Thinking UI.
                    await self.bot.send_message_draft(chat_id=self.chat, draft_id=draft_id, text='', read_timeout=5, write_timeout=5, connect_timeout=5, pool_timeout=5)
                else:
                    await self.bot.send_chat_action(chat_id=self.chat, action='typing', read_timeout=5, write_timeout=5, connect_timeout=5, pool_timeout=5)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                # UI is best-effort. Never fail an actual owner request on a draft error.
                if native:
                    native = False
                    log.debug('Native draft unavailable: %s', type(exc).__name__)
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
            task = asyncio.create_task(self._pulse(secrets.randbelow(2**31-1)+1, stop))
            async def end():
                stop.set()
                if not task.done(): task.cancel()
                await asyncio.gather(task, return_exceptions=True)
            try:
                yield end
            finally:
                await end()
