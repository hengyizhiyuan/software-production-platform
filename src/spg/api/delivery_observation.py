"""Observe only routed delivery responses; ASGI send is not client receipt."""
import json
import re
from hashlib import sha256
from urllib.parse import unquote
from email.message import Message
from starlette.concurrency import run_in_threadpool

class DeliveryObservationMiddleware:
    def __init__(self,app):self.app=app
    async def __call__(self,scope,receive,send):
        if scope['type']!='http':return await self.app(scope,receive,send)
        digest=sha256();size=0;status=None;headers={};complete=False;failure=None;error_body=bytearray()
        async def observed_send(message):
            nonlocal size,status,headers,complete
            observation=scope.get('state',{}).get('delivery_observation')
            if message['type']=='http.response.start':
                status=message['status'];headers={k.decode().lower():v.decode('latin1') for k,v in message.get('headers',[])}
                if observation:
                    message={**message,'headers':[*message.get('headers',[]),
                        (b'x-watt-delivery-action-id',observation.data['action_id'].encode())]}
            await send(message)
            if message['type']=='http.response.body' and observation:
                body=message.get('body',b'');digest.update(body);size+=len(body)
                if status>=400 and len(error_body)<4096: error_body.extend(body[:4096-len(error_body)])
                if not message.get('more_body',False):complete=True
        try:
            await self.app(scope,receive,observed_send)
        except BaseException as error:
            failure=type(error).__name__;raise
        finally:
            observation=scope.get('state',{}).get('delivery_observation')
            if observation:
                disposition=headers.get('content-disposition');filename=None
                if disposition:
                    m=Message();m['content-disposition']=disposition
                    filename=m.get_filename()
                    if isinstance(filename,tuple):filename=filename[-1]
                    filename=unquote(filename) if filename else None
                error_code=None;error_summary=None
                if error_body:
                    try:
                        parsed=json.loads(error_body)
                        code=parsed.get('code')
                        from spg.evaluation.production_trace import safe
                        reason=parsed.get('message')
                        if isinstance(reason,str):error_summary=safe(reason)[:512]
                        if isinstance(code,str) and re.fullmatch('[A-Z0-9_]{1,100}',code): error_code=code
                    except (ValueError,AttributeError):pass
                await run_in_threadpool(observation.finish,{'http_status':status,
                    'content_type':headers.get('content-type'),'content_disposition':disposition,
                    'returned_filename':filename,'byte_size':size,'sha256':digest.hexdigest(),
                    'complete':complete and failure is None,'failure':failure,'error_code':error_code,'error_summary':error_summary,
                    'completion_basis':'ASGI_SEND_COMPLETED' if complete and failure is None else 'INCOMPLETE_ASGI_SEND',
                    'client_received':'UNAVAILABLE','client_saved':'UNAVAILABLE'})
