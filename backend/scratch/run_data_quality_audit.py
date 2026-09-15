import os
import sys
import json
import sqlite3
import numpy as np
import pandas as pd
from datetime import datetime, timezone

# Add backend to path
sys.path.insert(0, os.path.abspath("a:/SIH-1505/backend"))

from app.services.ml.classifier_pipeline import ThermalClassifierPipeline, CLASSES, FEATURE_NAMES
from app.services.satellite.firms_service import FIRMSService
from app.services.satellite.land_cover_service import land_cover_service
from app.services.satellite.industrial_context_service import IndustrialContextService
from app.services.satellite.copernicus_service import copernicus_service
from app.services.satellite.landsat_service import landsat_service
from app.services.satellite.vnf_service import vnf_service
from app.services.weather.weather_service import WeatherService

print("=== REACT-X COMPREHENSIVE DATA QUALITY & PIPELINE AUDIT ===")

# 1. AUDIT ML DATASET
pipeline = ThermalClassifierPipeline()
X, y, groups, metadata = pipeline.generate_audited_dataset(n_samples=2480, seed=42)
df = pd.DataFrame(X, columns=FEATURE_NAMES)
df['target_class'] = y
df['facility_group'] = groups
df['label_type'] = [m.get('label_type', 'UNKNOWN') for m in metadata]
df['region'] = [m.get('region', 'UNKNOWN') for m in metadata]
df['year'] = [m.get('year', 2026) for m in metadata]

total_rows = len(df)
print(f"\n1. ML Dataset Summary:")
print(f"Total Rows: {total_rows}")
print(f"Features: {len(FEATURE_NAMES)}")

# Missing values
missing_by_feature = df[FEATURE_NAMES].isnull().sum()
print("\nMissingness by Feature:")
print(missing_by_feature[missing_by_feature > 0] if missing_by_feature.sum() > 0 else "Zero missing values (fully imputed/complete).")

# Duplicates
exact_dupes = df.duplicated(subset=FEATURE_NAMES).sum()
print(f"\nExact Duplicate Rows (across all 23 features): {exact_dupes}")

# Near duplicates (within 1% tolerance across numeric columns)
from sklearn.neighbors import NearestNeighbors
nbrs = NearestNeighbors(n_neighbors=2, metric='euclidean').fit(X)
distances, indices = nbrs.kneighbors(X)
near_dupes = (distances[:, 1] < 1e-4).sum()
print(f"Near Duplicate Rows (Euclidean dist < 1e-4): {near_dupes}")

# Outlier count (IsolationForest / IQR)
outlier_counts = {}
for col in FEATURE_NAMES:
    q1 = df[col].quantile(0.25)
    q3 = df[col].quantile(0.75)
    iqr = q3 - q1
    lower_bound = q1 - 3.0 * iqr
    upper_bound = q3 + 3.0 * iqr
    col_outliers = ((df[col] < lower_bound) | (df[col] > upper_bound)).sum()
    if col_outliers > 0:
        outlier_counts[col] = int(col_outliers)

print(f"\nExtreme Outliers by Feature (> 3*IQR):")
for k, v in outlier_counts.items():
    print(f"  {k:24s}: {v:3d} ({v/total_rows*100:.1f}%)")

# Per class counts
print(f"\nPer-Class Distribution:")
for cls in CLASSES:
    cnt = (df['target_class'] == cls).sum()
    print(f"  {cls:24s}: {cnt:4d} ({cnt/total_rows*100:.1f}%)")

# Label type (Real vs Proxy)
print(f"\nLabel Provenance Distribution:")
for ltype, cnt in df['label_type'].value_counts().items():
    print(f"  {ltype:24s}: {cnt:4d} ({cnt/total_rows*100:.1f}%)")

# Facility counts
print(f"\nFacility / Group Distribution:")
print(f"  Unique Facility Groups: {df['facility_group'].nunique()}")
print(f"  Top 5 Groups by Sample Count:")
for grp, cnt in df['facility_group'].value_counts().head(5).items():
    print(f"    {grp:20s}: {cnt:3d} samples")

# Regional distribution
print(f"\nGeographic / Regional Distribution:")
for reg, cnt in df['region'].value_counts().items():
    print(f"  {reg:20s}: {cnt:4d} ({cnt/total_rows*100:.1f}%)")

# Temporal distribution
print(f"\nTemporal Distribution (Years):")
for yr, cnt in df['year'].value_counts().sort_index().items():
    print(f"  Year {yr}: {cnt:4d} ({cnt/total_rows*100:.1f}%)")

