"""
Unit and behavior tests for single-worker FIRMS background polling guard.
Validates:
- ENABLE_BACKGROUND_POLL flag enforcement
- Preventing multiple API workers from starting background polling threads
- Standalone poller mode override
"""
import pytest
from app.core.config import settings
from app.services.satellite.firms_ingestion_service import FIRMSIngestionService


def test_background_polling_disabled_by_flag():
    """Verify that when ENABLE_BACKGROUND_POLL is False, start_background_polling does not start."""
    service = FIRMSIngestionService()
    original_flag = settings.ENABLE_BACKGROUND_POLL
    try:
        settings.ENABLE_BACKGROUND_POLL = False
        started = service.start_background_polling()
        assert started is False
        assert service.status.is_polling_active is False
    finally:
        settings.ENABLE_BACKGROUND_POLL = original_flag


def test_background_polling_force_override():
    """Verify that force=True overrides settings flag for dedicated CLI worker processes."""
    service = FIRMSIngestionService()
    original_flag = settings.ENABLE_BACKGROUND_POLL
    try:
        settings.ENABLE_BACKGROUND_POLL = False
        started = service.start_background_polling(force=True)
        assert started is True
        assert service.status.is_polling_active is True
        # Clean up
        service.stop_background_polling()
        assert service.status.is_polling_active is False
    finally:
        settings.ENABLE_BACKGROUND_POLL = original_flag


def test_multi_worker_simulation_idempotent():
    """
    Simulates 4 worker processes initializing.
    When ENABLE_BACKGROUND_POLL=False, none of the 4 API workers spawn a background loop.
    """
    workers = [FIRMSIngestionService() for _ in range(4)]
    original_flag = settings.ENABLE_BACKGROUND_POLL
    try:
        settings.ENABLE_BACKGROUND_POLL = False
        results = [w.start_background_polling() for w in workers]
        assert results == [False, False, False, False]
        assert all(not w.status.is_polling_active for w in workers)
    finally:
        settings.ENABLE_BACKGROUND_POLL = original_flag
