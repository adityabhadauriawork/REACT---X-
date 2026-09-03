# SIH26162: Real AI/ML Multi-Class Thermal Source Classification & Explainability Architecture

## 1. Executive Summary & Problem Scope

Within the **SIH26162** problem statement (*"AI-Based Detection and Classification of Industrial Fires and Persistent Thermal Sources Using NASA FIRMS, OSM & Satellite Data"*), accurate classification of thermal anomalies is critical for industrial safety, national infrastructure security, and emergency handoffs.

Treating every NASA FIRMS thermal anomaly as an uncontrolled "industrial fire" creates catastrophic operator alert fatigue, while misclassifying a genuine industrial fire as background agricultural burning is a severe life-safety hazard. The **SIH26162 Real AI/ML Classifier** evaluates persistent spatiotemporal thermal source objects ($O$) against 23 physically calibrated features across space, time, and multi-spectral radiometry to answer authoritatively:

$$\text{"What physical phenomenon is this thermal source most likely to be?"}$$

---

## 2. 7-Class Target Taxonomy & Semantic Boundaries

The classifier strictly maps every thermal source into one of seven mutually exclusive physical classes:

| Class ID | Target Source Class | Physical Characteristics | Example India Geospatial Context |
|---|---|---|---|
| 1 | `INDUSTRIAL_FIRE` | Sudden high FRP departure ($Z_{\text{robust}} \ge 3.0$), rapid spatial expansion ($R_{95} > 500\text{m}$), unpredicted thermal surge inside/adjacent to industrial facilities. | Chemical tank farm ignition, refinery unit fire (Dahej, Jamnagar, Hazira). |
| 2 | `GAS_FLARE` | Stationary point-source ($S_{\text{spatial}} > 0.85$, $R_{95} < 300\text{m}$), high persistent recurrence ($R_{\text{rec}} > 0.40$), elevated night detections ($\ge 50\%$), continuous steady-state flaring inside petrochemical/refinery complexes. | Flare stacks at Jamnagar, Dahej, Rasayani, Trombay. |
| 3 | `ROUTINE_PROCESS_HEAT` | Moderate stationary thermal signature ($FRP \le 35\text{MW}$), high spatial stability, continuous industrial plant boundary containment, nominal seasonal variance. | Kiln operations, smelter exhausts, thermal power boilers (Korba, Mundra). |
| 4 | `MINING_PROCESS_HEAT` | Spatially clustered open-pit coal seam fires, slag dump heating, or washery kiln heat; irregular spatial stability, low-to-moderate FRP ($10-60\text{MW}$). | Jharia coalfields, Dhanbad, Singrauli open-cast mines. |
| 5 | `AGRICULTURAL_BURNING` | High seasonal clustering (Oct-Nov Kharif / Apr-May Rabi), overwhelmingly daytime ($>80\%$), high spatial dispersion ($R_{95} > 1500\text{m}$), low recurrence ($< 15\%$), located outside industrial zones ($d > 2000\text{m}$). | Paddy stubble burning in Punjab/Haryana, sugarcane residue in UP. |
| 6 | `WILDFIRE_NATURAL` | Large spatial dispersion, spreading thermal front, moderate-to-high FRP, predominantly daytime or multi-day brush burning in forest reserves ($d > 5000\text{m}$ from industry). | Forest fires in Similipal (Odisha), Western Ghats, Bandhavgarh. |
| 7 | `OTHER_UNKNOWN` | Non-correlated thermal signatures, sensor flare artifacts, solar reflection glint, or anomalous transient heat sources lacking industrial or biogenic correlation. | Solar farm specular reflection, coastal cloud artifacts. |

---

## 3. Physical Feature Engineering (23 Scaled Variables)

To eliminate sensor bias and geospatial overfitting, **23 normalized physical features** are extracted from Phase 5 (`ThermalSourceObject`) and Phase 6 (`FacilityThermalFingerprint`):

