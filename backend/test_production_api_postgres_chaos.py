"""
FastAPI HTTP API PostgreSQL Connection Drop & Chaos Recovery Test.
Simulates active HTTP clients making concurrent DB-backed API requests
while server-side database connections are killed.
"""
import os
import time
from concurrent.futures import ThreadPoolExecutor
import pytest
from sqlalchemy import create_engine, text
from fastapi.testclient import TestClient

from app.core.database import get_engine_args, engine, Base
from app.main import app

TEST_PG_URL = os.getenv("TEST_POSTGRES_URL") or "postgresql://postgres:postgres@localhost:5432/reactx"


def _is_postgres_available(url: str) -> bool:
    try:
        e = create_engine(url, connect_args={"connect_timeout": 1})
        with e.connect() as conn:
            conn.execute(text("SELECT 1;"))
        return True
    except Exception:
        return False


def test_api_postgres_chaos_recovery():
    if not _is_postgres_available(TEST_PG_URL):
        pytest.skip("Live PostgreSQL server not reachable in local test environment")

    with TestClient(app) as client:
        # 1. Warm up API endpoints
        r1 = client.get("/api/facilities")
        assert r1.status_code == 200

        r2 = client.get("/readiness")
        assert r2.status_code == 200

        # 2. Sever all connections from the PostgreSQL server
        print("\n[API CHAOS RECOVERY] Severing all active connections via pg_terminate_backend...")
        admin_engine = create_engine(TEST_PG_URL, isolation_level="AUTOCOMMIT")
        with admin_engine.connect() as admin_conn:
            terminated = admin_conn.execute(
                text("SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE pid <> pg_backend_pid() AND datname = 'reactx';")
            ).fetchall()
            print(f"[API CHAOS RECOVERY] Terminated {len(terminated)} active server backends.")

        time.sleep(0.5)

        # 3. Issue concurrent API requests across severed connection pool
        def call_api(i: int):
            endpoints = ["/api/facilities", "/readiness", "/api/system/status", "/api/thermal/sources"]
            ep = endpoints[i % len(endpoints)]
            resp = client.get(ep)
            return resp.status_code == 200

        with ThreadPoolExecutor(max_workers=5) as executor:
            results = list(executor.map(call_api, range(15)))

        assert all(results), "Some API requests failed to recover from severed PostgreSQL connections"
        print(f"[API CHAOS RECOVERY] Succeeded: {results.count(True)}/{len(results)} concurrent API calls recovered seamlessly.")
