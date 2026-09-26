from typing import List, Optional
from fastapi import HTTPException, Security, Request, status
from fastapi.security import APIKeyHeader

API_KEY_HEADER = APIKeyHeader(name="X-REACT-X-API-KEY", auto_error=False)

class RoleSecurity:
    """
    Role-Based Access Control (RBAC) & Least Privilege Enforcement:
    Validates user role permissions for safety-critical operations.
    """
    VALID_ROLES = {
        "FIELD_RESPONDER",
        "HSE_COMMANDER",
        "PLANT_MANAGER",
        "DISTRICT_AUTHORITY",
        "EXECUTIVE_AUTHORITY",
        "DEMO_ADMIN"
    }

    # Permissions Matrix
    PERMISSIONS = {
        "VIEW_TELEMETRY": VALID_ROLES,
        "VIEW_COMMAND_MAP": VALID_ROLES,
        "RUN_HAZARD_SIMULATION": {"HSE_COMMANDER", "PLANT_MANAGER", "DEMO_ADMIN"},
        "RUN_PREVENTIVE_WHATIF": {"HSE_COMMANDER", "PLANT_MANAGER", "DEMO_ADMIN"},
        "AUTHORIZE_PREPLAN": {"HSE_COMMANDER", "PLANT_MANAGER", "DEMO_ADMIN"},
        "AUTHORIZE_DCS_CONTROL": {"HSE_COMMANDER", "PLANT_MANAGER", "DEMO_ADMIN"},
        "EXPORT_OFFICIAL_BRIEF": {"HSE_COMMANDER", "PLANT_MANAGER", "DISTRICT_AUTHORITY", "EXECUTIVE_AUTHORITY", "DEMO_ADMIN"}
    }

    @classmethod
    def verify_role_permission(cls, role: str, required_permission: str) -> bool:
        allowed = cls.PERMISSIONS.get(required_permission, set())
        if role.upper() not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{role}' is not authorized for operation '{required_permission}'."
            )
        return True


def verify_ingestion_api_key(api_key: Optional[str] = Security(API_KEY_HEADER)) -> bool:
    """
    Validates X-REACT-X-API-KEY on ingestion endpoints.
    If REACTX_INGESTION_API_KEY is configured in backend environment, the header is strictly enforced.
    If no key is configured in dev/demo environment, open access with REFERENCE provenance is allowed.
    """
    import os
    expected_key = os.getenv("REACTX_INGESTION_API_KEY", "").strip()
    if not expected_key:
        return True
    
    if not api_key or api_key.strip() != expected_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing X-REACT-X-API-KEY authentication header."
        )
    return True


def add_security_headers(response):
    """Adds hardened HTTP security headers."""
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response

