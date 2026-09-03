# REACT-X End-User Operations Runbook

**Document Version:** 1.0.0  
**Phase:** 22 — Final External Integration, Deployment & Release  
**Target Audience:** Incident Commanders, HSE Officers, Field Responders, Plant Managers  

---

## 1. Quick Operator Workflow

```
1. HOME SCREEN ────────► Review system state, active alerts, and monitored facilities.
      │
      ▼
2. MONITOR WORKSPACE ──► Inspect active thermal hotspots and plant boundary polygons.
      │
      ▼
3. INTELLIGENCE HUB ───► Review AI classification (7 classes), CUSUM predictions, and evidence.
      │
      ▼
4. RESPONSE SUITE ─────► Assess ALOHA chemical plume, Dijkstra evacuation paths, and resources.
      │
      ▼
5. AUTHORIZATION ──────► Commander formally signs off and exports compliance PDF.
```

---

## 2. Step-by-Step Task Procedures

### Task 1: Inspecting an Emerging Anomaly
1. On the **Home Screen**, check the **Priority Monitored Events** table.
2. Click **`Inspect`** on the flagged event to open the facility workspace.
3. Observe the **Hazard Trajectory** chart to evaluate whether the trend ($dT/dt$, $dP/dt$) breaches historical operating envelopes.

### Task 2: Verifying Cross-Modal Evidence
1. Navigate to **`INTELLIGENCE` $\to$ `Evidence & Fusion`**.
2. Inspect the **Multimodal Evidence Matrix**:
   - Check if Satellite, Telemetry, and Thermal Camera are `SUPPORTING`.
   - Review the Fused Certainty Score ($0\%$ to $100\%$) computed by Dempster-Shafer evidential combination.

### Task 3: Triggering Incident Response
1. Navigate to **`RESPONSE` $\to$ `Incident Assessment`**.
2. Inspect the **ALOHA Heavy-Gas Atmospheric Plume** overlaid on the live map.
3. Review the **Safe Evacuation Routing** table for wind-aware egress corridors.
4. Review the **Tactical Resource Dispatch** quota for water, foam, and mutual-aid appliances.
5. Click **`Pre-Plan PDF`** to generate an immutable, timestamped compliance audit document.
