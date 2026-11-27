import asyncio
import unittest
from unittest.mock import AsyncMock
from founder_jarvis.thinking import Thinking

class ThinkingTests(unittest.IsolatedAsyncioTestCase):
    async def test_native_typing_only_and_stops(self):
        bot=type('Bot',(),{})();bot.send_message_draft=AsyncMock();bot.send_chat_action=AsyncMock()
        async with Thinking(bot,123,.01).show() as end:
            await asyncio.sleep(.035);await end();count=bot.send_chat_action.await_count
            self.assertGreaterEqual(count,2);await asyncio.sleep(.025);self.assertEqual(bot.send_chat_action.await_count,count)
        bot.send_message_draft.assert_not_awaited()
    async def test_typing_error_is_best_effort(self):
        bot=type('Bot',(),{})();bot.send_message_draft=AsyncMock();bot.send_chat_action=AsyncMock(side_effect=RuntimeError('offline'))
        async with Thinking(bot,123,.01).show():await asyncio.sleep(.035)
        bot.send_chat_action.assert_awaited();bot.send_message_draft.assert_not_awaited()
    async def test_disabled(self):
        bot=type('Bot',(),{})()
        bot.send_message_draft=AsyncMock()
        async with Thinking(bot,123,.01).show(False): await asyncio.sleep(.02)
        bot.send_message_draft.assert_not_awaited()
    async def test_error_cleanup(self):
        bot=type('Bot',(),{})()
        bot.send_message_draft=AsyncMock()
        ui=Thinking(bot,123,.01)
        with self.assertRaises(ValueError):
            async with ui.show():
                await asyncio.sleep(.02)
                raise ValueError('actual job error')
        count=bot.send_message_draft.await_count
        await asyncio.sleep(.025)
        self.assertEqual(bot.send_message_draft.await_count,count)
        self.assertFalse(ui.gate.locked())
    async def test_missing_method(self):
        bot=type('Bot',(),{})()
        bot.send_chat_action=AsyncMock()
        async with Thinking(bot,123,.01).show(): await asyncio.sleep(.02)
        bot.send_chat_action.assert_awaited()
