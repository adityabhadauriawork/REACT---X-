"""
REACT-X Dedicated Satellite Ingestion Worker
=============================================
Runs standalone background polling for NASA FIRMS, STAC catalog scans,
and historical thermal ingestion without exposing web API routes.

Ensures that in a horizontally scaled API deployment (e.g. 5 API replicas),
exactly ONE dedicated worker process polls external feeds.
"""

import sys
import time
import signal
import logging
from app.core.config import settings
from app.core.database import engine, Base, SessionLocal
from app.core.migrations import run_auto_migrations
from app.services.site.site_service import site_service
from app.services.storage.repository import storage_repository
from app.services.satellite.industrial_context_service import industrial_context_service
from app.services.satellite.fingerprint_engine import fingerprint_engine
from app.services.industrial.telemetry_service import telemetry_service
from app.services.vision.vision_pipeline_service import vision_pipeline_service
from app.services.satellite.firms_ingestion_service import firms_ingestion_service

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [REACT-X WORKER] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("reactx.worker")

running = True

def handle_shutdown(signum, frame):
    global running
    logger.info(f"Received signal {signum}. Initiating graceful worker shutdown...")
    running = False
    firms_ingestion_service.stop_background_polling()
    logger.info("Worker background polling stopped safely.")
    sys.exit(0)

def main():
    signal.signal(signal.SIGINT, handle_shutdown)
    signal.signal(signal.SIGTERM, handle_shutdown)

    logger.info("Starting REACT-X Dedicated Ingestion Worker...")
    logger.info(f"Database: {settings.DATABASE_URL.split('@')[-1] if '@' in settings.DATABASE_URL else settings.DATABASE_URL}")
    logger.info(f"FIRMS Polling Interval: {settings.FIRMS_POLL_INTERVAL_MINUTES}m")
    logger.info(f"FIRMS Default Bounding Box: {settings.FIRMS_DEFAULT_BBOX}")

    # Ensure DB schema is ready
    Base.metadata.create_all(bind=engine)
    run_auto_migrations(engine, Base)

    # Seed initial context if empty
    db = SessionLocal()
    try:
        site_service.load_seed_data_if_empty(db)
        storage_repository.seed_default_operating_limits(db)
        industrial_context_service.seed_facilities_if_empty(db)
        fingerprint_engine.seed_initial_fingerprints_if_empty(db)
        telemetry_service.seed_initial_metadata(db)
        vision_pipeline_service.seed_initial_metadata(db)
    finally:
        db.close()

    # Start background polling
    if not settings.NASA_FIRMS_MAP_KEY:
        logger.warning("NASA_FIRMS_MAP_KEY is empty. Real-time NASA FIRMS polling will be idle until key is provided.")
    
    firms_ingestion_service.start_background_polling()
    logger.info("Background FIRMS ingestion loop active. Worker heartbeat running.")

    heartbeat_count = 0
    while running:
        time.sleep(30)
        heartbeat_count += 1
        if heartbeat_count % 10 == 0:  # Every 5 minutes
            logger.info("Worker heartbeat: active and monitoring satellite feeds.")

if __name__ == "__main__":
    main()
