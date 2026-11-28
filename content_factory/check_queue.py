"""Exercise an isolated Business v7 worker and Kelvin with a synthetic owner."""
import argparse
import asyncio
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time
import urllib.request

from founder_jarvis import advisor, shared_business


async def test_queue(origin, workspace):
    def admin(path, data):
        req = urllib.request.Request(origin + '/api/admin/hotels/kelvin/' + path,
              data=json.dumps(data).encode(), headers={'Content-Type': 'application/json'})
        with urllib.request.urlopen(req, timeout=10) as response:
            return json.load(response)

    bridge = shared_business.Bridge(admin('pair', {})['token'])
    assert bridge.call('diagnostics')['protocol'] == 7
    bridge.enqueue('foundation-probe-001', 'Ответь только словом сапфир.')
    bridge.enqueue('foundation-probe-002', 'Какое слово было в предыдущем ответе? Ответь тем же словом.')
    stop = asyncio.Event()
    delivered = []

    async def record(answer, voice):
        delivered.append('сапфир' in answer.lower())
        if len(delivered) == 2:
            stop.set()

    start = time.monotonic()
    await asyncio.wait_for(shared_business.loop(bridge, stop,
        lambda prompt, history: advisor.respond(prompt, history, workspace),
        record, lambda: [], asyncio.Lock(), auto_daily=False), timeout=420)
    final = bridge.call('diagnostics')['queue']
    result = {'queue':final,'reply_matched':delivered,'seconds':round(time.monotonic()-start,2),
              'transport':'loopback HTTP', 'delivery':'local callback'}
    print(json.dumps(result), flush=True)
    if final != {'done':2} or delivered != [True,True]:
        raise SystemExit('Queue or dialogue assertion failed')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('business', type=Path)
    args = parser.parse_args()
    fixture = args.business.resolve()/'Backend/IumrahBackend/tests/kelvin-http-fixture.mjs'
    if not fixture.is_file():
        raise SystemExit('Missing local Business test fixture')
    # The worker and the bridge communicate exclusively through the localhost fixture.
    old_origin = shared_business.ORIGIN
    with tempfile.TemporaryDirectory() as tmp:
        os.environ['KELVIN_PERSONA_ROOT'] = str(Path(tmp)/'empty-persona')
        with subprocess.Popen(['node', str(fixture)], stdout=subprocess.PIPE, text=True) as server:
            try:
                port = int(server.stdout.readline())
                shared_business.ORIGIN = 'http://127.0.0.1:' + str(port)
                asyncio.run(test_queue(shared_business.ORIGIN, Path(tmp)))
            finally:
                shared_business.ORIGIN = old_origin
                server.terminate()

if __name__ == '__main__':
    main()
