import os
import io
import csv
import time
import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional, Tuple
import httpx
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import SessionLocal
from app.services.satellite.firms_service import firms_service
from app.schemas.thermal import CanonicalThermalEvent, FIRMSIngestSummaryResponse

logger = logging.getLogger("sih26162.firms_ingestion")
logging.basicConfig(level=logging.INFO)

class FIRMSFeedStatus:
    def __init__(self):
        self.last_poll_timestamp: Optional[datetime] = None
        self.last_successful_poll_timestamp: Optional[datetime] = None
        self.last_successful_acquisition_timestamp: Optional[datetime] = None
        self.last_error: Optional[str] = None
        self.last_error_timestamp: Optional[datetime] = None
        self.total_polls_count: int = 0
        self.successful_polls_count: int = 0
        self.failed_polls_count: int = 0
        self.records_received_total: int = 0
        self.records_persisted_total: int = 0
        self.duplicates_skipped_total: int = 0
        self.records_rejected_total: int = 0
        self.last_ingestion_summary: Optional[Dict[str, Any]] = None
        self.is_polling_active: bool = False
        self.configured_sources: List[str] = settings.FIRMS_SOURCE_CONSTELLATIONS

    def to_dict(self) -> Dict[str, Any]:
        has_key = bool(settings.NASA_FIRMS_MAP_KEY and len(settings.NASA_FIRMS_MAP_KEY) >= 10)
        
        health_status = "HEALTHY"
        if not has_key:
            health_status = "NO_KEY_CONFIGURED"
        elif self.last_error and (not self.last_successful_poll_timestamp or self.last_error_timestamp > self.last_successful_poll_timestamp):
            health_status = "DEGRADED"

        return {
            "api_health_status": health_status,
            "has_configured_api_key": has_key,
            "configured_sources": self.configured_sources,
            "poll_interval_minutes": settings.FIRMS_POLL_INTERVAL_MINUTES,
            "default_bbox": settings.FIRMS_DEFAULT_BBOX,
            "last_poll_timestamp": self.last_poll_timestamp.isoformat() if self.last_poll_timestamp else None,
            "last_successful_poll_timestamp": self.last_successful_poll_timestamp.isoformat() if self.last_successful_poll_timestamp else None,
            "last_successful_acquisition_timestamp": self.last_successful_acquisition_timestamp.isoformat() if self.last_successful_acquisition_timestamp else None,
            "total_polls_count": self.total_polls_count,
            "successful_polls_count": self.successful_polls_count,
            "failed_polls_count": self.failed_polls_count,
            "records_received_total": self.records_received_total,
            "records_persisted_total": self.records_persisted_total,
            "duplicates_skipped_total": self.duplicates_skipped_total,
            "records_rejected_total": self.records_rejected_total,
            "last_error": self.last_error,
            "last_error_timestamp": self.last_error_timestamp.isoformat() if self.last_error_timestamp else None,
            "last_ingestion_summary": self.last_ingestion_summary,
            "is_polling_active": self.is_polling_active
        }

