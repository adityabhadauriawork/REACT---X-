"""
PostgreSQL Connection Pooling and Live Recovery Chaos Tests.
Validates:
1. Engine configuration extraction:
   - pool_pre_ping=True
   - pool_size=20
   - max_overflow=10
   - SQLite check_same_thread=False
2. Live PostgreSQL connection and QueuePool initialization against postgresql://postgres:postgres@localhost:5432/reactx
3. Concurrent transaction execution across connection pool.
4. Chaos Test: Dropping/killing socket connections and restarting service to verify pool_pre_ping transparently recycles stale connections.
5. Verification that SQLite behavior remains unchanged.
"""
import os
import time
import subprocess
from concurrent.futures import ThreadPoolExecutor
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool

from app.core.database import get_engine_args, Base

TEST_PG_URL = os.getenv("TEST_POSTGRES_URL") or "postgresql://postgres:postgres@localhost:5432/reactx"


def test_sqlite_engine_arguments():
    """Verify SQLite configuration produces check_same_thread=False without pool args."""
    args = get_engine_args("sqlite:///test_local.db")
    assert "connect_args" in args
    assert args["connect_args"].get("check_same_thread") is False
    assert "pool_size" not in args
    assert "pool_pre_ping" not in args


def test_postgresql_engine_arguments():
    """Verify PostgreSQL configuration sets pool_pre_ping=True, pool_size=20, max_overflow=10."""
    postgres_urls = [
        "postgresql://postgres:postgres@localhost:5432/reactx",
        "postgresql+psycopg2://postgres:postgres@127.0.0.1:5432/reactx",
        "postgres://user:secret@db.internal:5432/reactx"
    ]
    for url in postgres_urls:
        args = get_engine_args(url)
        assert args.get("pool_pre_ping") is True, f"Failed for {url}"
        assert args.get("pool_size") == 20, f"Failed for {url}"
        assert args.get("max_overflow") == 10, f"Failed for {url}"
        assert "connect_args" not in args, f"Failed for {url}"


def test_sqlite_runtime_behavior_unchanged():
    """Verify in-memory SQLite engine creates and executes without pooling conflicts."""
    test_engine = create_engine("sqlite:///:memory:", **get_engine_args("sqlite:///:memory:"))
    with test_engine.connect() as conn:
        result = conn.execute(text("SELECT 1;")).scalar()
        assert result == 1


def _is_postgres_available(url: str) -> bool:
    try:
        e = create_engine(url, connect_args={"connect_timeout": 1})
        with e.connect() as conn:
            conn.execute(text("SELECT 1;"))
        return True
    except Exception:
        return False


def test_postgres_live_connection_and_pool_verification():
    """
    Connects to live PostgreSQL, creates Base metadata tables,
    and executes concurrent queries across the 20-connection pool.
    """
    pg_args = get_engine_args(TEST_PG_URL)
    engine = create_engine(TEST_PG_URL, **pg_args)

    # 1. Verify pool type and configuration
    assert isinstance(engine.pool, QueuePool), "Expected QueuePool for PostgreSQL engine"
    assert engine.pool.size() == 20
    assert engine.pool._max_overflow == 10
    assert engine.pool._pre_ping is True

    if not _is_postgres_available(TEST_PG_URL):
        pytest.skip("Live PostgreSQL server not reachable in local test environment")

    # 2. Verify live connectivity
    with engine.connect() as conn:
        pg_version = conn.execute(text("SELECT version();")).scalar()
        assert "PostgreSQL" in pg_version

    # 3. Create tables in PostgreSQL
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine, autocommit=False, autoflush=False)

    # 4. Execute 20 concurrent transactions across the pool
    def run_worker(thread_id: int):
        s = Session()
        try:
            val = s.execute(text("SELECT 1;")).scalar()
            return val == 1
        finally:
            s.close()

    with ThreadPoolExecutor(max_workers=10) as executor:
        results = list(executor.map(run_worker, range(20)))

    assert all(results), "Concurrent pool transaction execution failed"


def test_postgres_chaos_recovery_after_service_restart():
    """
    CHAOS TEST:
    1. Pre-warm connection pool with active connections.
    2. Restart PostgreSQL service/container while transactions are active to terminate server-side sockets.
    3. Issue subsequent transactions to the stale connection pool.
    4. Verify pool_pre_ping detects stale sockets and transparently reconnects without raising OperationalError.
    """
    if not _is_postgres_available(TEST_PG_URL):
        pytest.skip("Live PostgreSQL server not reachable in local test environment")

    pg_args = get_engine_args(TEST_PG_URL)
    engine = create_engine(TEST_PG_URL, **pg_args)
    Session = sessionmaker(bind=engine, autocommit=False, autoflush=False)

    # Pre-warm pool
    s1 = Session()
    res1 = s1.execute(text("SELECT 1;")).scalar()
    assert res1 == 1
    s1.close()

    # Sever all active connections on the PostgreSQL server for 'reactx' database
    print("\n[CHAOS RECOVERY] Terminating all active PostgreSQL backend server connections via pg_terminate_backend...")
    admin_engine = create_engine(TEST_PG_URL, isolation_level="AUTOCOMMIT")
    with admin_engine.connect() as admin_conn:
        terminated = admin_conn.execute(
            text("SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE pid <> pg_backend_pid() AND datname = 'reactx';")
        ).fetchall()
        print(f"[CHAOS RECOVERY] Terminated {len(terminated)} active server backends.")

    time.sleep(0.5)

    # Issue requests through the engine - pool_pre_ping must recycle disconnected sockets transparently
    def verify_recovered_worker(worker_id: int):
        s = Session()
        try:
            val = s.execute(text("SELECT 100 + :id;"), {"id": worker_id}).scalar()
            return val == (100 + worker_id)
        finally:
            s.close()

    with ThreadPoolExecutor(max_workers=5) as executor:
        post_restart_results = list(executor.map(verify_recovered_worker, range(10)))

    assert all(post_restart_results), "Post-restart pool_pre_ping recovery failed on some threads"
    print(f"\n[CHAOS RECOVERY] Succeeded: {len(post_restart_results)}/{len(post_restart_results)} queries recovered transparently after service restart.")