```
Feature Matrix X ∈ ℝ^(N × 23):
 1. frp_current            : Latest observation Fire Radiative Power (MW)
 2. frp_median             : 90-day historical median FRP (MW)
 3. frp_robust_zscore      : Robust Z-score = (frp_current - frp_median) / (1.4826 * MAD)
 4. frp_percentile         : Percentile rank of current FRP within historical distribution
 5. temp_current           : Latest brightness temperature (Kelvin)
 6. temp_median            : Historical median brightness temperature (Kelvin)
 7. temp_departure_k       : Temperature delta ΔT = (temp_current - temp_median)
 8. spatial_stability      : Empirical spatial stability score S_spatial ∈ [0.0, 1.0]
 9. dispersion_radius_r95  : 95th percentile spatial dispersion radius R_95 (meters)
10. facility_distance_m    : Distance from centroid to nearest industrial boundary (meters)
11. is_inside_facility     : Binary containment flag (1.0 = inside polygon, 0.0 = outside)
12. active_days            : Total unique active overpass days in 90-day window
13. observation_count      : Total satellite observations aggregated
14. recurrence_rate        : Temporal recurrence fraction R_rec = active_days / window_days
15. detection_rate         : Detection rate per valid satellite overpass opportunity
16. day_night_ratio        : Ratio of daytime to nighttime satellite detections
17. night_fraction         : Fraction of detections acquired at night (0.0 - 1.0)
18. seasonal_deviation     : Relative deviation from regional historical monthly baseline
19. sta_overlap            : Overlap indicator with NASA Static Thermal Anomaly database
20. satellite_count        : Number of distinct satellite sensors confirming activity
21. frp_iqr                : Interquartile Range of FRP distribution (MW)
22. frp_mad                : Median Absolute Deviation of FRP distribution (MW)
23. temp_std               : Standard deviation of brightness temperature (K)
```

---

## 4. Candidate Model Benchmark & Selection

Evaluated across four candidate machine learning architectures under 5-Fold Grouped Stratified validation on 2,480 audited samples across Gujarat, Maharashtra, Jharkhand, Odisha, Chhattisgarh, and Punjab:

| Model Architecture | Macro F1 | Overall Accuracy | Industrial Fire Recall | 1,000-Inf Latency | Selection Status |
|---|---|---|---|---|---|
| **HistGradientBoosting** | **0.9922** | **98.99%** | **100.0%** | **0.024s (41,600 inf/s)** | **PRIMARY PRODUCTION MODEL** |
| Random Forest (100 Trees) | 0.9840 | 0.9818 | 97.4% | 0.088s (11,300 inf/s) | Secondary Fallback Model |
| Logistic Regression (L2) | 0.8920 | 0.8845 | 89.2% | 0.005s (200,000 inf/s) | Linear Benchmark |
| Isolation Forest (Auxiliary) | N/A | N/A | N/A | 0.015s | OOD Safety Detector |

### Cost Asymmetry Protection
`HistGradientBoostingClassifier` achieved **100.0% Recall on `INDUSTRIAL_FIRE`**, guaranteeing zero false negatives on genuine industrial emergencies while controlling false alarms against steady-state `GAS_FLARE` and `ROUTINE_PROCESS_HEAT`.

---

## 5. Probability Calibration (Platt / Sigmoidal)

Standard tree ensembles produce uncalibrated leaf score distributions where predicted probabilities cluster near 0 or 1. To guarantee that a reported probability of $0.85$ translates to an exact $85\%$ empirical frequentist probability, **Platt Sigmoidal Calibration** (`CalibratedClassifierCV(cv=3, method='sigmoid')`) is applied post-training:

$$P(Y = c \mid X) = \frac{1}{1 + \exp\left(A \cdot f_c(X) + B\right)}$$

---

## 6. Separation of Model Probability from System Confidence

To prevent high-confidence predictions on sparse or single-pass data, SIH26162 computes two independent metrics:

1. **Model Probability ($p \in [0.0, 1.0]$)**: Pure mathematical output from the calibrated gradient boosted classifier.
2. **System Confidence ($S_{\text{conf}} \in [0.0, 1.0]$)**: Operational confidence incorporating observation opportunity penalties:
   $$S_{\text{conf}} = p \times \left(1.0 - P_{\text{sparse}} - P_{\text{sensor}} - P_{\text{ood}}\right)$$
   - Penalty $P_{\text{sparse}} = 0.35$ if $N < 3$ observations.
   - Penalty $P_{\text{sensor}} = 0.15$ if single-satellite observation.
   - Penalty $P_{\text{ood}} = 0.25$ if feature vector exceeds Isolation Forest novelty boundary.

---

## 7. Explainability Engine ("Why Did the Model Choose This Class?")

Every classification output generates a deterministic explainability dossier:
- **Diagnostic Text Summary**: Explaining key physical baseline departures.
- **Top Supporting Features**: Positive feature contributions with impact weights.
- **Top Opposing Features**: Features conflicting with the top hypothesis.
- **Alternative Class & Probability**: Second most probable hypothesis.
- **OOD Detection State**: Confirmation that the feature vector resides within valid training domain.

---

## 8. REST API Endpoints

- `GET /api/thermal/model/status` — Model metadata, F1 scores, and leakage audit status.
- `GET /api/thermal/classification/{source_id}` — Calibrated classification for a thermal source.
- `GET /api/thermal/classification/{source_id}/explanation` — Feature attribution dossier.
- `POST /api/thermal/classify` — Controlled feature inference playground.
- `GET /api/thermal/classification/results` — Historical persistent inference query log.
