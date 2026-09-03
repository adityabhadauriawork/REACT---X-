# REACT-X Final Operations & Demonstration Runbook

**Document Version:** 1.0.0  
**Phase:** 20 — Final System Audit, Integration Readiness & Production Gap Closure  

---

## 1. Quickstart Guide

### Starting Backend Server:
```bash
cd backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

### Starting Frontend Server:
```bash
cd frontend
npm run dev
```

---

## 2. Running End-to-End Golden Scenarios

Execute predefined scenarios via REST API or the UI:
- **Scenario A (Normal Baseline):** `GET http://127.0.0.1:8000/api/orchestration/scenarios/SCENARIO_A`
- **Scenario D (Telemetry Drift):** `GET http://127.0.0.1:8000/api/orchestration/scenarios/SCENARIO_D`
- **Scenario E (Cross-Modal Confirmation):** `GET http://127.0.0.1:8000/api/orchestration/scenarios/SCENARIO_E`
- **Scenario I (Critical Incident):** `GET http://127.0.0.1:8000/api/orchestration/scenarios/SCENARIO_I`
- **Scenario J (Cooldown & Recovery):** `GET http://127.0.0.1:8000/api/orchestration/scenarios/SCENARIO_J`

---

## 3. Triggering End-to-End Pipeline Execution

```bash
curl -X POST "http://127.0.0.1:8000/api/orchestration/pipeline/execute?facility_id=FAC-IN-DAHEJ-001&asset_id=T-04&frp_mw=45.0"
```

Returns:
- Complete `EndToEndExecutionTrace` with millisecond timings for all 11 stages.
- Synthesized `IncidentPacket` ready for incident commander review.
