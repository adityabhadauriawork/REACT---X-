# Facility Thermal Radiometric Vision Architecture

**System:** REACT-X / SIH26162  
**Document Version:** 1.0.0 (Phase 13 Vision Foundation)  
**Classification:** Plant Computer Vision & Thermal Sensing  

---

## 1. Overview & Operational Role

While satellite infrared sensors provide broad regional situational awareness (15 min – 12 hr cadence), facility-installed **Thermal Radiometric Cameras** operate at seconds-level cadence (1–10 FPS), monitoring critical process units, storage spheres, and cryogenic tank skin temperatures.

Phase 13 establishes an edge-first computer vision pipeline that transforms continuous pixel matrices into **structured, quality-verified visual evidence**.

---

## 2. Radiometric Thermal Processing Pipeline

```
+-------------------------------------------------------------------------+
|                  PLANT THERMAL RADIOMETRIC CAMERA                       |
|               (e.g. FLIR A-Series, Optris PI, Axis Q29)                 |
+-------------------------------------------------------------------------+
                                     | (RTSP / ONVIF / Direct Matrix)
                                     v
+-------------------------------------------------------------------------+
|                    REACT-X CAMERA SOURCE ADAPTER                        |
|                  (ThermalCameraAdapter / Simulator)                     |
+-------------------------------------------------------------------------+
                                     | (H x W Temperature Matrix in °C)
                                     v
+-------------------------------------------------------------------------+
|                    RADIOMETRIC EXTRACTION ENGINE                        |
|    - Min, Max, Mean, 95th Percentile Temperatures                       |
|    - Zone Baseline Delta (ΔT = T_max - T_baseline)                     |
|    - Rate of Temperature Rise (dT/dt in °C/min)                         |
+-------------------------------------------------------------------------+
                                     |
                                     v
+-------------------------------------------------------------------------+
|                   SPATIAL HOTSPOT TRACKING ENGINE                       |
|    - Threshold Segmentation & Contour Detection                         |
|    - Centroid Matching & Multi-Frame Persistence Tracking               |
|    - Spatial Area Growth Rate (% / sec)                                 |
+-------------------------------------------------------------------------+
                                     |
                                     v
+-------------------------------------------------------------------------+
|                  QUALITY & TEMPORAL CONSISTENCY ENGINE                  |
|    - Frozen Stream Detection (Zero variance across time)                |
|    - Clock Skew & Blur / Occlusion Checks                               |
|    - Multi-Frame Confirmation (WATCH -> ABNORMAL -> CRITICAL)          |
+-------------------------------------------------------------------------+
                                     |
                                     v
+-------------------------------------------------------------------------+
|                    UNIFIED VISUAL EVIDENCE CONTRACT                     |
|    - VisualEvidence (Type: THERMAL_HOTSPOT, Rate of Rise, URI)          |
|    - Multi-Modal Cross-Correlation with Facility Telemetry              |
+-------------------------------------------------------------------------+
```

---

## 3. Mathematical Foundations

### A. Temperature Distribution
For a radiometric frame $F \in \mathbb{R}^{H \times W}$:
$$T_{\text{max}} = \max_{(x,y)} F(x,y), \quad T_{\text{mean}} = \frac{1}{HW}\sum_{x,y} F(x,y)$$

### B. Rate-of-Rise ($dT/dt$)
$$\frac{dT}{dt} = \left(\frac{T_{\text{max}}(t) - T_{\text{max}}(t - \Delta t)}{\Delta t}\right) \times 60 \quad [^\circ\text{C}/\text{min}]$$

### C. Spatial Hotspot Tracking
Hotspots are segmented using dynamic baseline offsets:
$$\text{HotspotMask}(x,y) = F(x,y) \ge T_{\text{threshold}}$$
Tracked across frames via Euclidean centroid distance $\Delta d < 0.15$ (normalized space).

---

## 4. Hardware Connectivity Status

> [!NOTE]
> **CURRENT DEPLOYMENT STATUS:**  
> **REAL THERMAL CAMERA HARDWARE NOT YET CONNECTED; INTERFACE READY.**  
> 
> The system operates in high-fidelity radiometric simulation mode with full support for scenarios: `NORMAL`, `GRADUAL_HEATING`, `LOCAL_HOTSPOT`, `RAPID_HEATING`, `HOTSPOT_GROWTH`, `MULTIPLE_HOTSPOTS`, and `CAMERA_FAILURE`.
