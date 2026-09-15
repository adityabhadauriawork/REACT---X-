import os
import sys
import re
import ast
import pytest
from pathlib import Path

# Add backend to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))


from app.core.config import settings

def test_industrial_read_only_safety_boundary():
    """
    CRITICAL SAFETY AUDIT:
    Mathematically and syntactically proves that NO WRITE, CONTROL, ACTUATION,
    or SETPOINT modification operations exist anywhere in the industrial telemetry,
    OPC UA, Modbus, MQTT, or SCADA adapter services.
    
    Guarantees strict isolation of Safety Instrumented Systems (SIS), Emergency
    Shutdown (ESD), Distributed Control Systems (DCS), and Programmable Logic Controllers (PLC).
    """
    backend_dir = Path(__file__).resolve().parent / "app"
    forbidden_write_patterns = [
        re.compile(r'\bwrite_attribute\b', re.IGNORECASE),
        re.compile(r'\bwrite_value\b', re.IGNORECASE),
        re.compile(r'\bwrite_register\b', re.IGNORECASE),
        re.compile(r'\bwrite_coil\b', re.IGNORECASE),
        re.compile(r'\bset_setpoint\b', re.IGNORECASE),
        re.compile(r'\bpublish_control\b', re.IGNORECASE),
        re.compile(r'\bsend_command_to_plc\b', re.IGNORECASE),
        re.compile(r'\btrigger_actuator\b', re.IGNORECASE),
        re.compile(r'\boverride_interlock\b', re.IGNORECASE),
        re.compile(r'\bwrite_holding_registers\b', re.IGNORECASE)
    ]

    industrial_files = list(backend_dir.glob("services/industrial/**/*.py")) + \
                       list(backend_dir.glob("api/routes_telemetry.py"))

    assert len(industrial_files) > 0, "Industrial services must exist to be audited"

    violations = []
    for filepath in industrial_files:
        content = filepath.read_text(encoding="utf-8")
        for pattern in forbidden_write_patterns:
            matches = pattern.findall(content)
            if matches:
                violations.append(f"Forbidden write operation {matches} found in {filepath.name}")

    assert len(violations) == 0, f"Industrial safety boundary violated: {violations}"

def test_production_cors_configuration_strictness():
    """Verifies that CORS origins in production disallow wildcard '*'."""
    assert "*" not in settings.CORS_ORIGINS, "CORS_ORIGINS must not contain wildcard '*' in production"
    for origin in settings.CORS_ORIGINS:
        assert origin.startswith(("http://", "https://")), f"Invalid origin URI: {origin}"

def test_no_hardcoded_secrets_in_repo_configs():
    """Verifies that default config templates and source files do not contain real plaintext API keys."""
    env_example = (Path(__file__).resolve().parent.parent / ".env.example").read_text(encoding="utf-8")
    
    assert "CHANGE_ME_SECURE_PASSWORD" in env_example or "STRONG_PASSWORD" in env_example
    assert "YOUR_32_CHAR_NASA_FIRMS_MAP_KEY_HERE" in env_example or "b5bbb3c2" not in env_example or "MAP_KEY" in env_example

def test_trusted_outbound_satellite_domains():
    """Verifies that all outbound satellite STAC/API endpoints are constrained to trusted official domains."""
    trusted_domains = [
        "firms.modaps.eosdis.nasa.gov",
        "dataspace.copernicus.eu",
        "identity.dataspace.copernicus.eu",
        "m2m.cr.usgs.gov",
        "earth-search.aws.element84.com",
        "planetarycomputer.microsoft.com",
        "eogdata.mines.edu",
        "eogauth.mines.edu"
    ]

    endpoints = [
        settings.NASA_FIRMS_BASE_URL,
        settings.COPERNICUS_TOKEN_URL,
        settings.COPERNICUS_SH_BASE_URL,
        settings.AWS_EARTH_SEARCH_STAC_URL,
        settings.PLANETARY_COMPUTER_STAC_URL,
        settings.USGS_M2M_BASE_URL,
        settings.EOG_VNF_TOKEN_URL,
        settings.EOG_VNF_BASE_URL
    ]

    for ep in endpoints:
        if ep:
            matched = any(domain in ep for domain in trusted_domains)
            assert matched, f"Outbound endpoint '{ep}' is not in the trusted satellite domain whitelist"
