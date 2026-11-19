import asyncio
import time
from unittest.mock import AsyncMock, Mock
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy.orm import sessionmaker
from app.core.config import Settings, settings
from app.db.session import _build_engine
from app.models.models import AuthRateBucket


def test_hosted_settings_reject_local_database_without_leaking_credentials():
    with pytest.raises(ValidationError) as error:
        Settings(_env_file=None, vercel=True, database_url='postgresql://postgres:secret@localhost/app')
    assert 'secret' not in str(error.value)
    config = Settings(_env_file=None, vercel=True, database_url='postgresql://postgres:secret@pooler.example:6543/app',
                      vercel_url='preview.example.vercel.app', frontend_origins='https://example.com,http://localhost:3000')
    assert config.secure_cookies
    assert not config.embedded_worker_enabled
    assert config.allowed_origins == {'https://preview.example.vercel.app', 'https://example.com'}


def test_database_is_lazy_and_connection_budget_is_bounded():
    engine = _build_engine('postgresql+psycopg2://unused:unused@invalid.example/unused')
    assert engine.pool.size() == settings.db_pool_size
    assert engine.pool.checkedout() == 0  # No connection attempt during import/build.
    engine.dispose()


def test_vercel_api_prefix_secure_cookie_and_no_embedded_jobs(db_session, monkeypatch):
    from index import app, api
    from app.db.session import get_db
    from app.main import Base, PaperWorker
    monkeypatch.setattr(settings, 'vercel', True)
    monkeypatch.setattr(settings, 'vercel_url', 'demo.vercel.app')
    monkeypatch.setattr(settings, 'paper_worker_enabled', True)
    setup = Mock(side_effect=AssertionError('Hosted requests must not perform schema DDL'))
    monkeypatch.setattr(Base.metadata, 'create_all', setup)
    run = AsyncMock()
    monkeypatch.setattr(PaperWorker, 'run', run)
    def override():
        yield db_session
    api.dependency_overrides[get_db] = override
    try:
        with TestClient(app, base_url='https://demo.vercel.app', headers={'Origin': 'https://demo.vercel.app'}) as client:
            assert client.get('/api/health').json()['paper_trading']['mode'] == 'external'
            assert client.get('/api/openapi.json').status_code == 200
            result = client.post('/api/auth/signup', json={'email': 'vercel@example.com', 'full_name': 'Hosted', 'password': 'practice123'})
            assert result.status_code == 200, result.text
            cookie = result.headers['set-cookie']
            assert 'Secure' in cookie and 'HttpOnly' in cookie and 'Path=/' in cookie
            assert client.get('/api/auth/me').status_code == 200
            assert client.post('/api/auth/login', content='email=bad', headers={'Content-Type': 'text/plain'}).status_code == 415
            assert client.post('/api/auth/logout', json={}).status_code == 403
            client.headers['X-CSRF-Token'] = result.json()['csrf_token']
            assert client.put('/api/watchlist/AAPL').json() == ['AAPL']
            assert client.post('/api/auth/logout', json={}).status_code == 200
            assert client.get('/api/auth/me').status_code == 401
        setup.assert_not_called()
        run.assert_not_awaited()
    finally:
        api.dependency_overrides.clear()


def test_login_limit_is_shared_by_independent_hosted_clients(db_session, monkeypatch):
    from index import app, api
    from app.db.session import get_db
    monkeypatch.setattr(settings, 'vercel', True)
    monkeypatch.setattr('app.services.login_throttle.time.time', lambda: 120000.0)
    def override():
        yield db_session
    api.dependency_overrides[get_db] = override
    try:
        body = {'email': 'unknown@example.com', 'password': 'incorrect'}
        for i in range(16):
            # Separate clients model separate API instances; only PostgreSQL state is shared.
            with TestClient(app, base_url='https://demo.vercel.app') as client:
                response = client.post('/api/auth/login', json=body, headers={'x-vercel-forwarded-for': '203.0.113.1'})
                assert response.status_code == (401 if i < 15 else 429)
        with TestClient(app, base_url='https://demo.vercel.app') as client:
            assert client.post('/api/auth/login', json=body, headers={'x-vercel-forwarded-for': '203.0.113.2'}).status_code == 401
        assert db_session.query(AuthRateBucket).count() == 2
    finally:
        api.dependency_overrides.clear()


def test_worker_probe_detects_stalls_and_shutdown(monkeypatch):
    from worker import healthy
    from app.services.paper_worker import PaperWorker
    worker = PaperWorker()
    assert healthy(worker, time.monotonic())
    worker.last_progress_monotonic = time.monotonic() - 1000
    assert not healthy(worker, time.monotonic())
    worker.last_progress_monotonic = time.monotonic()
    worker.stop()
    assert not healthy(worker, time.monotonic())


def test_standalone_worker_lifecycle_stops_cleanly(db_session, monkeypatch):
    import worker as daemon
    monkeypatch.setattr(daemon, 'engine', db_session.get_bind())
    stopped = []
    async def fake_run(self):
        await self.wake.wait()
        stopped.append(True)
    monkeypatch.setattr(daemon.PaperWorker, 'run', fake_run)
    with TestClient(daemon.app) as client:
        assert client.get('/health').status_code == 200
    assert stopped == [True]
