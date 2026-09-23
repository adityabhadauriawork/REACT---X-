from fastapi import FastAPI, Response, Depends
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.database import engine, Base, SessionLocal, get_db
from app.core.correlation import CorrelationIdMiddleware
from app.core.metrics import PrometheusMetricsMiddleware, get_prometheus_metrics_bytes
from app.services.site.site_service import site_service

# Import API routers
from app.api.routes_site import router as site_router
from app.api.routes_chemicals import router as chemicals_router
from app.api.routes_scenarios import router as scenarios_router
from app.api.routes_hazard import router as hazard_router
from app.api.routes_impact import router as impact_router
from app.api.routes_evacuation import router as evacuation_router
from app.api.routes_resources import router as resources_router
from app.api.routes_preplan import router as preplan_router
from app.api.routes_weather import router as weather_router
from app.api.routes_intelligence import router as intelligence_router
from app.api.routes_streaming import router as streaming_router
from app.api.routes_thermal import router as thermal_router
from app.api.routes_thermal_sources import router as thermal_sources_router
from app.api.routes_facilities import router as facilities_router
from app.api.routes_thermal_fingerprints import router as thermal_fingerprints_router
from app.api.routes_thermal_classification import router as thermal_classification_router
from app.api.routes_thermal_corroboration import satellite_router, evidence_router
from app.api.routes_thermal_assessment import assessment_router
from app.api.routes_health import router as health_router, health as health_check_handler, readiness as readiness_check_handler
from app.api.routes_telemetry import router as telemetry_router
from app.api.routes_vision import router as vision_router
from app.api.routes_prediction import router as prediction_router
from app.api.routes_fusion import router as fusion_router
from app.api.routes_adaptive import router as adaptive_router
from app.api.routes_discrimination import router as discrimination_router
from app.api.routes_national import router as national_router
from app.api.routes_orchestration import router as orchestration_router
from app.api.routes_data_gateway import router as data_gateway_router
from app.services.storage.repository import storage_repository
from app.services.satellite.industrial_context_service import industrial_context_service
from app.services.satellite.fingerprint_engine import fingerprint_engine
from app.services.industrial.telemetry_service import telemetry_service
from app.services.vision.vision_pipeline_service import vision_pipeline_service
from app.services.satellite.firms_ingestion_service import firms_ingestion_service
from app.core.migrations import run_auto_migrations
from app.models.thermal_classification import ThermalClassificationResultModel
from app.models.thermal_corroboration import ThermalEvidenceBundleModel, ThermalEvidenceMemberModel
from app.models.thermal_assessment import IndustrialThermalAssessmentModel

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize and migrate database tables & columns
    Base.metadata.create_all(bind=engine)
    run_auto_migrations(engine, Base)

    # Seed initial plant, chemical, storage limits, industrial facility context, baseline fingerprints, telemetry, and vision catalogs
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

    # Start NASA FIRMS live polling background loop only if key is configured AND background polling is enabled
    if settings.NASA_FIRMS_MAP_KEY and settings.ENABLE_BACKGROUND_POLL:
        firms_ingestion_service.start_background_polling()

    yield

    firms_ingestion_service.stop_background_polling()


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.PROJECT_VERSION,
    description="SIH26162 — AI-Based Detection and Classification of Industrial Fires and Persistent Thermal Sources Using NASA FIRMS, OSM & Satellite Data",
    lifespan=lifespan
)

# Request Correlation ID tracking (attaches X-Request-ID to all responses)
app.add_middleware(CorrelationIdMiddleware)

# Prometheus operational metrics tracking (measures latency & request counts)
app.add_middleware(PrometheusMetricsMiddleware)

# CORS configuration — origins are environment-configurable with regex for all Vercel deployments
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global unhandled exception handler to ensure CORS headers and structured error responses
@app.exception_handler(Exception)
async def global_exception_handler(request, exc: Exception):
    import traceback
    traceback.print_exc()
    return JSONResponse(
        status_code=500,
        content={
            "detail": str(exc) or "Internal Server Error",
            "error_type": exc.__class__.__name__
        }
    )

# Mount API routers
app.include_router(health_router, prefix=settings.API_V1_STR)
app.include_router(thermal_router, prefix=settings.API_V1_STR)
app.include_router(thermal_sources_router, prefix=settings.API_V1_STR)
app.include_router(facilities_router, prefix=settings.API_V1_STR)
app.include_router(thermal_fingerprints_router, prefix=settings.API_V1_STR)
app.include_router(thermal_classification_router, prefix=settings.API_V1_STR)
app.include_router(evidence_router, prefix=settings.API_V1_STR)
app.include_router(satellite_router, prefix=settings.API_V1_STR)
app.include_router(assessment_router, prefix=settings.API_V1_STR)
app.include_router(site_router, prefix=settings.API_V1_STR)
app.include_router(chemicals_router, prefix=settings.API_V1_STR)
app.include_router(scenarios_router, prefix=settings.API_V1_STR)
app.include_router(hazard_router, prefix=settings.API_V1_STR)
app.include_router(impact_router, prefix=settings.API_V1_STR)
app.include_router(evacuation_router, prefix=settings.API_V1_STR)
app.include_router(resources_router, prefix=settings.API_V1_STR)
app.include_router(preplan_router, prefix=settings.API_V1_STR)
app.include_router(weather_router, prefix=settings.API_V1_STR)
app.include_router(intelligence_router, prefix=settings.API_V1_STR)
app.include_router(streaming_router, prefix=settings.API_V1_STR)
app.include_router(telemetry_router, prefix=settings.API_V1_STR)
app.include_router(vision_router, prefix=settings.API_V1_STR)
app.include_router(prediction_router, prefix=settings.API_V1_STR)
app.include_router(fusion_router, prefix=settings.API_V1_STR)
app.include_router(adaptive_router, prefix=settings.API_V1_STR)
app.include_router(discrimination_router, prefix=settings.API_V1_STR)
app.include_router(national_router, prefix=settings.API_V1_STR)
app.include_router(orchestration_router, prefix=settings.API_V1_STR)
app.include_router(data_gateway_router, prefix=settings.API_V1_STR)

# Prometheus Operational Metrics Exporter
@app.get("/metrics", tags=["Observability"])
@app.get("/api/metrics", tags=["Observability"])
def prometheus_metrics():
    """Returns real-time Prometheus operational metrics in standard text format."""
    return Response(
        content=get_prometheus_metrics_bytes(),
        media_type="text/plain; version=0.0.4; charset=utf-8"
    )

# Root-level health and readiness probes for standard container orchestrators / load balancers
@app.get("/health", tags=["Health & Observability"])
def root_liveness():
    return health_check_handler()

@app.get("/readiness", tags=["Health & Observability"])
def root_readiness(db: Session = Depends(get_db)):
    return readiness_check_handler(db=db)

@app.get("/api/version")
def api_version():
    return {
        "service": settings.PROJECT_NAME,
        "version": settings.PROJECT_VERSION,
        "system_version": settings.SYSTEM_VERSION
    }

@app.get("/")
def root_info():
    return {
        "message": "SIH26162 AI Satellite Thermal Intelligence & Industrial Fire Command Platform API is running.",
        "docs_url": "/docs",
        "api_prefix": settings.API_V1_STR
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)

