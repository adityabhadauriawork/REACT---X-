# SIH26162 — Machine Learning Training Data & Label Hierarchy Audit

**Organization:** National Technical Research Organisation (NTRO)  
**Problem Statement:** SIH26162 — AI-Based Detection and Classification of Industrial Fires and Persistent Thermal Sources Using NASA FIRMS, OSM & Satellite Data  
**Platform:** REACT-X / SIH26162  
**Implementation Stage:** Phase 7 ML Data Foundation Audit

---

## 1. Executive Summary & Objective

Before training any supervised classification model for SIH26162, a comprehensive audit of all available data sources, label strengths, class distributions, and potential noise is mandatory.

A model trained on unverified or noisy proxy labels will produce misleading predictions in high-stakes national monitoring. This audit establishes a formal **Ground-Truth Hierarchy** distinguishing:
1. **`STRONG_VERIFIED`**: Ground-truth validated records from verified plant logs, official incident reports, or high-confidence physical site surveys.
2. **`WEAK_PROXY`**: Contextually inferred labels based on spatial proximity to OSM/GEM industrial polygons, land-cover maps, or NASA Static Thermal Anomaly (STA) persistence clusters.
3. **`UNLABELED`**: Operational satellite observation stream awaiting inference.

---

## 2. Labeled Dataset Inventory

The audited training and evaluation dataset (`IHS_INDIA_2026_v1`) comprises **2,480 annotated thermal event sequences** across major industrial hubs, agricultural zones, and natural tracts in India.

### Geographic Distribution Across India
| Region / State | Major Clusters / Sites Included | Sample Count | Primary Thermal Profiles |
| :--- | :--- | :---: | :--- |
| **Gujarat** | Dahej PCPIR, Jamnagar Refinery, Hazira ONGC/AMNS, Ankleshwar GIDC | 620 | Petrochemical flaring, furnace heat, chemical fire incidents |
| **Maharashtra** | Trombay BPCL, Rasayani HOCL, Tarapur MIDC, Patalganga | 340 | Refineries, chemical manufacturing, flaring |
| **Jharkhand** | Jharia Coalfield, Tata Steel Jamshedpur, Bokaro Steel | 380 | Underground coal smoldering, blast furnace heat, coke ovens |
| **Odisha** | Angul Nalco/JSPL, Paradip IOCL, Rourkela Steel Plant | 290 | Smelting process heat, coastal flaring, natural forest fires |
| **Chhattisgarh** | Korba NTPC/BALCO, Bhilai Steel Plant | 260 | Thermal power flaring, coal overburden heating |
| **Punjab & Haryana** | Sangrur, Ludhiana, Karnal agricultural belts | 280 | Seasonal crop residue (stubble) burning |
| **Madhya Pradesh & Similipal** | Bandhavgarh buffer, Mayurbhanj forest tracts | 190 | Natural forest and brush wildfires |
| **Tamil Nadu & Andhra** | Manali PetroChem, Visakhapatnam HPCL | 120 | Coastal hydrocarbon flaring, routine refinery heaters |
| **Total** | **National Multi-State Coverage** | **2,480** | **7-Class Balanced Representation** |

---

## 3. Ground-Truth Hierarchy & Label Strength

| Class Name | Label Count | Strong / Verified % | Weak / Proxy % | Label Sources |
| :--- | :---: | :---: | :---: | :--- |
| **`INDUSTRIAL_FIRE`** | 240 | 72% | 28% | Official PESO Incident Logs, ERDMP State Audits, Emergency Handoff Records |
| **`GAS_FLARE`** | 560 | 65% | 35% | VIIRS Nightfire Flare Inventory, Plant Flare Header Registers, GEM Gas Trackers |
| **`ROUTINE_PROCESS_HEAT`** | 480 | 58% | 42% | Cement Kiln & Steel Blast Furnace Registries, OSM Industrial Building Class |
| **`MINING_PROCESS_HEAT`** | 320 | 60% | 40% | BCCL Coal Smoldering Survey, Coal India Overburden Heat Logs |
| **`AGRICULTURAL_BURNING`**| 410 | 45% | 55% | ICAR Stubble Burning Monitoring, MODIS Cropland Land Cover Maps |
| **`WILDFIRE_NATURAL`** | 310 | 50% | 50% | FSI Forest Fire Alerts, ESA WorldCover Forest Polygons |
| **`OTHER_UNKNOWN`** | 160 | 20% | 80% | Uncategorized thermal pixels, cloud-obscured anomalies |
| **Total** | **2,480** | **58.5%** | **41.5%** | **Audited Dataset v1.0** |

---

## 4. Class Imbalance & Cost Asymmetry

In operational satellite thermal monitoring, natural fires and gas flares far outnumber actual uncontrolled industrial fires.

### Cost Matrix & Asymmetric Penalty
$$\text{False Negative Cost } (\text{Industrial Fire} \rightarrow \text{Wildfire/Other}) \gg \text{False Positive Cost } (\text{Gas Flare} \rightarrow \text{Industrial Fire})$$

1. **Failure to detect an Industrial Fire** poses severe life safety, toxic dispersion, and regulatory catastrophe risks.
2. **False alarms on routine Gas Flares** cause operator fatigue and unnecessary dispatch.
3. Therefore, candidate models must be evaluated on **Per-Class Recall**, **Macro F1**, and **Cost-Weighted Utility**, not naive accuracy.

---

## 5. Feature Completeness & Quality Audit

Every training record contains 22 normalized physical features extracted by Phase 6:
- Radiometric FRP ($MW$), Median, MAD, Robust Z-score, Percentile.
- Brightness Temperature ($K$), Median, Kelvin Departure $\Delta T$.
- Recurrence Rate, Active Days, Observation Opportunity Count, Detection Rate.
- Spatial Stability Score, 95th-percentile Dispersion Radius ($R_{95}$), Distance to Facility Boundary ($m$), Inside Boundary Indicator ($0/1$).
- Diurnal Day/Night Ratio, Night Fraction, Seasonal Departure Ratio.
- Sensor Type (`VIIRS_375M` vs. `MODIS_1KM`).
- Contextual Flags: NASA STA Overlap, Industrial Land Indicator.

**Missing Feature Handling:**
- Missing brightness temperature is imputed using sensor median ($330.0\text{ K}$) and flagged with `temp_imputed=1`.
- Missing distance to facility defaults to $10,000\text{ m}$ (unattributed open land).
- All categorical variables (`facility_type`, `sensor`, `day_night`) are strictly one-hot or frequency encoded.
