# REACT-X Final UI Architecture & Information Hierarchy

**Document Version:** 1.0.0  
**Phase:** 21 — Final Product Rationalization, UX Simplification & Demo Polish  

---

## 1. Information Hierarchy & Progressive Disclosure Levels

```
LEVEL 1: WHAT IS HAPPENING?
  ├── Home Status Banner (Active Alerts, Monitored Facilities, System Freshness)
  ├── 5 Large Task-Oriented Workspaces
  └── Priority Events Feed
        │
        ▼ (Click Action Card or Event)
LEVEL 2: WHY? (EVIDENCE & EXPLANATION)
  ├── Multimodal Evidence Matrix (Satellite, Telemetry, Thermal Camera, CCTV)
  ├── 10m Copernicus Land-Cover Context
  └── AI Source Classification (Routine Heat vs Uncontained Fire)
        │
        ▼ (Drill-Down / Scenario Escalation)
LEVEL 3: WHAT HAPPENS NEXT? (PREDICTION & RESPONSE)
  ├── CUSUM Rate-of-Rise Forecasts (10m, 30m, 60m)
  ├── ALOHA Atmospheric Chemical Plume Dispersion
  ├── Safe Evacuation Routes (Dijkstra Egress Paths)
  └── Tactical Resource Allocation Quotas
        │
        ▼ (Audit / Verification Request)
LEVEL 4: HOW DID THE SYSTEM ARRIVE HERE? (TRACEABILITY)
  ├── End-to-End Execution Trace (`trace_id`)
  ├── Dempster-Shafer Orthogonal Mass Assignments
  └── Decision Audit Trail & Regulatory Compliance Log
```

---

## 2. Complete Navigation Map

```
HOME
  └── Executive Overview & Task Launcher (HomeOverview.jsx)

MONITOR
  ├── Live Command Map (PlantMap.jsx)
  ├── Thermal Sources (ThermalIntelligenceHub.jsx - Sources Tab)
  └── Facilities (Facilities Grid & FacilityProfileModal.jsx)

INTELLIGENCE
  ├── AI Classification (ThermalIntelligenceHub.jsx - Classification Tab)
  ├── Hazard Trajectory (PreIncidentSafetyCenter.jsx)
  └── Evidence & Fusion (PreIncidentSafetyCenter.jsx - Fusion Matrix)

RESPONSE
  ├── Incident Assessment & Plume (ImpactMatrix.jsx)
  ├── Evacuation Routing (EvacuationNavigator.jsx)
  ├── Tactical Resource Dispatch (ResourceTactics.jsx)
  └── Emergency Pre-Plan Document (PrePlanViewer.jsx)

SIMULATION
  └── Simulation Lab & 8-Step Demo (SimulationLab.jsx - Dahej Reference Environment)

SYSTEM
  ├── Historical Analytics (HistoricalAnalytics.jsx)
  ├── Decision Audit Trail (DecisionAuditTrail.jsx)
  └── System Readiness & Source Health (Readiness View)
```