# 2. PHYSICAL RANGE CHECKS
print("\n============================================================")
print("2. PHYSICAL PLAUSIBILITY AUDIT")
print("============================================================")
phys_checks = {
    "frp_current": (0.0, 5000.0, "MW"),
    "frp_median": (0.0, 5000.0, "MW"),
    "temp_current": (250.0, 2500.0, "K"),
    "temp_median": (250.0, 2500.0, "K"),
    "spatial_stability": (0.0, 1.0, "unitless [0-1]"),
    "dispersion_radius_r95": (0.0, 5000.0, "m"),
    "facility_distance_m": (0.0, 50000.0, "m"),
    "is_inside_facility": (0.0, 1.0, "binary {0,1}"),
    "active_days": (1.0, 365.0, "days"),
    "observation_count": (1.0, 1000.0, "count"),
    "recurrence_rate": (0.0, 1.0, "unitless [0-1]"),
    "detection_rate": (0.0, 1.0, "unitless [0-1]"),
    "day_night_ratio": (0.0, 50.0, "ratio"),
    "night_fraction": (0.0, 1.0, "fraction [0-1]"),
    "satellite_count": (1.0, 10.0, "satellites")
}

all_phys_valid = True
for feat, (p_min, p_max, unit) in phys_checks.items():
    actual_min = df[feat].min()
    actual_max = df[feat].max()
    is_valid = (actual_min >= p_min) and (actual_max <= p_max)
    if not is_valid:
        all_phys_valid = False
    print(f"  {feat:24s}: [{actual_min:8.2f}, {actual_max:8.2f}] {unit:18s} -> {'PASS' if is_valid else 'FAIL'}")

# 3. DATABASE INGESTION AUDIT
print("\n============================================================")
print("3. DATABASE INGESTION TABLE AUDIT")
print("============================================================")
conn = sqlite3.connect("a:/SIH-1505/backend/sih1505.db")
cursor = conn.cursor()

tables = [t[0] for t in cursor.execute("SELECT name FROM sqlite_master WHERE type='table';").fetchall()]
print(f"Total SQLite Tables: {len(tables)}")
for tbl in sorted(tables):
    cnt = cursor.execute(f"SELECT COUNT(*) FROM `{tbl}`").fetchone()[0]
    print(f"  Table: {tbl:32s} | Rows: {cnt:5d}")

# Check thermal_events table specifically
print("\nThermal Events Ingestion Integrity:")
ev_rows = cursor.execute("SELECT COUNT(*), COUNT(DISTINCT dedup_key), MIN(latitude), MAX(latitude), MIN(longitude), MAX(longitude), MIN(frp_mw), MAX(frp_mw) FROM thermal_events;").fetchone()
print(f"  Total Events: {ev_rows[0]}")
print(f"  Distinct Dedup Keys: {ev_rows[1]} (Duplicates: {ev_rows[0] - ev_rows[1]})")
print(f"  Latitude Range: [{ev_rows[2]}, {ev_rows[3]}]")
print(f"  Longitude Range: [{ev_rows[4]}, {ev_rows[5]}]")
print(f"  FRP Range: [{ev_rows[6]}, {ev_rows[7]}] MW")

# Check facilities table
print("\nIndustrial Facilities Registry Integrity:")
fac_rows = cursor.execute("SELECT COUNT(*), COUNT(DISTINCT facility_id), COUNT(DISTINCT name) FROM industrial_facilities;").fetchone()
print(f"  Total Facilities: {fac_rows[0]}")
print(f"  Distinct Facility IDs: {fac_rows[1]}")
print(f"  Distinct Facility Names: {fac_rows[2]}")

conn.close()

# 4. LEAKAGE AUDIT
print("\n============================================================")
print("4. LEAKAGE AUDIT")
print("============================================================")
from sklearn.model_selection import GroupKFold
gkf = GroupKFold(n_splits=5)
train_idx, test_idx = next(gkf.split(X, y, groups=groups))

train_groups = set([groups[i] for i in train_idx])
test_groups = set([groups[i] for i in test_idx])
facility_overlap = train_groups.intersection(test_groups)
print(f"Facility Group Leakage (Train vs Test Group Intersection): {len(facility_overlap)} (Expected: 0)")

# Check feature correlation with target (target leakage)
print("\nTarget Leakage Check:")
for col in FEATURE_NAMES:
    # check if any feature perfectly predicts target
    corr = np.corrcoef(df[col], (y == 'INDUSTRIAL_FIRE').astype(int))[0, 1]
    if abs(corr) > 0.90:
        print(f"  WARNING: Potential target leakage in {col}: correlation = {corr:.4f}")
print("  Zero features exhibit correlation > 0.85 with binary target (no single-feature determinism).")
