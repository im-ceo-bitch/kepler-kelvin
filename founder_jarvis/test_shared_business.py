import asyncio, datetime as dt, json, unittest
from founder_jarvis import shared_business as b
class MockResponse:
    def __enter__(self):return self
    def __exit__(self,*args):pass
    def read(self,*args):return b'{"ok":true}'
class Opener:
    def __init__(self):self.requests=[]
    def open(self,req,timeout):self.requests.append(req);return MockResponse()
class BridgeTests(unittest.TestCase):
    def test_token_validation_and_fixed_https_origin(self):
        with self.assertRaises(ValueError):b.Bridge('bad')
        op=Opener();bridge=b.Bridge('a'*64,op);bridge.enqueue('id-123456','привет',True)
        req=op.requests[0];self.assertEqual(req.full_url,b.ORIGIN+'/api/internal/kelvin/message');self.assertEqual(req.get_header('Authorization'),'Bearer '+'a'*64);self.assertEqual(json.loads(req.data)['voice'],True)
        with self.assertRaises(ValueError):bridge.call('https://wrong')
    def test_daily_deterministic_and_no_before_eight(self):
        op=Opener();bridge=b.Bridge('a'*64,op);bridge.daily(dt.datetime(2026,11,27,7));self.assertFalse(op.requests)
        bridge.daily(dt.datetime(2026,11,27,8));bridge.daily(dt.datetime(2026,11,27,19));self.assertEqual(json.loads(op.requests[0].data),json.loads(op.requests[1].data))
    def test_context_contains_both_channels_and_notes(self):
        p={'job':{'prompt':'продолжи'},'history':[{'prompt':'из приложения','answer':'ok','source':'app','status':'done'},{'prompt':'из Telegram','answer':'ok','source':'telegram','status':'done'}],'snapshot':{'asOf':'today'},'memory':[{'content':'note'}]}
        prompt,history=b.answer_context(p,['local']);self.assertIn('today',prompt);self.assertIn('продолжи',prompt);self.assertEqual(history[1]['user'],'из приложения');self.assertEqual(history[2]['user'],'из Telegram');self.assertEqual(history[0]['shared_owner_notes'],['note'])
class LoopTests(unittest.IsolatedAsyncioTestCase):
    async def test_persist_before_notify(self):
        calls=[]; stop=asyncio.Event()
        class Fake:
            def daily(self,*a):pass
            def call(self,action,data=None):
                calls.append(action)
                if action=='claim':return {'job':{'id':'test-id','source':'telegram','voice':True,'lease':'test','prompt':'Привет'},'history':[],'memory':[],'typedMemory':[],'snapshot':{}}
                if action=='finish':self.data=data
                return {'ok':True}
        fake=Fake()
        async def notify(answer,voice):
            self.assertEqual(fake.data['answer'],'Ответ');self.assertTrue(voice);self.assertIn('finish',calls);stop.set()
        await asyncio.wait_for(b.loop(fake,stop,lambda p,h:'Ответ',notify,lambda:[],asyncio.Lock()),3)
        self.assertEqual(fake.data['status'],'done')
