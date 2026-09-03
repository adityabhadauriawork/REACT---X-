import math
import numpy as np
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
from app.schemas.canonical import CanonicalEvent, DataClassification, DataQualityFlag
from app.services.ingestion.rolling_buffer import rolling_buffer

class StreamRouter:
    """
    Decision-value-based stream router:
    Directs observations to rolling buffers, derives moving features,
    and forwards critical anomalies to the Hot Path without database write saturation.
    """
    def __init__(self):
        self.hot_subscribers = []
        self.warm_aggregates: Dict[str, Dict[str, Any]] = {}

    def route_event(self, event: Any) -> Dict[str, Any]:
        # 1. Always append to in-memory rolling buffer
        rolling_buffer.append(event)

        asset_id = getattr(event, "asset_id", "UNKNOWN")
        signal_id = getattr(event, "signal_id", getattr(event, "sensor_id", "UNKNOWN"))
        unit = getattr(event, "unit", "")
        value = getattr(event, "value", getattr(event, "reading_value", 0.0))
        quality = getattr(event, "quality", getattr(event, "quality_status", None))
        classification = getattr(event, "classification", None)

        # 2. Update warm rolling statistics
        key = f"{asset_id}::{signal_id}"
        recent = rolling_buffer.get_recent_points(asset_id, signal_id, count=30)
        
        vals = [
            getattr(e, "value", getattr(e, "reading_value", 0.0))
            for e in recent
            if str(getattr(e, "quality", getattr(e, "quality_status", "GOOD"))).upper() in ("GOOD", "DATAQUALITYFLAG.GOOD", "TELEMETRYQUALITY.GOOD")
        ]
        features = {}
        if len(vals) >= 3:
            mean_val = float(np.mean(vals))
            std_val = float(np.std(vals))
            rms_val = float(np.sqrt(np.mean(np.square(vals))))
            roc = float((vals[-1] - vals[0]) / max(1, len(vals)))
            features = {
                "mean": round(mean_val, 3),
                "std": round(std_val, 3),
                "rms": round(rms_val, 3),
                "rate_of_change": round(roc, 3),
                "samples_count": len(vals)
            }
            self.warm_aggregates[key] = {
                "asset_id": asset_id,
                "signal_id": signal_id,
                "unit": unit,
                "last_value": value,
                "features": features,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }

        # 3. If HOT classification, immediately trigger hot path processing
        is_hot = (str(classification).upper() in ("HOT", "DATACLASSIFICATION.HOT"))
        return {
            "is_hot": is_hot,
            "signal_id": signal_id,
            "asset_id": asset_id,
            "has_warm_aggregate": key in self.warm_aggregates
        }

    def get_warm_aggregates_for_asset(self, asset_id: str) -> Dict[str, Any]:
        prefix = f"{asset_id}::"
        res = {}
        for k, agg in self.warm_aggregates.items():
            if k.startswith(prefix):
                sig = k.split("::")[1]
                res[sig] = agg
        return res

stream_router = StreamRouter()
