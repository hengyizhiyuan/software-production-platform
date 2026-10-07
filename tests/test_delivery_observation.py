"""Delivery observation truth boundaries; no new publishing authority."""
import asyncio
from hashlib import sha256
from io import BytesIO
from types import SimpleNamespace
from zipfile import ZipFile
import pytest
from spg.application.delivery_observation import classify_delivery, archive_inventory
from spg.api.delivery_observation import DeliveryObservationMiddleware

@pytest.mark.parametrize('expected,selected,response,result',[
    ({'revision':'a'},{'revision':'a'},None,'PASS'),
    ({'revision':'old'},{'revision':'old'},None,'PASS'),
    ({'revision':'new'},{'revision':'old'},None,'OBSERVED_DELIVERY_DIVERGENCE'),
    ({'revision':'a','manifest_id':'x'},{'revision':'a','manifest_id':'y'},None,'OBSERVED_DELIVERY_DIVERGENCE'),
    ({},{},None,'UNAVAILABLE'),
    ({'revision':'a'},None,None,'UNRESOLVED'),
    ({'revision':'a'},{'revision':'a'},{'complete':False,'http_status':200},'NOT_SERVED'),
    ({'revision':'a'},{'revision':'a'},{'complete':True,'http_status':409},'NOT_SERVED'),
    ({'revision':'a','payload_sha256':'expected'},{'revision':'a'},{'complete':True,'http_status':200,'sha256':'other'},'OBSERVED_DELIVERY_DIVERGENCE'),
])
def test_action_specific_classification(expected,selected,response,result):
    assert classify_delivery(expected,selected,response)==result


def test_inventory_uses_canonical_hash_without_reopening_file_bytes(monkeypatch):
    data=BytesIO()
    with ZipFile(data,'w') as z:z.writestr('source/index.html',b'<h1>Real bytes</h1>')
    canonical=SimpleNamespace(path='index.html',size_bytes=19,sha256='canonical')
    monkeypatch.setattr(ZipFile,'read',lambda *a:pytest.fail('inventory must not decompress or hash blobs'))
    inventory=archive_inventory(data.getvalue(),[canonical],True)
    assert inventory['file_count']==1 and inventory['files'][0]['sha256']=='canonical'
    assert 'data' not in inventory


@pytest.mark.parametrize('broken',[False,True])
def test_actual_asgi_bytes_and_failed_send_never_prove_client_receipt(broken):
    records=[]
    observation=SimpleNamespace(data={'action_id':'server-action'},finish=records.append)
    async def app(scope,receive,send):
        scope['state']={'delivery_observation':observation}
        await send({'type':'http.response.start','status':200,'headers':[(b'content-type',b'application/octet-stream'),(b'content-disposition',b"attachment; filename*=UTF-8''%E4%BA%A4%E4%BB%98.txt")]})
        await send({'type':'http.response.body','body':b'first','more_body':True})
        await send({'type':'http.response.body','body':b'last','more_body':False})
    messages=[]
    async def send(message):
        if broken and message.get('body')==b'last':raise ConnectionError('closed')
        messages.append(message)
    async def receive():return {'type':'http.disconnect'}
    coroutine=DeliveryObservationMiddleware(app)({'type':'http','state':{}},receive,send)
    if broken:
        with pytest.raises(ConnectionError):asyncio.run(coroutine)
    else:asyncio.run(coroutine)
    fact=records[0]
    assert fact['complete'] is (not broken)
    assert fact['byte_size']==(5 if broken else 9)
    assert fact['sha256']==sha256(b'first' if broken else b'firstlast').hexdigest()
    assert fact['returned_filename']=='交付.txt'
    assert fact['client_received']==fact['client_saved']=='UNAVAILABLE'
    assert (b'x-watt-delivery-action-id',b'server-action') in messages[0]['headers']


def test_http_failure_reason_is_bounded_and_credentials_redacted():
    import json
    records=[]
    observation=SimpleNamespace(data={'action_id':'action'},finish=records.append)
    payload=json.dumps({'code':'PROVIDER_UNAVAILABLE','message':'provider token rejected Bearer private-credential password=private-password'}).encode()
    async def app(scope,receive,send):
        scope['state']={'delivery_observation':observation}
        await send({'type':'http.response.start','status':503,'headers':[(b'content-type',b'application/json')]})
        await send({'type':'http.response.body','body':payload,'more_body':False})
    async def send(message):pass
    async def receive():return {'type':'http.disconnect'}
    asyncio.run(DeliveryObservationMiddleware(app)({'type':'http'},receive,send))
    fact=records[0]
    assert fact['complete'] and fact['http_status']==503
    assert fact['sha256']==sha256(payload).hexdigest()
    assert fact['error_code']=='PROVIDER_UNAVAILABLE'
    assert 'private-credential' not in fact['error_summary'] and 'private-password' not in fact['error_summary']
