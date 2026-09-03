import os
from pathlib import Path
from typing import List
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR.parent / "data"

# Automatically load environment variables from .env files
load_dotenv(BASE_DIR / ".env")
load_dotenv(BASE_DIR.parent / ".env")


class Settings:
    PROJECT_NAME: str = "SIH26162 — AI Satellite Thermal Intelligence & Industrial Fire Platform"
    PROJECT_VERSION: str = "2.0.0"
    SYSTEM_VERSION: str = "2.0.0-rc1"
    API_V1_STR: str = "/api"
    DATABASE_URL: str = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR}/sih1505.db")
    SEED_DATA_PATH: Path = DATA_DIR / "seed_data.json"

    # NASA FIRMS API Credentials & Configuration
    NASA_FIRMS_MAP_KEY: str = os.getenv("NASA_FIRMS_MAP_KEY", os.getenv("NASA_FIRMS_API_KEY", ""))
    NASA_FIRMS_BASE_URL: str = os.getenv("NASA_FIRMS_BASE_URL", "https://firms.modaps.eosdis.nasa.gov/api/area/csv")
    FIRMS_POLL_INTERVAL_MINUTES: int = int(os.getenv("FIRMS_POLL_INTERVAL_MINUTES", "15"))
    FIRMS_TIMEOUT_SEC: float = float(os.getenv("FIRMS_TIMEOUT_SEC", "15.0"))
    FIRMS_MAX_RETRIES: int = int(os.getenv("FIRMS_MAX_RETRIES", "3"))
    FIRMS_LOOKBACK_DAYS: int = int(os.getenv("FIRMS_LOOKBACK_DAYS", "1"))
    FIRMS_DEFAULT_BBOX: str = os.getenv("FIRMS_DEFAULT_BBOX", "68.0,8.0,97.0,37.5")  # Full India
    FIRMS_SOURCE_CONSTELLATIONS: List[str] = [
        s.strip() for s in os.getenv(
            "FIRMS_SOURCE_CONSTELLATIONS",
            "VIIRS_NOAA20_NRT,VIIRS_NOAA21_NRT,VIIRS_SNPP_NRT,MODIS_NRT"
        ).split(",") if s.strip()
    ]

    # Copernicus Data Space & Sentinel Hub Configuration
    COPERNICUS_CLIENT_ID: str = os.getenv("COPERNICUS_CLIENT_ID", "")
    COPERNICUS_CLIENT_SECRET: str = os.getenv("COPERNICUS_CLIENT_SECRET", "")
    COPERNICUS_TOKEN_URL: str = os.getenv(
        "COPERNICUS_TOKEN_URL",
        "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token"
    )
    COPERNICUS_SH_BASE_URL: str = os.getenv(
        "COPERNICUS_SH_BASE_URL",
        "https://sh.dataspace.copernicus.eu"
    )
    COPERNICUS_TIMEOUT_SEC: float = float(os.getenv("COPERNICUS_TIMEOUT_SEC", "15.0"))
    COPERNICUS_MAX_CLOUD_PCT: float = float(os.getenv("COPERNICUS_MAX_CLOUD_PCT", "40.0"))

    # ML / Classification Settings
    ML_ABSTENTION_THRESHOLD: float = float(os.getenv("ML_ABSTENTION_THRESHOLD", "0.45"))

    # Data Quality Settings
    DATA_QUALITY_MIN_COVERAGE: float = float(os.getenv("DATA_QUALITY_MIN_COVERAGE", "0.60"))

    # CORS — explicitly configured origins. '*' is allowed only in demo/dev mode.
    CORS_ORIGINS: list = [
        o.strip() for o in os.getenv(
            "CORS_ORIGINS",
            "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000,http://127.0.0.1:3000"
        ).split(",") if o.strip()
    ]

settings = Settings()
