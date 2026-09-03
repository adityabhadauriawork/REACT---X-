# REACT-X Operations & Incident Response Runbook

**Document Version:** 1.0.0  
**Phase:** 19 — End-to-End System Integration, Connectivity & Operational Orchestration  

---

## 1. Operating Modes & Transitions

REACT-X supports four explicit operational modes:
1. **LIVE Mode:** Ingests live NASA FIRMS passes, real OPC-UA/MQTT gateway streams, and on-site cameras.
2. **REFERENCE Mode:** Executes golden validation datasets (e.g. Dahej PetroChem Alpha) for calibration and compliance audits.
3. **SIMULATION Mode:** Executes dynamic training scenarios (Scenarios A through J) through the real production pipeline.
4. **MIXED Mode:** Clearly separates live telemetry from simulated secondary sensors, tagging each piece of evidence with its provenance.

---

## 2. Incident Packet Verification Workflow

```
Thermal / Process Anomaly Triggered
               │
               ▼
   Pipeline Orchestrator Runs (11 Stages)
               │
               ▼
   IncidentPacket Generated (Status: PENDING_INCIDENT_COMMANDER_REVIEW)
               │
               ▼
┌────────────────────────────────────────────────────────┐
│  HUMAN OPERATOR / INCIDENT COMMANDER REVIEW            │
│  - Inspect Fused Evidential Breakdown (Satellite + T + Cam) │
│  - Review ALOHA Plume Dispersion & Evacuation Routes   │
│  - Verify Resource Quota (Foam Tenders, Ambulances)    │
└──────────────────────────┬─────────────────────────────┘
                           │
            ┌──────────────┴──────────────┐
            ▼                             ▼
   [AUTHORIZE RESPONSE]          [REJECT / RECALIBRATE]
```
