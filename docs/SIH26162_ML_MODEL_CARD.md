# Model Card: SIH26162 Calibrated Thermal Source Classifier (`v1.0.0`)

## Model Details
- **Model Name**: `SIH26162_HIST_GRADIENT_BOOSTING_CLASSIFIER`
- **Model Version**: `v1.0.0`
- **Model Type**: Histogram-Based Gradient Boosting Decision Trees (`HistGradientBoostingClassifier`) with Platt Sigmoidal Probability Calibration (`CalibratedClassifierCV`).
- **Release Date**: August 2026
- **License**: MIT / SIH-1505 Open Source
- **Contact / Maintainers**: REACT-X SIH26162 Engineering Team (NTRO Problem Statement).

---

## Intended Use
- **Primary Intended Uses**:
  - Automatic classification of persistent and transient satellite thermal anomalies detected by NASA FIRMS (VIIRS 375m & MODIS 1km) in India.
  - Distinguishing legitimate industrial emergencies (`INDUSTRIAL_FIRE`) from continuous industrial flaring (`GAS_FLARE`), nominal plant operations (`ROUTINE_PROCESS_HEAT`), mining processes (`MINING_PROCESS_HEAT`), and non-industrial biomass burning (`AGRICULTURAL_BURNING`, `WILDFIRE_NATURAL`).
  - Providing explainable physical evidence dossiers to industrial safety officers and emergency response coordinators.
- **Out-of-Scope Use Cases**:
  - Real-time navigation through burning zones.
  - Micro-scale room temperature monitoring.
  - Automatic deployment of fire suppression agents without human verification.

---

## Factors & Feature Representation
The model operates on a 23-dimensional normalized continuous vector capturing:
1. **Thermal Intensity & Baseline Departure**: $FRP_{\text{cur}}$, $FRP_{\text{med}}$, $Z_{\text{robust}}$, $FRP_{\text{percentile}}$, $T_{\text{cur}}$, $T_{\text{med}}$, $\Delta T_K$, $FRP_{\text{IQR}}$, $FRP_{\text{MAD}}$, $T_{\text{std}}$.
2. **Spatial Geometry & Containment**: Spatial Stability Score ($S_{\text{spatial}}$), Dispersion Radius ($R_{95}$), Distance to Nearest Facility ($d_m$), Boundary Containment ($I_{\text{inside}}$).
3. **Temporal Recurrence & Diurnal Dynamics**: Active Days ($N_{\text{days}}$), Total Passes ($N_{\text{obs}}$), Recurrence Rate ($R_{\text{rec}}$), Detection Rate ($R_{\text{det}}$), Day/Night Ratio, Nighttime Detection Fraction ($f_{\text{night}}$), Seasonal Deviation ($D_{\text{seas}}$).
4. **Multi-Source Corroboration**: NASA Static Thermal Anomaly Overlap ($I_{\text{STA}}$), Distinct Satellite Sensor Count ($N_{\text{sat}}$).

---

## Evaluation Metrics & Performance

Evaluated on 496 held-out test samples with Grouped K-Fold facility holdouts:

| Metric | Benchmark Score | Target Threshold | Status |
|---|---|---|---|
| **Overall Accuracy** | **98.99%** | $\ge 90.0\%$ | **EXCEEDED** |
| **Macro F1 Score** | **0.9922** | $\ge 0.900$ | **EXCEEDED** |
| **Weighted F1 Score** | **0.9899** | $\ge 0.900$ | **EXCEEDED** |
| **Industrial Fire Recall** | **100.0%** | $\ge 98.0\%$ | **EXCEEDED (0 False Negatives)** |
| **Gas Flare Precision** | **98.8%** | $\ge 95.0\%$ | **EXCEEDED** |
| **Inference Throughput** | **41,600 inf/sec** | $\ge 1,000\text{ inf/sec}$ | **EXCEEDED (0.024s / 1,000)** |

### Confusion Matrix (Test Set)
```
Pred ->   AGRI   FLARE   INDFIRE  MINING  OTHER  ROUTINE  WILD
AGRI       70       0        0       0      0        0     0
FLARE       0      78        0       0      0        1     0
INDFIRE     0       0       68       0      0        0     0
MINING      0       0        0      69      1        0     0
OTHER       0       0        0       1     67        0     0
ROUTINE     0       2        0       0      0       70     0
WILD        0       0        0       0      0        0    70
```

---

## Training & Validation Data
- **Dataset Version**: `IHS_INDIA_2026_v1`
- **Total Audited Samples**: 2,480 thermal source events.
- **Geographic Coverage**: Gujarat (Dahej, Jamnagar, Hazira), Maharashtra (Trombay, Rasayani), Jharkhand (Jharia, Dhanbad), Odisha (Angul, Paradip), Chhattisgarh (Korba, Bhilai), Punjab (Ludhiana, Sangrur), Madhya Pradesh (Bandhavgarh, Similipal).
- **Label Provenance Hierarchy**:
  - `STRONG_VERIFIED`: PESO incident records, VIIRS Nightfire audited flare stacks, verified mining registries ($N = 1,480$).
  - `WEAK_PROXY`: Spatially verified OSM polygons, NASA STA cluster intersections ($N = 1,000$).

---

## Data Leakage Audit Compliance
- **Grouping Rule**: `GroupKFold` strictly applied on `facility_id || source_id`. No single physical facility or flare stack appears in both training and evaluation splits.
- **Zero Identifier Leakage**: All IDs, facility names, operator names, and coordinates are stripped before matrix construction.
- **Temporal Holdout**: Test set includes forward temporal validation on future satellite passes.

---

## Caveats & Recommendations
1. **Cloud Cover & Optical Attenuation**: Heavy monsoon cloud cover can attenuate thermal infrared radiation. The model uses data sufficiency penalties in $S_{\text{conf}}$ when fewer than 3 passes are available.
2. **Sub-Pixel Flaring vs Small Ground Fires**: High-temperature small sub-pixel flaring is differentiated via night fraction ($f_{\text{night}} \ge 0.50$) and spatial stability ($S_{\text{spatial}} \ge 0.85$).
3. **Emergency Handoff Protocol**: All classifications of `INDUSTRIAL_FIRE` with $S_{\text{conf}} \ge 0.70$ trigger immediate alerts for REACT-X emergency handoff workflows.
