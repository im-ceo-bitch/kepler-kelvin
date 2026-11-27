import asyncio
import unittest
from unittest.mock import AsyncMock
from founder_jarvis.thinking import Thinking

class ThinkingTests(unittest.IsolatedAsyncioTestCase):
    async def test_native_reuses_id_and_stops(self):
        bot=type('Bot',(),{})()
        bot.send_message_draft=AsyncMock()
        bot.send_chat_action=AsyncMock()
        ui=Thinking(bot,123,interval=.01)
        async with ui.show() as end:
            await asyncio.sleep(.035)
            await end()
            count=bot.send_message_draft.await_count
            self.assertGreaterEqual(count,2)
            self.assertEqual(len({c.kwargs['draft_id'] for c in bot.send_message_draft.await_args_list}),1)
            self.assertTrue(all(c.kwargs['text']=='' and c.kwargs['chat_id']==123 for c in bot.send_message_draft.await_args_list))
            await asyncio.sleep(.025)
            self.assertEqual(bot.send_message_draft.await_count,count)
        bot.send_chat_action.assert_not_awaited()
    async def test_fallback(self):
        bot=type('Bot',(),{})()
        bot.send_message_draft=AsyncMock(side_effect=RuntimeError('unsupported'))
        bot.send_chat_action=AsyncMock()
        async with Thinking(bot,123,.01).show(): await asyncio.sleep(.035)
        bot.send_message_draft.assert_awaited_once()
        self.assertGreaterEqual(bot.send_chat_action.await_count,1)
        self.assertEqual(bot.send_chat_action.await_args.kwargs['action'],'typing')
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
