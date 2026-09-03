# SIH26162 — Security Architecture

**System:** REACT-X Thermal Intelligence Platform  
**Classification:** Not Classified (Research/Prototype)  
**Prepared for:** SIH 2026 Evaluation — Problem Statement SIH26162  
**Organization:** NTRO (Prototype, Not Production Deployment)

---

## 1. Security Posture Summary

| Layer | Control | Status |
|---|---|---|
| OT Boundary | Read-only observation, no physical actuation | ✅ ENFORCED |
| API Authentication | Demo-mode (no auth) with JWT upgrade path | ⚠️ NOT IMPLEMENTED |
| CORS | Env-configurable origins (no wildcard in production) | ✅ IMPLEMENTED |
| Secrets Management | All secrets via environment variables | ✅ IMPLEMENTED |
| Data Encryption at Rest | Not implemented (SQLite dev, PostGIS prod) | ⚠️ ARCHITECTURE DEFINED |
| Data Encryption in Transit | HTTPS via reverse proxy (not built-in) | ⚠️ ARCHITECTURE DEFINED |
| Synthetic Data Marking | All seed/mock data explicitly labeled | ✅ IMPLEMENTED |
| Stack Trace Exposure | No internal tracebacks in API responses | ✅ IMPLEMENTED |
| Input Validation | Pydantic V2 schema validation on all endpoints | ✅ IMPLEMENTED |

---

## 2. OT Safety Boundary (Critical)

**The most important security constraint in this system:**

> **SIH26162 is a READ-ONLY satellite observation platform. It does NOT command, control, or interfere with any operational technology (OT), industrial control system (ICS), SCADA system, or physical equipment.**

### What the system does:
- Ingests NASA FIRMS satellite thermal observations
- Classifies thermal sources using AI/ML
- Generates human-readable risk assessments
- Prepares incident *drafts* for human operator review
- Displays alerts on a monitoring dashboard

### What the system does NOT do:
- Issue PLC commands
- Trigger Safety Instrumented System (SIS) signals
- Control Emergency Shutdown Devices (ESD)
- Activate sirens, sprinklers, or evacuation systems
- Send autonomous actuation commands of any kind

### Enforcement:
- All incident drafts include explicit disclaimers:
  - `chemical_consequence_status: "INSUFFICIENT_DATA"` unless chemical inventory confirmed
  - `site_evacuation_status: "SITE_LEVEL_DATA_UNAVAILABLE"` unless worker roster confirmed
- No PLC/SIS/ESD command fields exist anywhere in the codebase
- The REACT-X handoff gateway requires human operator authorization (`IncidentPromotionRequest`)

---

## 3. CORS Configuration

In development (default), the API accepts requests from:
```
http://localhost:5173
http://localhost:3000
http://127.0.0.1:5173
http://127.0.0.1:3000
```

In production, set:
```
CORS_ORIGINS=https://your-actual-frontend-domain.com
```

**The wildcard `"*"` has been removed from the default configuration.**

---

## 4. Authentication Architecture

### Current State (Demo/SIH Evaluation):
- **No authentication** — the API is open for SIH evaluation purposes
- All endpoints accessible without credentials
- This is intentional for prototype demonstration

### Production Upgrade Path (Not Implemented):
1. Add `python-jose` + `passlib` dependencies
2. Implement `app/api/routes_auth.py` with:
   - `POST /api/auth/token` — issues JWT (RS256)
   - Bearer token dependency injected into all protected routes
3. Role-based access: `HSE_OPERATOR`, `HSE_COMMANDER`, `READ_ONLY_VIEWER`
4. Incident promotion requires `HSE_COMMANDER` role minimum

### Why not implemented:
- SIH26162 evaluation focuses on AI/ML and satellite data integration
- Authentication adds no analytical value to the problem statement
- Building insecure authentication is worse than no authentication
- The architecture is clearly defined for production upgrade

---

## 5. Secrets Management

All secrets are managed via environment variables. **No secrets are hard-coded.**

| Secret | Environment Variable | Default |
|---|---|---|
| NASA FIRMS API Key | `NASA_FIRMS_MAP_KEY` | `""` (empty — FIRMS disabled) |
| Database URL | `DATABASE_URL` | SQLite dev path |
| PostgreSQL password | `DB_PASSWORD` | Required for production profile |
| CORS origins | `CORS_ORIGINS` | Localhost dev origins |

### `.env.example`:
Provided at repository root with placeholder values. `.env` is gitignored.

---

## 6. Data Classification

| Data Type | Classification | Handling |
|---|---|---|
| NASA FIRMS satellite observations | Open public data (NASA public domain) | No restriction |
| OpenStreetMap facility data | CC BY-SA 2.0 | Attribution required |
| AI/ML classification outputs | SCREENING-LEVEL INTELLIGENCE — NOT CERTIFIED | Explicit label in all outputs |
| Synthetic seed data | SYNTHETIC | Explicitly labeled with `is_live_data=False` |
| Industrial risk assessments | SCREENING-LEVEL — OPERATOR REVIEW REQUIRED | Disclaimer in all outputs |

---

## 7. Data Provenance & Integrity

Every `IndustrialThermalAssessment` includes an `AssessmentLineage` object that records:
- Contributing satellite observation IDs
- ML model version used
- Evidence fusion algorithm version
- Risk scoring algorithm version
- Processing timestamp (UTC)

This enables reproducibility audits: given identical input observations and versions, the assessment output is deterministic within documented tolerance.

---

## 8. Synthetic Data Governance

> [!IMPORTANT]
> The development seed dataset is synthetic. It is generated programmatically to train and test the ML pipeline.
> 
> **All synthetic data is explicitly marked:**
> - `is_live_data = False` on all seeded ThermalEventModel records
> - Model card explicitly states training data source and limitations
> - Validation report includes `"certified": false` flag

---

## 9. API Error Security

- All API errors return structured JSON, never raw Python exceptions
- No internal tracebacks exposed in production responses (verified by `test_api_reliability.py`)
- 422/404/400 responses use FastAPI standard error format
- Health/readiness responses do not expose passwords, tokens, or internal paths

---

## 10. Network Architecture Recommendation (Not Implemented)

For production deployment, the following network segmentation is recommended:

```
Internet → [Load Balancer + TLS Termination] → [Frontend (nginx)]
                                             → [API Gateway] → [Backend FastAPI]
                                                            → [Database (PostGIS)]
                    [OT Network - ISOLATED] ←← (NO CONNECTION)
```

**Key constraint:** The satellite observation system must have ZERO network connectivity to OT systems, SCADA networks, or plant control rooms.

---

## 11. Compliance Notes

This system is a research prototype for SIH26162 evaluation. It is:
- **NOT** compliant with IEC 62443 (Industrial Cybersecurity)
- **NOT** compliant with IEC 61508 (Functional Safety)
- **NOT** approved for PESO/OISD regulatory use
- **NOT** intended for deployment in live industrial facilities without appropriate security hardening, certification, and regulatory approval

All outputs must be treated as **screening-level intelligence requiring human expert review**.
