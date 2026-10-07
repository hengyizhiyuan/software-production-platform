"""Bounded request timing. Records numbers and route templates, never payloads.

Spans are inclusive; overlapping categories must not be summed. Uninstrumented
filesystem/external work remains unknown, never an invented zero.
"""
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from functools import wraps
import logging
from time import perf_counter
from uuid import uuid4

from sqlalchemy import event

_current = ContextVar('watt_request_performance', default=None)


@dataclass
class Observation:
    request_id: str = field(default_factory=lambda: str(uuid4()))
    elapsed: dict = field(default_factory=dict)
    counts: dict = field(default_factory=dict)

    def add(self, category, seconds):
        self.elapsed[category] = self.elapsed.get(category, 0) + seconds
        self.counts[category] = self.counts.get(category, 0) + 1

    def record(self, *, route, method, status, total, size):
        return {'request_id': self.request_id, 'endpoint': route, 'method': method,
            'status': status, 'total_ms': round(total * 1000, 2), 'response_bytes': size,
            'times_ms': {k: round(v * 1000, 2) for k,v in self.elapsed.items()},
            'counts': self.counts,
            'unmeasured': [k for k in ('model_provider','external_http','git','filesystem','subprocess',
                'projection','serialization') if k not in self.elapsed],
            'timing_semantics': 'inclusive spans; missing categories unknown; streaming total ends at last body'}


@contextmanager
def span(category):
    observation = _current.get()
    if observation is None:
        yield
        return
    start = perf_counter()
    try:
        yield
    finally:
        observation.add(category, perf_counter() - start)


def timed(category):
    def decorate(fn):
        @wraps(fn)
        def call(*args, **kwargs):
            with span(category):
                return fn(*args, **kwargs)
        return call
    return decorate


def observe_engine(engine):
    """A connection-local stack handles concurrent queries without SQL logging."""
    @event.listens_for(engine, 'before_cursor_execute')
    def before(connection, *_):
        connection.info.setdefault('watt_query_times', []).append((_current.get(), perf_counter()))

    def finish(connection, *_):
        stack = connection.info.get('watt_query_times', [])
        if stack:
            observation, start = stack.pop()
            if observation is not None:
                observation.add('db', perf_counter() - start)

    event.listen(engine, 'after_cursor_execute', finish)
    @event.listens_for(engine, 'handle_error')
    def failure(context):
        if context.connection is not None:
            finish(context.connection)


class PerformanceMiddleware:
    def __init__(self, app):
        self.app = app
        logger = logging.getLogger('spg.performance')
        logger.setLevel(logging.INFO)
        if not logger.handlers:
            logger.addHandler(logging.StreamHandler())

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http':
            return await self.app(scope, receive, send)
        observation = Observation()
        token = _current.set(observation)
        start = perf_counter()
        size, status = 0, 500
        async def measured_send(message):
            nonlocal size, status
            if message['type'] == 'http.response.start':
                status = message['status']
                # Header has no user text, secrets or entity identifiers.
                message = {**message, 'headers': [*message.get('headers', []),
                    (b'x-watt-request-id', observation.request_id.encode())]}
            elif message['type'] == 'http.response.body':
                size += len(message.get('body', b''))
            await send(message)
        try:
            await self.app(scope, receive, measured_send)
        finally:
            route = getattr(scope.get('route'), 'path', None) or 'UNMATCHED'
            import json
            logging.getLogger('spg.performance').info('请求性能 %s', json.dumps(observation.record(
                route=route, method=scope['method'], status=status,
                total=perf_counter()-start, size=size), ensure_ascii=False))
            _current.reset(token)


from fastapi.responses import JSONResponse


class TimedJSONResponse(JSONResponse):
    def render(self, content):
        with span('serialization'):
            return super().render(content)


@timed('subprocess')
def run_process(*args, **kwargs):
    import subprocess
    return subprocess.run(*args, **kwargs)


_projection_scope = ContextVar('watt_projection_scope', default=None)


def projection_scope(fn):
    """Share reads only within one explicitly read-only composition call.

    No cache survives its return; commands/authorization are never decorated.
    """
    @wraps(fn)
    def call(*args, **kwargs):
        if _projection_scope.get() is not None:
            return fn(*args, **kwargs)
        token = _projection_scope.set({})
        try:
            return fn(*args, **kwargs)
        finally:
            _projection_scope.reset(token)
    return call


def projection_memo(fn):
    @wraps(fn)
    def call(*args, **kwargs):
        cache = _projection_scope.get()
        if cache is None:
            return fn(*args, **kwargs)
        key = (fn, id(args[0]), repr(args[1:]), repr(sorted(kwargs.items())))
        if key not in cache:
            cache[key] = fn(*args, **kwargs)
        return cache[key]
    return call


def share_projection_rows(database, session, rows):
    cache = _projection_scope.get()
    if cache is not None:
        cache[('rows', id(database))] = rows


def bind_projection_rows(database, session, work_ids):
    cache = _projection_scope.get()
    rows = None if cache is None else cache.get(('rows', id(database)))
    if rows is None or not set(work_ids) <= {r['id'] for r in rows.get('product_works', [])}:
        return False
    session.info['watt_projection_rows'] = rows
    return True
