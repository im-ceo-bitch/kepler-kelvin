"""Owner-side adapter to canonical iumrah Telegram Care. Never polls a client token."""
from __future__ import annotations
import logging
import re
import threading
import uuid
from founder_jarvis import business, integrations

log=logging.getLogger('kelvin.care')
class CareService:
    def __init__(self,bridge,token,owner,send=None):
        self.bridge=bridge;self.token=token;self.owner=owner;self.sender=send or business.tg
        self.halt=threading.Event();self.thread=None;self.last='не проверен';self.enabled=False
        self.guard=threading.RLock()
    def call(self,action,**data):
        if not self.bridge:raise RuntimeError('Сначала подключи Mac к iumrah Business.')
        return self.bridge.call('care',{'action':action,**data})
    def status(self):
        return 'Telegram Care: '+self.last+'; Instagram/Facebook отключены.'
    def refresh(self):
        r=self.call('status');self.enabled=r.get('enabled') is True
        self.last=('подключён' if self.enabled else 'интеграция выключена')+f"; неподтверждённых уведомлений: {r.get('uncertain',0)}"
        if r.get('occupied'):self.last='назначен другому владельцу'
        return r
    def start(self):
        if self.bridge:
            self.thread=threading.Thread(target=self.loop,daemon=True,name='kelvin-care');self.thread.start()
    def stop(self):self.halt.set()
    def poll(self):
        with self.guard:
            if not self.refresh().get('enabled'):return
            n=self.call('claim').get('notice')
            if not n:return
            thread=str(n['thread']);ident=n['id']
            if not re.fullmatch(r'\d{1,16}',thread) or not isinstance(ident,int):raise RuntimeError('Invalid Care notice')
            delivery=n.get('delivery')
            answer=('Ответ: '+str(n['answer']) if delivery=='sent' else 'Доставка не подтверждена. Проверь переписку; автоматически не повторяю.' if delivery=='uncertain' else 'Автоответ не подтверждён или диалог ведёт сотрудник.')
            text=integrations.redact('iumrah Care · Telegram\nКлиент: '+str(n['question'])+'\n'+answer+'\nДиалог: '+('ручной' if n.get('mode')=='human' else 'авто'))
            state='uncertain'
            try:
                self.sender(self.token,'sendMessage',{'chat_id':self.owner,'text':text,'protect_content':True,'disable_web_page_preview':True,'reply_markup':{'inline_keyboard':[[{'text':'Взять общение','callback_data':'care:take:'+thread},{'text':'Продолжай сам','callback_data':'care:resume:'+thread}],[{'text':'Переписка','callback_data':'care:show:'+thread}]]}})
                state='sent'
            finally:
                self.call('ack',id=ident,state=state)
    def loop(self):
        while not self.halt.is_set():
            try:self.poll()
            except Exception as e:
                self.last='связь временно недоступна';log.warning('Care bridge: %s',type(e).__name__)
            self.halt.wait(20 if self.enabled else 60)
    def owner_command(self,arg,event=None):
        with self.guard:
            parts=arg.split(maxsplit=2);cmd=parts[0] if parts else 'status'
            if cmd=='status':
                self.refresh();return self.status()+'\n/biz enable — подключить Kelvin к действующему Care\n/biz disable — отключить Kelvin (вернуть прежний Care)\n/biz pending | take ID | resume ID | show ID | reply ID текст'
            if cmd in ('enable','disable'):
                self.call(cmd);self.refresh();return 'Kelvin подключён. Старые сообщения не рассылаются.' if cmd=='enable' else 'Kelvin отключён. Прежняя логика Care сохранена.'
            if cmd=='pending':
                r=self.call('pending');return '\n'.join(f"{x['thread']} · {x.get('preview','')[:150]}" for x in r.get('threads',[])) or 'Нет диалогов в ручном режиме.'
            if len(parts)<2 or not re.fullmatch(r'\d{1,16}',parts[1]):raise RuntimeError('Укажи ID диалога из уведомления.')
            thread=parts[1]
            if cmd in ('take','resume'):
                self.call(cmd,thread=thread);return 'Диалог передан тебе. Автоответы приостановлены.\nОтветить: /biz reply '+thread+' текст' if cmd=='take' else 'Автоответы для новых сообщений возобновлены.'
            if cmd=='show':
                r=self.call(cmd,thread=thread);return 'Диалог '+thread+' · '+r['mode']+'\n'+'\n'.join(('Клиент' if x['role']=='user' else 'Care' if x['role']=='auto' else 'Сотрудник')+': '+x['body']+(' [доставка не подтверждена]' if x.get('delivery')!='sent' else '') for x in r['messages'])+'\nОтветить: /biz reply '+thread+' текст'
            if cmd=='reply' and len(parts)==3 and 0<len(parts[2].strip())<=1000:
                if event is None:raise RuntimeError('Нет идентификатора команды; отправка остановлена.')
                key=str(uuid.uuid5(uuid.NAMESPACE_URL,f'kelvin-care:{self.owner}:{event}:{thread}'))
                try:self.call('reply',thread=thread,text=parts[2],requestId=key)
                except RuntimeError as e:raise RuntimeError('Ответ не подтверждён. Проверь переписку перед повтором. '+str(e)) from None
                return 'Ответ отправлен. Диалог остаётся в ручном режиме.'
            raise RuntimeError('Неизвестная команда /biz. Используй /biz status.')
