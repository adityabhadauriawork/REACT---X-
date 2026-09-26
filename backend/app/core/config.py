import os
from pathlib import Path
from typing import List
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Automatically locate seed_data.json across local, Docker, and Render container layouts
def _find_seed_data_path() -> Path:
    candidates = [
        BASE_DIR / "data" / "seed_data.json",
        BASE_DIR / "app" / "data" / "seed_data.json",
        BASE_DIR.parent / "data" / "seed_data.json",
        Path.cwd() / "data" / "seed_data.json",
        Path.cwd() / "backend" / "data" / "seed_data.json",
        Path("/app/data/seed_data.json"),
        Path("/app/app/data/seed_data.json")
    ]
    for c in candidates:
        if c.exists():
            return c
    return BASE_DIR / "data" / "seed_data.json"

# Automatically load environment variables from .env files
load_dotenv(BASE_DIR / ".env")
load_dotenv(BASE_DIR.parent / ".env")


class Settings:
    PROJECT_NAME: str = "REACT-X — Industrial Thermal Intelligence & Emergency Response Platform"
    PROJECT_VERSION: str = "2.0.0"
    SYSTEM_VERSION: str = "2.0.0-rc1"
    API_V1_STR: str = "/api"
    DATABASE_URL: str = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR}/sih1505.db")
    SEED_DATA_PATH: Path = _find_seed_data_path()

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
    ENABLE_BACKGROUND_POLL: bool = os.getenv("ENABLE_BACKGROUND_POLL", "true").lower() in ("true", "1", "yes")

    # Copernicus Data Space & Sentinel Hub Configuration (Optional credentials; falls back to public STAC)
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

    # Public Open STAC Endpoints (Zero-auth public catalogs)
    AWS_EARTH_SEARCH_STAC_URL: str = os.getenv(
        "AWS_EARTH_SEARCH_STAC_URL",
        "https://earth-search.aws.element84.com/v1"
    )
    PLANETARY_COMPUTER_STAC_URL: str = os.getenv(
        "PLANETARY_COMPUTER_STAC_URL",
        "https://planetarycomputer.microsoft.com/api/stac/v1"
    )

    # USGS M2M API & Landsat 8/9 Configuration (Optional credentials; falls back to Planetary Computer STAC)
    USGS_M2M_USERNAME: str = os.getenv("USGS_M2M_USERNAME", "")
    USGS_M2M_TOKEN: str = os.getenv("USGS_M2M_TOKEN", os.getenv("USGS_M2M_API_KEY", ""))
    USGS_M2M_BASE_URL: str = os.getenv(
        "USGS_M2M_BASE_URL",
        "https://m2m.cr.usgs.gov/api/api/json/stable"
    )
    USGS_M2M_DATASET_NAME: str = os.getenv("USGS_M2M_DATASET_NAME", "landsat_ot_c2_l2")
    USGS_M2M_TIMEOUT_SEC: float = float(os.getenv("USGS_M2M_TIMEOUT_SEC", "15.0"))
    USGS_M2M_MAX_CLOUD_PCT: float = float(os.getenv("USGS_M2M_MAX_CLOUD_PCT", "50.0"))

    # Earth Observation Group (EOG) — VIIRS Nightfire (VNF) Configuration (Optional; native Planck estimator is default)
    EOG_VNF_USERNAME: str = os.getenv("EOG_VNF_USERNAME", "")
    EOG_VNF_PASSWORD: str = os.getenv("EOG_VNF_PASSWORD", "")
    EOG_VNF_CLIENT_ID: str = os.getenv("EOG_VNF_CLIENT_ID", "eogdata_oidc")
    EOG_VNF_CLIENT_SECRET: str = os.getenv("EOG_VNF_CLIENT_SECRET", "")
    EOG_VNF_TOKEN_URL: str = os.getenv(
        "EOG_VNF_TOKEN_URL",
        "https://eogauth.mines.edu/realms/eog/protocol/openid-connect/token"
    )
    EOG_VNF_BASE_URL: str = os.getenv(
        "EOG_VNF_BASE_URL",
        "https://eogdata.mines.edu/wwwdata/viirs_products/vnf/v40"
    )
    EOG_VNF_TIMEOUT_SEC: float = float(os.getenv("EOG_VNF_TIMEOUT_SEC", "20.0"))

    # ISRO / MOSDAC — INSAT-3D/3DR/3DS Geostationary Configuration (Rapid 15-min temporal cadence)
    MOSDAC_USERNAME: str = os.getenv("MOSDAC_USERNAME", os.getenv("MOSDAC_USER", ""))
    MOSDAC_PASSWORD: str = os.getenv("MOSDAC_PASSWORD", os.getenv("MOSDAC_API_KEY", ""))
    MOSDAC_API_BASE_URL: str = os.getenv("MOSDAC_API_BASE_URL", "https://mosdac.gov.in/api")
    MOSDAC_PRODUCT_FIRE: str = os.getenv("MOSDAC_PRODUCT_FIRE", "3RIMG_L2P_FIR")
    MOSDAC_PRODUCT_LST: str = os.getenv("MOSDAC_PRODUCT_LST", "3RIMG_L2B_LST")
    MOSDAC_TIMEOUT_SEC: float = float(os.getenv("MOSDAC_TIMEOUT_SEC", "15.0"))

    # Deployment Environment Mode: development | reference | production | simulation
    APP_ENV: str = os.getenv("APP_ENV", "development").lower()

    # ML / Classification Settings
    ML_ABSTENTION_THRESHOLD: float = float(os.getenv("ML_ABSTENTION_THRESHOLD", "0.45"))

    # Data Quality Settings
    DATA_QUALITY_MIN_COVERAGE: float = float(os.getenv("DATA_QUALITY_MIN_COVERAGE", "0.60"))

    # CORS — explicitly configured origins. '*' is prohibited in production mode.
    CORS_ORIGINS: list = [
        o.strip() for o in os.getenv(
            "CORS_ORIGINS",
            "https://react-x-rho.vercel.app,http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000,http://127.0.0.1:3000"
        ).split(",") if o.strip()
    ]

    def validate_production_configuration(self) -> None:
        """Strict production configuration validator.
        Fails fast if mandatory production criteria are not satisfied.
        """
        if self.APP_ENV == "production":
            errors = []
            if not self.DATABASE_URL.startswith(("postgresql://", "postgres://")):
                errors.append(
                    "DATABASE_URL must point to a PostgreSQL/PostGIS cluster (postgresql://...) in production. "
                    f"Found: '{self.DATABASE_URL[:16]}...'"
                )
            if "*" in self.CORS_ORIGINS:
                errors.append("CORS_ORIGINS must not contain wildcard '*' in production mode.")
            if not self.CORS_ORIGINS:
                errors.append("CORS_ORIGINS cannot be empty in production mode.")
            
            if errors:
                raise ValueError("CRITICAL PRODUCTION CONFIGURATION ERROR:\n- " + "\n- ".join(errors))

settings = Settings()
settings.validate_production_configuration()

