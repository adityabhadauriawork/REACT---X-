from typing import Dict, Any
from app.schemas.canonical import CanonicalEvent, DataClassification, DataQualityFlag

class StreamClassifier:
    """
    Classifies canonical events by safety-criticality, anomaly state, and latency requirements:
    - HOT (0-10s): High-severity anomalies, critical assets, active incident state, early warning triggers
    - WARM (minutes-hours): Rolling statistical aggregates, operational trends, telemetry baseline
    - COLD (days-years): Deep historical learning, training datasets, regulatory forensic archives
    """

    CRITICAL_ASSETS = {"T-04", "T-03", "T-02", "PU-01", "PU-02", "PU-03", "SUB-01"}

    def classify_event(self, event: CanonicalEvent) -> DataClassification:
        # Rule 1: Any CRITICAL or WARNING severity hint is strictly HOT path
        if event.severity_hint in ["CRITICAL", "WARNING"]:
            return DataClassification.HOT

        # Rule 2: Any BAD or UNCERTAIN quality flag requires immediate HOT review
        if event.quality in [DataQualityFlag.BAD, DataQualityFlag.UNCERTAIN]:
            return DataClassification.HOT

        # Rule 3: Critical process units in TRANSIENT or EMERGENCY modes
        if event.asset_id in self.CRITICAL_ASSETS and event.operating_mode in ["TRANSIENT", "EMERGENCY"]:
            return DataClassification.HOT

        # Rule 4: Normal operational data from standard sensors is WARM
        if event.severity_hint == "NORMAL" and event.quality == DataQualityFlag.GOOD:
            return DataClassification.WARM

        # Default classification
        return DataClassification.WARM

stream_classifier = StreamClassifier()
