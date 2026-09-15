import json
from app.services.ml.thermal_classifier_service import ThermalClassifierService

svc = ThermalClassifierService()

test_cases = [
    ("Hot Asphalt Road", {
        "frp_current": 0.8, "frp_median": 0.5, "frp_mad": 0.3, "frp_iqr": 0.4, "frp_robust_zscore": 0.6,
        "frp_percentile": 52.0, "temp_current": 324.0, "temp_median": 320.0, "temp_percentile": 55.0,
        "temp_departure_k": 4.0, "spatial_stability": 0.30, "dispersion_radius_r95": 800.0,
        "facility_distance_m": 3500.0, "is_inside_facility": 0.0, "active_days": 15, "observation_count": 18,
        "recurrence_rate": 0.15, "detection_rate": 0.20, "day_night_ratio": 12.0, "night_fraction": 0.02,
        "seasonal_deviation": 2.5, "sta_overlap": 0.0, "satellite_count": 1
    }),
    ("Metal Industrial Roof", {
        "frp_current": 1.5, "frp_median": 1.0, "frp_mad": 0.4, "frp_iqr": 0.6, "frp_robust_zscore": 0.8,
        "frp_percentile": 55.0, "temp_current": 328.0, "temp_median": 322.0, "temp_percentile": 58.0,
        "temp_departure_k": 6.0, "spatial_stability": 0.65, "dispersion_radius_r95": 350.0,
        "facility_distance_m": 50.0, "is_inside_facility": 1.0, "active_days": 20, "observation_count": 25,
        "recurrence_rate": 0.22, "detection_rate": 0.25, "day_night_ratio": 10.0, "night_fraction": 0.05,
        "seasonal_deviation": 2.2, "sta_overlap": 0.0, "satellite_count": 2
    }),
    ("Solar Panel Field", {
        "frp_current": 0.5, "frp_median": 0.4, "frp_mad": 0.2, "frp_iqr": 0.3, "frp_robust_zscore": 0.3,
        "frp_percentile": 51.0, "temp_current": 322.0, "temp_median": 319.0, "temp_percentile": 54.0,
        "temp_departure_k": 3.0, "spatial_stability": 0.40, "dispersion_radius_r95": 600.0,
        "facility_distance_m": 4200.0, "is_inside_facility": 0.0, "active_days": 25, "observation_count": 30,
        "recurrence_rate": 0.28, "detection_rate": 0.30, "day_night_ratio": 15.0, "night_fraction": 0.01,
        "seasonal_deviation": 2.0, "sta_overlap": 0.0, "satellite_count": 1
    }),
    ("Dry Bare Soil", {
        "frp_current": 1.2, "frp_median": 0.8, "frp_mad": 0.3, "frp_iqr": 0.5, "frp_robust_zscore": 0.9,
        "frp_percentile": 56.0, "temp_current": 326.0, "temp_median": 321.0, "temp_percentile": 57.0,
        "temp_departure_k": 5.0, "spatial_stability": 0.25, "dispersion_radius_r95": 900.0,
        "facility_distance_m": 6500.0, "is_inside_facility": 0.0, "active_days": 12, "observation_count": 14,
        "recurrence_rate": 0.12, "detection_rate": 0.15, "day_night_ratio": 9.0, "night_fraction": 0.04,
        "seasonal_deviation": 2.8, "sta_overlap": 0.0, "satellite_count": 1
    }),
    ("Dark Warehouse Roof", {
        "frp_current": 2.0, "frp_median": 1.2, "frp_mad": 0.5, "frp_iqr": 0.7, "frp_robust_zscore": 1.0,
        "frp_percentile": 58.0, "temp_current": 330.0, "temp_median": 324.0, "temp_percentile": 60.0,
        "temp_departure_k": 6.0, "spatial_stability": 0.70, "dispersion_radius_r95": 300.0,
        "facility_distance_m": 80.0, "is_inside_facility": 1.0, "active_days": 22, "observation_count": 28,
        "recurrence_rate": 0.24, "detection_rate": 0.28, "day_night_ratio": 8.0, "night_fraction": 0.06,
        "seasonal_deviation": 2.1, "sta_overlap": 0.0, "satellite_count": 2
    }),
    ("Cloud / Shadow Contaminated", {
        "frp_current": 3.5, "frp_median": 3.0, "frp_mad": 1.0, "frp_iqr": 1.5, "frp_robust_zscore": 0.3,
        "frp_percentile": 52.0, "temp_current": 295.0, "temp_median": 320.0, "temp_percentile": 20.0,
        "temp_departure_k": -25.0, "spatial_stability": 0.15, "dispersion_radius_r95": 1200.0,
        "facility_distance_m": 2000.0, "is_inside_facility": 0.0, "active_days": 2, "observation_count": 3,
        "recurrence_rate": 0.02, "detection_rate": 0.05, "day_night_ratio": 1.0, "night_fraction": 0.30,
        "seasonal_deviation": 0.5, "sta_overlap": 0.0, "satellite_count": 1
    }),
    ("Mixed Pixel (Factory + Road)", {
        "frp_current": 6.0, "frp_median": 5.0, "frp_mad": 1.2, "frp_iqr": 1.8, "frp_robust_zscore": 0.6,
        "frp_percentile": 55.0, "temp_current": 332.0, "temp_median": 328.0, "temp_percentile": 56.0,
        "temp_departure_k": 4.0, "spatial_stability": 0.55, "dispersion_radius_r95": 450.0,
        "facility_distance_m": 220.0, "is_inside_facility": 0.0, "active_days": 18, "observation_count": 24,
        "recurrence_rate": 0.20, "detection_rate": 0.22, "day_night_ratio": 4.0, "night_fraction": 0.15,
        "seasonal_deviation": 1.5, "sta_overlap": 0.0, "satellite_count": 2
    }),
    ("Sun-Glint Reflective Surface", {
        "frp_current": 1.0, "frp_median": 0.5, "frp_mad": 0.3, "frp_iqr": 0.4, "frp_robust_zscore": 1.1,
        "frp_percentile": 60.0, "temp_current": 335.0, "temp_median": 320.0, "temp_percentile": 68.0,
        "temp_departure_k": 15.0, "spatial_stability": 0.45, "dispersion_radius_r95": 550.0,
        "facility_distance_m": 600.0, "is_inside_facility": 0.0, "active_days": 8, "observation_count": 10,
        "recurrence_rate": 0.08, "detection_rate": 0.10, "day_night_ratio": 20.0, "night_fraction": 0.0,
        "seasonal_deviation": 3.0, "sta_overlap": 0.0, "satellite_count": 1
    }),
    ("Routine Gas Flare", {
        "frp_current": 24.5, "frp_median": 22.0, "frp_mad": 3.5, "frp_iqr": 5.0, "frp_robust_zscore": 0.5,
        "frp_percentile": 54.0, "temp_current": 365.0, "temp_median": 360.0, "temp_percentile": 55.0,
        "temp_departure_k": 5.0, "spatial_stability": 0.95, "dispersion_radius_r95": 120.0,
        "facility_distance_m": 10.0, "is_inside_facility": 1.0, "active_days": 85, "observation_count": 160,
        "recurrence_rate": 0.94, "detection_rate": 0.88, "day_night_ratio": 1.1, "night_fraction": 0.52,
        "seasonal_deviation": 1.0, "sta_overlap": 1.0, "satellite_count": 3
    }),
    ("Routine Process Heat", {
        "frp_current": 12.0, "frp_median": 11.5, "frp_mad": 1.8, "frp_iqr": 2.5, "frp_robust_zscore": 0.2,
        "frp_percentile": 52.0, "temp_current": 345.0, "temp_median": 342.0, "temp_percentile": 53.0,
        "temp_departure_k": 3.0, "spatial_stability": 0.92, "dispersion_radius_r95": 140.0,
        "facility_distance_m": 20.0, "is_inside_facility": 1.0, "active_days": 80, "observation_count": 140,
        "recurrence_rate": 0.89, "detection_rate": 0.85, "day_night_ratio": 1.2, "night_fraction": 0.48,
        "seasonal_deviation": 1.0, "sta_overlap": 1.0, "satellite_count": 3
    }),
    ("Real Industrial Fire Escalation", {
        "frp_current": 145.0, "frp_median": 15.0, "frp_mad": 2.5, "frp_iqr": 4.0, "frp_robust_zscore": 35.0,
        "frp_percentile": 99.9, "temp_current": 450.0, "temp_median": 340.0, "temp_percentile": 99.9,
        "temp_departure_k": 110.0, "spatial_stability": 0.88, "dispersion_radius_r95": 200.0,
        "facility_distance_m": 15.0, "is_inside_facility": 1.0, "active_days": 35, "observation_count": 50,
        "recurrence_rate": 0.40, "detection_rate": 0.45, "day_night_ratio": 1.3, "night_fraction": 0.45,
        "seasonal_deviation": 1.2, "sta_overlap": 1.0, "satellite_count": 3
    }),
    ("Wildfire / Forest Fire", {
        "frp_current": 85.0, "frp_median": 5.0, "frp_mad": 2.0, "frp_iqr": 3.0, "frp_robust_zscore": 26.0,
        "frp_percentile": 99.5, "temp_current": 410.0, "temp_median": 315.0, "temp_percentile": 99.0,
        "temp_departure_k": 95.0, "spatial_stability": 0.20, "dispersion_radius_r95": 2500.0,
        "facility_distance_m": 12000.0, "is_inside_facility": 0.0, "active_days": 3, "observation_count": 8,
        "recurrence_rate": 0.03, "detection_rate": 0.05, "day_night_ratio": 1.8, "night_fraction": 0.35,
        "seasonal_deviation": 3.5, "sta_overlap": 0.0, "satellite_count": 2
    }),
    ("Agricultural Crop Burning", {
        "frp_current": 28.0, "frp_median": 2.0, "frp_mad": 1.0, "frp_iqr": 1.5, "frp_robust_zscore": 17.5,
        "frp_percentile": 98.0, "temp_current": 365.0, "temp_median": 310.0, "temp_percentile": 96.0,
        "temp_departure_k": 55.0, "spatial_stability": 0.15, "dispersion_radius_r95": 3200.0,
        "facility_distance_m": 18000.0, "is_inside_facility": 0.0, "active_days": 2, "observation_count": 3,
        "recurrence_rate": 0.02, "detection_rate": 0.03, "day_night_ratio": 8.0, "night_fraction": 0.08,
        "seasonal_deviation": 4.0, "sta_overlap": 0.0, "satellite_count": 2
    }),
    ("Mining Open Cast Process Heat", {
        "frp_current": 35.0, "frp_median": 30.0, "frp_mad": 4.0, "frp_iqr": 6.0, "frp_robust_zscore": 0.8,
        "frp_percentile": 62.0, "temp_current": 355.0, "temp_median": 350.0, "temp_percentile": 60.0,
        "temp_departure_k": 5.0, "spatial_stability": 0.78, "dispersion_radius_r95": 650.0,
        "facility_distance_m": 1800.0, "is_inside_facility": 0.0, "active_days": 60, "observation_count": 90,
        "recurrence_rate": 0.67, "detection_rate": 0.60, "day_night_ratio": 1.5, "night_fraction": 0.40,
        "seasonal_deviation": 1.1, "sta_overlap": 1.0, "satellite_count": 2
    }),
    ("Out-of-Distribution / Unknown Thermal Emitter", {
        "frp_current": 600.0, "frp_median": 1.0, "frp_mad": 0.2, "frp_iqr": 0.3, "frp_robust_zscore": 2000.0,
        "frp_percentile": 99.9, "temp_current": 950.0, "temp_median": 300.0, "temp_percentile": 99.9,
        "temp_departure_k": 650.0, "spatial_stability": 0.01, "dispersion_radius_r95": 15000.0,
        "facility_distance_m": 45000.0, "is_inside_facility": 0.0, "active_days": 1, "observation_count": 1,
        "recurrence_rate": 0.01, "detection_rate": 0.01, "day_night_ratio": 0.0, "night_fraction": 1.0,
        "seasonal_deviation": 10.0, "sta_overlap": 0.0, "satellite_count": 1
    })
]

print(f"Running inference across {len(test_cases)} hard-negative and physical scenarios...")
for name, feats in test_cases:
    clean_id = f"SRC-{name.replace(' ', '_').replace('/', '_')}"
    res = svc.classify_features(feats, source_id=clean_id)
    print("----------------------------------------------------")
    print(f"CASE: {name}")
    print(f"  Predicted Class: {res.predicted_class}")
    print(f"  Classification State: {res.classification_state}")
    print(f"  System Confidence: {res.system_confidence}")
    is_ood = res.explanation.get("is_out_of_distribution", False) if isinstance(res.explanation, dict) else getattr(res.explanation, "is_out_of_distribution", False)
    print(f"  Is OOD: {is_ood}")
    sorted_probs = sorted(res.class_probabilities.items(), key=lambda x: x[1], reverse=True)
    print(f"  All Probabilities: {sorted_probs}")