class FIRMSIngestionService:
    """
    Production Ingestion Pipeline for NASA FIRMS REST API.
    Provides robust HTTP fetching, exponential backoff, rate limit handling,
    CSV/JSON parsing, deterministic deduplication, database persistence,
    and live status reporting.
    """

    def __init__(self):
        self.status = FIRMSFeedStatus()
        self._background_task: Optional[asyncio.Task] = None
        self._client: Optional[httpx.AsyncClient] = None

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(settings.FIRMS_TIMEOUT_SEC, connect=5.0),
                headers={"User-Agent": "SIH26162-REACT-X-ThermalIntelligence/2.0.0"}
            )
        return self._client

    # =========================================================================
    # 1. URL CONSTRUCTION & SOURCE PARSING
    # =========================================================================

    def build_firms_url(
        self,
        source_constellation: str,
        bbox: Optional[str] = None,
        days: int = 1
    ) -> str:
        """
        Construct standard NASA FIRMS Area CSV API URL:
        https://firms.modaps.eosdis.nasa.gov/api/area/csv/[MAP_KEY]/[SOURCE]/[BBOX]/[DAYS]
        """
        map_key = settings.NASA_FIRMS_MAP_KEY or "DEMO_KEY"
        target_bbox = bbox or settings.FIRMS_DEFAULT_BBOX
        base_url = settings.NASA_FIRMS_BASE_URL.rstrip("/")
        return f"{base_url}/{map_key}/{source_constellation}/{target_bbox}/{days}"

    def parse_firms_csv(self, csv_text: str, source_constellation: str) -> List[Dict[str, Any]]:
        """
        Parse raw NASA FIRMS CSV response into structured dictionary records.
        Handles both VIIRS NRT and MODIS header schemas.
        """
        if not csv_text or "latitude" not in csv_text.lower():
            # Check for error responses from NASA API
            if "invalid map_key" in csv_text.lower():
                raise ValueError("NASA FIRMS API rejected credentials: Invalid MAP_KEY.")
            if "no data" in csv_text.lower() or len(csv_text.strip()) == 0:
                return []
            if "error" in csv_text.lower():
                raise ValueError(f"NASA FIRMS API Error: {csv_text.strip()[:200]}")
            return []

        f = io.StringIO(csv_text.strip())
        reader = csv.DictReader(f)
        records = []

        for row in reader:
            if not row or not row.get("latitude"):
                continue
            
            clean_row = dict(row)
            # Attach source constellation context
            clean_row["_source_constellation"] = source_constellation
            records.append(clean_row)

        return records

    # =========================================================================
    # 2. RESILIENT FETCH WITH EXPONENTIAL BACKOFF & RETRIES
    # =========================================================================

    async def fetch_source_records(
        self,
        source_constellation: str,
        bbox: Optional[str] = None,
        days: int = 1
    ) -> List[Dict[str, Any]]:
        """
        Fetch NASA FIRMS thermal anomaly observations with retries and exponential backoff.
        """
        if not settings.NASA_FIRMS_MAP_KEY:
            logger.info(f"NASA_FIRMS_MAP_KEY is empty. Skipping live HTTP request for {source_constellation}.")
            return []

        url = self.build_firms_url(source_constellation, bbox=bbox, days=days)
        client = self._get_client()
        
        retries = settings.FIRMS_MAX_RETRIES
        delay = 1.0

        for attempt in range(1, retries + 1):
            try:
                # Sanitized log (never log MAP_KEY)
                masked_url = url.replace(settings.NASA_FIRMS_MAP_KEY, "***MAP_KEY***")
                logger.info(f"[POLL ATTEMPT {attempt}/{retries}] Fetching {masked_url}")

                response = await client.get(url)

                if response.status_code == 200:
                    records = self.parse_firms_csv(response.text, source_constellation)
                    logger.info(f"[SUCCESS] Received {len(records)} records from {source_constellation}.")
                    return records
                
                elif response.status_code == 429:
                    retry_after = float(response.headers.get("Retry-After", delay * 2.0))
                    logger.warning(f"[RATE LIMITED] HTTP 429 on {source_constellation}. Backing off for {retry_after}s.")
                    await asyncio.sleep(retry_after)
                    delay *= 2.0
                
                elif response.status_code in [401, 403]:
                    err_msg = f"NASA FIRMS Authentication Failure (HTTP {response.status_code}): Invalid or expired MAP_KEY."
                    logger.error(err_msg)
                    raise ValueError(err_msg)
                
                else:
                    logger.warning(f"[HTTP {response.status_code}] Attempt {attempt} failed on {source_constellation}: {response.text[:150]}")
                    if attempt < retries:
                        await asyncio.sleep(delay)
                        delay *= 2.0
                    else:
                        raise httpx.HTTPStatusError(f"HTTP {response.status_code}", request=response.request, response=response)

            except (httpx.RequestError, httpx.TimeoutException) as e:
                logger.warning(f"[NETWORK ERROR] Attempt {attempt} failed on {source_constellation}: {e}")
                if attempt < retries:
                    await asyncio.sleep(delay)
                    delay *= 2.0
                else:
                    raise

        return []

    # =========================================================================
    # 3. END-TO-END INGESTION CYCLE
    # =========================================================================

    async def run_ingestion_cycle(
        self,
        db: Optional[Session] = None,
        bbox: Optional[str] = None,
        days: int = 1,
        source_override: Optional[List[str]] = None
    ) -> FIRMSIngestSummaryResponse:
        """
        Execute a full synchronized ingestion cycle across all configured constellations.
        Fetches observations, standardizes, deduplicates, and saves to database.
        """
        start_time = time.time()
        self.status.total_polls_count += 1
        self.status.last_poll_timestamp = datetime.now(timezone.utc)
        
        sources_to_poll = source_override or settings.FIRMS_SOURCE_CONSTELLATIONS
        all_raw_records: List[Dict[str, Any]] = []
        cycle_errors: List[str] = []

        for source in sources_to_poll:
            try:
                records = await self.fetch_source_records(source, bbox=bbox, days=days)
                all_raw_records.extend(records)
            except Exception as e:
                err_str = f"Source [{source}] fetch failed: {str(e)}"
                logger.error(err_str)
                cycle_errors.append(err_str)

        # Database session management
        owns_session = False
        if db is None:
            db = SessionLocal()
            owns_session = True

        try:
            # Ingest & Deduplicate through Canonical FIRMS service
            summary = firms_service.ingest_records(
                records=all_raw_records,
                db=db,
                source="NASA_FIRMS",
                is_live_data=True
            )

            # Update Metrics & Telemetry
            self.status.records_received_total += summary.records_received
            self.status.records_persisted_total += summary.records_persisted
            self.status.duplicates_skipped_total += summary.duplicates_skipped
            self.status.records_rejected_total += summary.records_rejected_invalid

            if cycle_errors and not all_raw_records:
                self.status.failed_polls_count += 1
                self.status.last_error = "; ".join(cycle_errors)
                self.status.last_error_timestamp = datetime.now(timezone.utc)
            else:
                self.status.successful_polls_count += 1
                self.status.last_successful_poll_timestamp = datetime.now(timezone.utc)
                if summary.records_persisted > 0:
                    self.status.last_successful_acquisition_timestamp = datetime.now(timezone.utc)
                if cycle_errors:
                    self.status.last_error = f"Partial success with errors: {'; '.join(cycle_errors)}"
                else:
                    self.status.last_error = None

            self.status.last_ingestion_summary = {
                "records_received": summary.records_received,
                "records_persisted": summary.records_persisted,
                "duplicates_skipped": summary.duplicates_skipped,
                "duration_ms": summary.ingestion_duration_ms,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

            return summary

        finally:
            if owns_session:
                db.close()

    # =========================================================================
    # 4. BACKGROUND POLLER
    # =========================================================================

    async def _poller_loop(self):
        """Continuous background polling loop executing every N minutes."""
        logger.info(f"NASA FIRMS Background Poller started (Interval: {settings.FIRMS_POLL_INTERVAL_MINUTES}m).")
        self.status.is_polling_active = True
        
        while self.status.is_polling_active:
            try:
                logger.info("Executing scheduled NASA FIRMS poll cycle...")
                await self.run_ingestion_cycle(days=settings.FIRMS_LOOKBACK_DAYS)
            except Exception as e:
                logger.error(f"Scheduled FIRMS poll encounter exception: {e}")
                self.status.last_error = str(e)
                self.status.last_error_timestamp = datetime.now(timezone.utc)
            
            interval_sec = max(60, settings.FIRMS_POLL_INTERVAL_MINUTES * 60)
            await asyncio.sleep(interval_sec)

    def start_background_polling(self):
        """Start the background ingestion poller if not already running."""
        if not self.status.is_polling_active:
            self.status.is_polling_active = True
            loop = asyncio.get_event_loop()
            self._background_task = loop.create_task(self._poller_loop())

    def stop_background_polling(self):
        """Stop background polling task."""
        self.status.is_polling_active = False
        if self._background_task and not self._background_task.done():
            self._background_task.cancel()

    def get_feed_status(self) -> Dict[str, Any]:
        """Return diagnostic status metrics for observability dashboard."""
        return self.status.to_dict()

firms_ingestion_service = FIRMSIngestionService()
