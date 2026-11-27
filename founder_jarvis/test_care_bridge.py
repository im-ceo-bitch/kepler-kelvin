import unittest
from unittest.mock import Mock
from founder_jarvis.care_bridge import CareService

class FakeBridge:
    def __init__(self):self.calls=[];self.enabled=True;self.notice=None;self.error=None
    def call(self,path,b):
        assert path=='care';self.calls.append(b);action=b['action']
        if self.error==action:raise RuntimeError('test error')
        if action=='status':return {'enabled':self.enabled,'uncertain':0}
        if action=='claim':n=self.notice;self.notice=None;return {'notice':n}
        if action=='enable':self.enabled=True
        if action=='disable':self.enabled=False
        if action=='show':return {'mode':'human','messages':[{'role':'user','body':'Вопрос','delivery':'sent'}]}
        if action=='pending':return {'threads':[]}
        return {'ok':True}
class CareTests(unittest.TestCase):
    def setUp(self):
        self.bridge=FakeBridge();self.sender=Mock();self.service=CareService(self.bridge,'not-a-real-token',1,self.sender)
    def notice(self,delivery='sent'):
        self.bridge.notice={'id':1,'thread':'123','question':'Цена?','answer':'Уточните даты','delivery':delivery,'mode':'auto'}
    def test_notice_only_to_owner_and_buttons(self):
        self.notice();self.service.poll();args=self.sender.call_args.args;self.assertEqual(args[1],'sendMessage');self.assertEqual(args[2]['chat_id'],1);self.assertIn('Цена?',args[2]['text']);self.assertIn('Уточните даты',args[2]['text']);self.assertTrue(args[2]['protect_content']);self.assertEqual(args[2]['reply_markup']['inline_keyboard'][0][0]['callback_data'],'care:take:123');self.assertEqual(self.bridge.calls[-1],{'action':'ack','id':1,'state':'sent'});self.service.poll();self.assertEqual(self.sender.call_count,1)
    def test_unknown_delivery_not_asserted_successful(self):
        self.notice('uncertain');self.service.poll();self.assertIn('не подтверждена',self.sender.call_args.args[2]['text']);self.assertNotIn('Ответ: Уточните',self.sender.call_args.args[2]['text'])
    def test_failure_ack_uncertain(self):
        self.notice();self.sender.side_effect=RuntimeError('network');
        with self.assertRaises(RuntimeError):self.service.poll()
        self.assertEqual(self.bridge.calls[-1],{'action':'ack','id':1,'state':'uncertain'});self.service.poll();self.assertEqual(self.sender.call_count,1)
    def test_disabled_never_claims(self):
        self.bridge.enabled=False;self.notice();self.service.poll();self.sender.assert_not_called();self.assertEqual(self.bridge.calls,[{'action':'status'}])
    def test_explicit_owner_controls(self):
        self.assertIn('приостановлены',self.service.owner_command('take 123'));self.assertEqual(self.bridge.calls[-1],{'action':'take','thread':'123'});self.service.owner_command('resume 123');self.assertEqual(self.bridge.calls[-1],{'action':'resume','thread':'123'});self.assertIn('Вопрос',self.service.owner_command('show 123'))
    def test_reply_stable_for_duplicate_telegram_event(self):
        self.service.owner_command('reply 123 Добрый день',event=10);a=self.bridge.calls[-1];self.service.owner_command('reply 123 Добрый день',event=10);self.assertEqual(self.bridge.calls[-1],a);self.service.owner_command('reply 123 Добрый день',event=11);self.assertNotEqual(self.bridge.calls[-1]['requestId'],a['requestId']);self.sender.assert_not_called()
    def test_no_manual_send_without_event(self):
        with self.assertRaises(RuntimeError):self.service.owner_command('reply 123 hello')
        self.assertEqual(self.bridge.calls,[])
    def test_invalid_scope_or_unpaired(self):
        for command in ('reply 123x hello','take ../../../','ig media','publish 123'):
            with self.assertRaises(RuntimeError):self.service.owner_command(command,event=1)
        self.assertEqual(self.bridge.calls,[])
        with self.assertRaises(RuntimeError):CareService(None,'token',1).owner_command('enable')
    def test_ack_failure_no_retry_by_adapter(self):
        self.notice();self.bridge.error='ack';
        with self.assertRaises(RuntimeError):self.service.poll()
        self.bridge.error=None;self.service.poll();self.assertEqual(self.sender.call_count,1)
    def test_enable_disable_no_customer_token_or_poller(self):
        self.service.owner_command('disable');self.assertFalse(self.service.enabled);self.service.owner_command('enable');self.assertTrue(self.service.enabled);self.assertEqual({x['action'] for x in self.bridge.calls},{'status','enable','disable'});self.sender.assert_not_called()
