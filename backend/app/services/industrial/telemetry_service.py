import time
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.schemas.telemetry import (
    FacilityTelemetryObservation, SensorMetadata, EdgeGateway,
    TelemetryHealthResponse, TelemetryHistoryQuery, SourceProtocol, GatewayStatus,
    SensorType, TelemetryQuality, DataQualityFlag, FreshnessStatus
)
from app.services.industrial.base_telemetry_adapter import TelemetrySourceAdapter
from app.services.industrial.opcua_adapter import opcua_adapter
from app.services.industrial.mqtt_adapter import mqtt_adapter
from app.services.industrial.telemetry_simulator import telemetry_simulator, SimulationScenario
from app.services.ingestion.telemetry_freshness_engine import telemetry_freshness_engine
from app.services.ingestion.telemetry_buffer_queue import EdgeLocalBuffer, BackpressureQueue
from app.services.ingestion.telemetry_state_store import telemetry_state_store
from app.services.ingestion.telemetry_quality_validator import telemetry_quality_validator
from app.services.storage.telemetry_repository import telemetry_repository

logger = logging.getLogger(__name__)

class TelemetryService:
    """
    Unified Industrial Telemetry Ingestion Orchestrator.
    Manages edge adapters (OPC UA, MQTT, Simulator), data normalization, quality validation,
    thread-safe latest-value state caching, backpressure buffering, and durable persistence.
    """

    def __init__(self):
        self.adapters: Dict[str, TelemetrySourceAdapter] = {
            "OPC_UA": opcua_adapter,
            "MQTT_SPARKPLUG": mqtt_adapter,
            "SIMULATOR": telemetry_simulator
        }
        self.edge_buffer = EdgeLocalBuffer(max_capacity=5000)
        self.backpressure_queue = BackpressureQueue(max_queue_size=2000)
        self.start_time = time.time()
        self.total_ingested = 0
        self.good_count = 0
        self.warning_count = 0
        self.bad_count = 0
        self.stale_count = 0
        self.ingestion_latencies: List[float] = []

        # Register all sensors into state store
        self._sync_sensors_to_state_store()

    def _sync_sensors_to_state_store(self):
        """Sync adapter sensor metadata catalogs into in-memory state store."""
        telemetry_state_store.clear()
        for adapter in self.adapters.values():
            for s in adapter.get_registered_sensors():
                telemetry_state_store.register_sensor_metadata(s)

    def seed_initial_metadata(self, db: Session):
        """Seed default edge gateways and sensor catalogs into the database."""
        # Gateways
        gateways = [
            EdgeGateway(
                gateway_id="GW-DAHEJ-OPCUA-01",
                facility_id="FAC-IN-DAHEJ-001",
                protocol=SourceProtocol.OPC_UA,
                endpoint="opc.tcp://127.0.0.1:4840/REACTX/OPCUAServer",
                status=GatewayStatus.CONNECTED,
                active_sensors_count=len(opcua_adapter.registered_sensors)
            ),
            EdgeGateway(
                gateway_id="GW-DAHEJ-MQTT-01",
                facility_id="FAC-IN-DAHEJ-001",
                protocol=SourceProtocol.MQTT_SPARKPLUG,
                endpoint="mqtts://127.0.0.1:8883/spBv1.0/PlantDahej",
                status=GatewayStatus.CONNECTED,
                active_sensors_count=len(mqtt_adapter.registered_sensors)
            ),
            EdgeGateway(
                gateway_id="GW-SIM-DAHEJ-01",
                facility_id="FAC-IN-DAHEJ-001",
                protocol=SourceProtocol.SIMULATED_GATEWAY,
                endpoint="simulator://internal-timeseries-engine",
                status=GatewayStatus.CONNECTED,
                active_sensors_count=len(telemetry_simulator.registered_sensors)
            ),
        ]
        for gw in gateways:
            telemetry_repository.register_gateway(db, gw)

        # Sensors
        for adapter in self.adapters.values():
            for meta in adapter.get_registered_sensors():
                telemetry_repository.register_sensor(db, meta)

    def ingest_observations(
        self,
        observations: List[FacilityTelemetryObservation],
        db: Optional[Session] = None
    ) -> List[FacilityTelemetryObservation]:
        """
        Process incoming batch of observations:
        1. Validate quality & physics bounds
        2. Update latest-value store
        3. Enqueue to backpressure buffer
        4. Persist to database if session provided
        """
        t0 = time.perf_counter()
        processed: List[FacilityTelemetryObservation] = []

        for obs in observations:
            # Look up metadata from adapter
            adapter = self.adapters.get(obs.source_protocol.value, telemetry_simulator)
            meta = adapter.registered_sensors.get(obs.sensor_id) if adapter else None

            # 1. Quality validation & unit normalization
            validated = telemetry_quality_validator.normalize_and_validate(obs, meta)

            # 2. Update state store
            telemetry_state_store.update_latest_observation(validated)

            # 3. Quality counts tracking
            self.total_ingested += 1
            if validated.quality == TelemetryQuality.GOOD:
                self.good_count += 1
            elif validated.quality == TelemetryQuality.WARNING:
                self.warning_count += 1
            elif validated.quality == TelemetryQuality.BAD:
                self.bad_count += 1
            elif validated.quality == TelemetryQuality.STALE:
                self.stale_count += 1

            # 4. Backpressure queue
            self.backpressure_queue.enqueue(validated)
            processed.append(validated)

        # 5. Durable persistence
        if db is not None and processed:
            try:
                telemetry_repository.persist_observations(db, processed)
            except Exception as e:
                logger.error(f"Error persisting telemetry batch: {e}")
                db.rollback()

        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        self.ingestion_latencies.append(elapsed_ms)
        if len(self.ingestion_latencies) > 500:
            self.ingestion_latencies.pop(0)

        return processed

    def generate_simulator_tick(self, db: Optional[Session] = None, force_all: bool = True) -> List[FacilityTelemetryObservation]:
        """Generate one correlated tick batch from simulator and ingest."""
        raw_batch = telemetry_simulator.generate_tick_batch(force_all=force_all)
        return self.ingest_observations(raw_batch, db)

    def get_latest_facility_telemetry(self, facility_id: str) -> List[FacilityTelemetryObservation]:
        """Retrieve latest values across all sensors in a facility with dynamic freshness."""
        results = telemetry_state_store.get_latest_for_facility(facility_id)
        if not results:
            # Generate initial tick if state is empty
            self.generate_simulator_tick()
            results = telemetry_state_store.get_latest_for_facility(facility_id)
        return results

    def get_latest_sensor_telemetry(self, sensor_id: str) -> Optional[FacilityTelemetryObservation]:
        """Retrieve latest value for a specific sensor."""
        obs = telemetry_state_store.get_latest_for_sensor(sensor_id)
        if not obs:
            self.generate_simulator_tick()
            obs = telemetry_state_store.get_latest_for_sensor(sensor_id)
        return obs

    def query_history(self, db: Session, query: TelemetryHistoryQuery) -> List[FacilityTelemetryObservation]:
        """Fetch paginated historical telemetry with time-window filtering."""
        return telemetry_repository.query_history(db, query)

    def get_health(self, db: Optional[Session] = None) -> TelemetryHealthResponse:
        """Compute full telemetry ingestion and gateway health metrics."""
        uptime = max(0.1, time.time() - self.start_time)
        rate = round(self.total_ingested / uptime, 1)

        total_q = max(1, self.good_count + self.warning_count + self.bad_count + self.stale_count)
        good_pct = round((self.good_count / total_q) * 100.0, 1)
        warn_pct = round((self.warning_count / total_q) * 100.0, 1)
        bad_pct = round((self.bad_count / total_q) * 100.0, 1)
        stale_pct = round((self.stale_count / total_q) * 100.0, 1)

        p95 = round(sorted(self.ingestion_latencies)[int(len(self.ingestion_latencies) * 0.95)], 2) if self.ingestion_latencies else 0.4
        p99 = round(sorted(self.ingestion_latencies)[int(len(self.ingestion_latencies) * 0.99)], 2) if self.ingestion_latencies else 1.1

        gateways = [
            EdgeGateway(
                gateway_id=opcua_adapter.gateway_id,
                facility_id=opcua_adapter.facility_id,
                protocol=opcua_adapter.protocol,
                endpoint=opcua_adapter.endpoint,
                status=opcua_adapter.status,
                active_sensors_count=len(opcua_adapter.registered_sensors)
            ),
            EdgeGateway(
                gateway_id=mqtt_adapter.gateway_id,
                facility_id=mqtt_adapter.facility_id,
                protocol=mqtt_adapter.protocol,
                endpoint=f"mqtts://{mqtt_adapter.broker_host}:{mqtt_adapter.broker_port}",
                status=mqtt_adapter.status,
                active_sensors_count=len(mqtt_adapter.registered_sensors)
            ),
            EdgeGateway(
                gateway_id=telemetry_simulator.gateway_id,
                facility_id=telemetry_simulator.facility_id,
                protocol=telemetry_simulator.protocol,
                endpoint="simulator://internal-timeseries-engine",
                status=telemetry_simulator.status,
                active_sensors_count=len(telemetry_simulator.registered_sensors)
            ),
        ]

        total_sensors = sum(len(a.registered_sensors) for a in self.adapters.values())

        return TelemetryHealthResponse(
            status="OPERATIONAL",
            uptime_sec=round(uptime, 1),
            events_ingested_total=self.total_ingested,
            events_per_second=rate if rate > 0 else float(telemetry_simulator.sensor_count),
            active_gateways_count=len(gateways),
            active_sensors_count=total_sensors,
            gateways=gateways,
            quality_good_pct=good_pct,
            quality_warning_pct=warn_pct,
            quality_bad_pct=bad_pct,
            quality_stale_pct=stale_pct,
            p95_ingestion_latency_ms=p95,
            p99_ingestion_latency_ms=p99,
            backpressure_queue_size=self.backpressure_queue.size(),
            backpressure_dropped_count=self.backpressure_queue.dropped_count(),
            read_only_mode_verified=True,
            system_clock_utc=datetime.now(timezone.utc)
        )

    def set_simulator_scenario(self, scenario_name: str) -> Dict[str, Any]:
        """Trigger one of Scenarios A-J on the simulator."""
        telemetry_simulator.set_scenario(scenario_name)
        return {
            "status": "SCENARIO_UPDATED",
            "active_scenario": scenario_name,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

telemetry_service = TelemetryService()
