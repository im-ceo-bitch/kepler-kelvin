"""Test actual Python Bridge against JS backend via isolated loopback HTTP.
Requires Node 22 and a checkout of Business. No external services, no credentials.
"""
import argparse, json, subprocess, urllib.request
from pathlib import Path
from founder_jarvis import shared_business

def run(business):
    path=Path(business)/'Backend/IumrahBackend/tests/kelvin-http-fixture.mjs'
    proc=subprocess.Popen(['node',str(path.resolve())],stdout=subprocess.PIPE,text=True)
    original=shared_business.ORIGIN
    try:
        port=int(proc.stdout.readline().strip());origin=f'http://127.0.0.1:{port}';shared_business.ORIGIN=origin
        def admin(endpoint,data=None):
            req=urllib.request.Request(origin+'/api/admin/hotels/kelvin/'+endpoint,data=None if data is None else json.dumps(data).encode(),headers={'Content-Type':'application/json'})
            with urllib.request.urlopen(req,timeout=10) as response:return json.load(response)
        bridge=shared_business.Bridge(admin('pair',{})['token']);assert bridge.call('diagnostics')['protocol']==7
        bridge.call('records',{'action':'save','id':'integration-memory','kind':'decision','content':'Тестовая цель 20 поездок'})
        bridge.enqueue('integration-tg-001','Привет')
        admin('message',{'id':'integration-app-001','prompt':'Что помнишь?','voice':True})
        first=bridge.call('claim')['job'];assert first['id']=='integration-tg-001'
        data={'id':first['id'],'lease':first['lease'],'status':'done','answer':'Тестовый ответ'}
        assert bridge.finish(data)['ok'];assert bridge.finish(data)['replay']
        second=bridge.call('claim');assert second['job']['id']=='integration-app-001';assert second['job']['voice'];assert second['history'][0]['answer']=='Тестовый ответ';assert any(x['id']=='integration-memory' for x in second['typedMemory'])
        j=second['job'];assert bridge.finish({'id':j['id'],'lease':j['lease'],'status':'done','answer':'Тестовый голосовой ответ'})['ok']
        assert admin('turn',{'id':j['id']})['turn']['status']=='done';assert bridge.call('diagnostics')['queue']=={'done':2}
        bridge.call('autonomy',{'action':'publish','id':'kelvin-auto-2026-11-27-morning','kind':'morning','text':'Тестовый брифинг'})
        assert admin('insights')['insights'][0]['text']=='Тестовый брифинг'
        admin('revoke',{})
        try:bridge.call('diagnostics')
        except RuntimeError as e:assert 'HTTP 401' in str(e)
        else:raise AssertionError('Revoked token accepted')
        print('PASS: real loopback HTTP, pairing, shared memory, Telegram/app queue, exact completion replay, voice turn lookup, archive, revocation')
    finally:
        shared_business.ORIGIN=original;proc.terminate()
        try:proc.wait(timeout=5)
        except subprocess.TimeoutExpired:proc.kill();proc.wait()
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('business');run(p.parse_args().business)
