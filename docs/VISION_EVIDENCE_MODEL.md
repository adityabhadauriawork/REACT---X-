# Canonical Visual Evidence Model & Multi-Modal Fusion Contract

**System:** REACT-X / SIH26162  
**Document Version:** 1.0.0 (Phase 13 Vision Foundation)  
**Classification:** Information Model & Fusion Interface  

---

## 1. Visual Evidence Contract (`VisualEvidence`)

The visual evidence contract standardizes derived vision outputs across both radiometric thermal sensors and optical CCTV cameras:

```json
{
  "evidence_id": "EVID-TH-8A2F10C9",
  "source_id": "CAM-TH-DAHEJ-01",
  "facility_id": "FAC-IN-DAHEJ-001",
  "asset_id": "T-04",
  "zone_id": "Sector D - Cryogenic Yard",
  "timestamp_utc": "2026-09-01T10:15:30Z",
  "evidence_type": "THERMAL_HOTSPOT",
  "feature_name": "peak_temperature",
  "value": 88.4,
  "unit": "°C",
  "confidence": 0.94,
  "quality": "GOOD",
  "freshness_status": "LIVE",
  "freshness_age_sec": 0.5,
  "is_live_data": false,
  "model_version": "v1.0.0-radiometric-contour",
  "evidence_uri": "evidence://thermal/CAM-TH-DAHEJ-01/FRM-01.bin"
}
```

---

## 2. Cross-Modal Linkage to Facility Telemetry

REACT-X links visual evidence to Phase 12 process telemetry through spatial and asset keys:

$$\text{Correlation}(\text{VisualEvidence}, \text{Telemetry}) \iff (\text{Asset}_{\text{vis}} = \text{Asset}_{\text{tel}}) \land (|t_{\text{vis}} - t_{\text{tel}}| < \Delta t_{\text{window}})$$

### Example Multi-Channel Corroboration:
- **Thermal Camera:** $T_{\text{skin}} = +88.4^\circ\text{C}$, $dT/dt = +8.2^\circ\text{C}/\text{min}$
- **Pressure Transmitter (`PRESS_01`):** Overpressure rise to $2.8\,\text{bar}$
- **Skin Temperature RTD (`TEMP_SKIN`):** $+84.1^\circ\text{C}$
- **Optical CCTV:** Visible plume signature (confidence $0.82$)

This creates multiple independent, corroborating evidence channels for future risk assessment.
