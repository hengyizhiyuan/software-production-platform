"""Single-owner prefill is explicit; a real login is still required."""
from fastapi import FastAPI
from fastapi.testclient import TestClient

from spg.api.authority import _valid_session, install_authority_boundary
from spg.config import Settings

TOKEN = 'prefill-test-operator-token-at-least-32-characters'


def client_for(settings):
    app = FastAPI()
    install_authority_boundary(app, database=None, settings=settings)
    return TestClient(app)


def test_prefill_default_does_not_disclose_token():
    client = client_for(Settings(auth_mode='required', operator_token=TOKEN))
    response = client.get('/auth/login-prefill')
    assert response.status_code == 200
    assert response.json() == {'token': None}
    assert response.headers['cache-control'] == 'no-store'
    assert TOKEN not in client.get('/login').text


def test_env_prefill_requires_explicit_login_and_uses_configured_token(tmp_path):
    env = tmp_path / '.env'
    env.write_text(f'SPG_OPERATOR_TOKEN={TOKEN}\nSPG_LOGIN_PREFILL_ENABLED=true\n')
    client = client_for(Settings(_env_file=env, auth_mode='required'))
    response = client.get('/auth/login-prefill')
    assert response.json() == {'token': TOKEN}
    assert response.headers['cache-control'] == 'no-store'
    assert 'set-cookie' not in response.headers
    assert client.get('/auth/session').status_code == 401
    assert client.post('/auth/session', json={'token': 'wrong'}).status_code == 401
    login = client.post('/auth/session', json=response.json())
    assert login.status_code == 200
    assert _valid_session(TOKEN, client.cookies.get('watt_session'))
    assert 'httponly' in login.headers['set-cookie'].lower()
    replacement = TOKEN + '-rotated'
    env.write_text(f'SPG_OPERATOR_TOKEN={replacement}\nSPG_LOGIN_PREFILL_ENABLED=true\n')
    updated = client_for(Settings(_env_file=env, auth_mode='required'))
    assert updated.get('/auth/login-prefill').json() == {'token': replacement}
    assert updated.post('/auth/session', json={'token': TOKEN}).status_code == 401
    assert updated.post('/auth/session', json={'token': replacement}).status_code == 200
