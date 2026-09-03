import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from sklearn.ensemble import IsolationForest

class FacilityAssetBaseline:
    def __init__(
        self,
        asset_id: str,
        temp_mean: float,
        temp_std: float,
        press_mean: float,
        press_std: float,
        gas_mean: float,
        gas_std: float,
        flow_mean: float,
        flow_std: float
    ):
        self.asset_id = asset_id
        self.temp_mean = temp_mean
        self.temp_std = temp_std
        self.press_mean = press_mean
        self.press_std = press_std
        self.gas_mean = gas_mean
        self.gas_std = gas_std
        self.flow_mean = flow_mean
        self.flow_std = flow_std

class FacilityAnomalyEngine:
    """
    Layer 2: Facility-Specific Multivariate Anomaly & Statistical Deviation Model.
    Extracts tabular features from Phase 12 process sensors and scores deviations
    against facility-calibrated operational baselines.
    """

    def __init__(self):
        self.baselines: Dict[str, FacilityAssetBaseline] = {
            "T-04": FacilityAssetBaseline(
                asset_id="T-04",
                temp_mean=-33.0,
                temp_std=1.0,
                press_mean=4.2,
                press_std=0.5,
                gas_mean=2.0,
                gas_std=2.5,
                flow_mean=120.0,
                flow_std=10.0
            ),
            "T-03": FacilityAssetBaseline(
                asset_id="T-03",
                temp_mean=24.0,
                temp_std=1.0,
                press_mean=10.5,
                press_std=0.4,
                gas_mean=0.2,
                gas_std=0.1,
                flow_mean=85.0,
                flow_std=4.0
            ),
            "PROC-01": FacilityAssetBaseline(
                asset_id="PROC-01",
                temp_mean=145.0,
                temp_std=3.5,
                press_mean=18.0,
                press_std=0.8,
                gas_mean=1.2,
                gas_std=0.5,
                flow_mean=310.0,
                flow_std=12.0
            )
        }
        self.iso_models: Dict[str, IsolationForest] = {}
        self._fit_models()

    def _fit_models(self):
        np.random.seed(42)
        n = 300
        for asset_id, b in self.baselines.items():
            t = np.random.normal(b.temp_mean, b.temp_std, n)
            p = np.random.normal(b.press_mean, b.press_std, n)
            g = np.random.normal(b.gas_mean, b.gas_std, n)
            f = np.random.normal(b.flow_mean, b.flow_std, n)
            data = np.column_stack([t, p, g, f])
            
            iso = IsolationForest(n_estimators=40, contamination=0.03, random_state=42)
            iso.fit(data)
            self.iso_models[asset_id] = iso

    def get_baseline(self, asset_id: str) -> FacilityAssetBaseline:
        return self.baselines.get(asset_id, self.baselines["T-04"])

    def score_observations(
        self,
        asset_id: str,
        temperature_c: float,
        pressure_bar: float,
        gas_ppm: float,
        flow_m3_h: float
    ) -> Dict[str, Any]:
        """
        Computes Layer 2 multivariate anomaly score and z-score baseline deviations.
        """
        base = self.get_baseline(asset_id)
        
        # Z-Scores
        z_t = (temperature_c - base.temp_mean) / max(0.01, base.temp_std)
        z_p = (pressure_bar - base.press_mean) / max(0.01, base.press_std)
        z_g = (gas_ppm - base.gas_mean) / max(0.01, base.gas_std)
        z_f = (flow_m3_h - base.flow_mean) / max(0.01, base.flow_std)

        feat_vector = np.array([[temperature_c, pressure_bar, gas_ppm, flow_m3_h]])
        iso_model = self.iso_models.get(asset_id)
        
        if iso_model:
            raw_decision = float(iso_model.decision_function(feat_vector)[0])
            # Sigmoid scaling
            iso_score = float(1.0 / (1.0 + np.exp(raw_decision * 7.5)))
        else:
            iso_score = 0.1

        # Max absolute Z-Score
        max_z = max(abs(z_t), abs(z_p), abs(z_g), abs(z_f))
        stat_score = min(1.0, max_z / 5.0)

        # Composite anomaly score
        composite_score = round(min(1.0, (iso_score * 0.6) + (stat_score * 0.4)), 3)
        is_anom = composite_score > 0.45 or max_z > 3.0

        return {
            "anomaly_score": composite_score,
            "is_anomaly": is_anom,
            "z_scores": {
                "temperature": round(z_t, 2),
                "pressure": round(z_p, 2),
                "gas": round(z_g, 2),
                "flow": round(z_f, 2)
            },
            "max_z_score": round(max_z, 2),
            "deltas_from_baseline": {
                "temperature_c": round(temperature_c - base.temp_mean, 2),
                "pressure_bar": round(pressure_bar - base.press_mean, 2),
                "gas_ppm": round(gas_ppm - base.gas_mean, 2)
            }
        }

facility_anomaly_engine = FacilityAnomalyEngine()
