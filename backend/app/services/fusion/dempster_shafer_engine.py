from typing import Dict, List, Any, Optional, Tuple, Set
from app.schemas.fusion import DempsterShaferMass, EvidenceItem, EvidenceSupportState

class DempsterShaferCombiner:
    """
    Mathematical Dempster-Shafer Evidence Combination Engine.
    Combines Basic Belief Assignments (BBAs) over the hazard frame of discernment:
    Θ = {NORMAL, THERMAL_ESCALATION, GAS_RELEASE, PRESSURE_ABNORMALITY, FIRE_DEVELOPMENT, INCIDENT}
    Explicitly tracks uncommitted uncertainty mass m(Θ) and orthogonal conflict mass K.
    """

    FRAME_OF_DISCERNMENT = {
        "NORMAL",
        "THERMAL_ESCALATION",
        "GAS_RELEASE",
        "PRESSURE_ABNORMALITY",
        "FIRE_DEVELOPMENT",
        "INCIDENT"
    }

    def combine_evidence_items(self, evidence_items: List[EvidenceItem]) -> DempsterShaferMass:
        if not evidence_items:
            # Complete uncertainty: m(Θ) = 1.0
            return DempsterShaferMass(
                hypothesis_masses={"NORMAL": 0.0},
                uncertainty_mass=1.0,
                conflict_mass_k=0.0,
                belief={"NORMAL": 0.0},
                plausibility={"NORMAL": 1.0}
            )

        # 1. Generate individual BBAs for each valid evidence item
        bbas: List[Dict[frozenset, float]] = []
        for item in evidence_items:
            if item.support_state in [EvidenceSupportState.MISSING, EvidenceSupportState.STALE]:
                continue
            bba = self._evidence_to_bba(item)
            if bba:
                bbas.append(bba)

        if not bbas:
            return DempsterShaferMass(
                hypothesis_masses={"NORMAL": 0.0},
                uncertainty_mass=1.0,
                conflict_mass_k=0.0,
                belief={"NORMAL": 0.0},
                plausibility={"NORMAL": 1.0}
            )

        # 2. Sequentially combine BBAs using Dempster's rule
        current_bba = bbas[0]
        cumulative_k = 0.0

        for next_bba in bbas[1:]:
            current_bba, k_step = self._dempster_combine_two(current_bba, next_bba)
            cumulative_k = max(cumulative_k, k_step)

        # 3. Format output masses, belief, and plausibility
        hyp_masses: Dict[str, float] = {}
        beliefs: Dict[str, float] = {}
        plausibilities: Dict[str, float] = {}
        uncertainty_mass = 0.0

        frame_set = frozenset(self.FRAME_OF_DISCERNMENT)

        for s, mass in current_bba.items():
            if s == frame_set:
                uncertainty_mass = round(mass, 4)
            elif len(s) == 1:
                hyp = list(s)[0]
                hyp_masses[hyp] = round(mass, 4)

        # Compute Belief Bel(A) and Plausibility Pl(A)
        for hyp in self.FRAME_OF_DISCERNMENT:
            single = frozenset([hyp])
            bel = current_bba.get(single, 0.0)
            pl = bel + uncertainty_mass
            beliefs[hyp] = round(bel, 4)
            plausibilities[hyp] = round(pl, 4)

        return DempsterShaferMass(
            hypothesis_masses=hyp_masses,
            uncertainty_mass=uncertainty_mass,
            conflict_mass_k=round(cumulative_k, 4),
            belief=beliefs,
            plausibility=plausibilities
        )

    def _evidence_to_bba(self, item: EvidenceItem) -> Dict[frozenset, float]:
        """Convert single EvidenceItem into Basic Belief Assignment."""
        frame_set = frozenset(self.FRAME_OF_DISCERNMENT)
        bba: Dict[frozenset, float] = {}

        if item.support_state == EvidenceSupportState.CONTRADICTING or item.normalized_score < 0.20:
            # Evidence strongly supports NORMAL baseline condition
            norm_strength = max(0.70, 1.0 - item.normalized_score)
            eff_mass = min(0.95, norm_strength * item.reliability_score * (0.5 if item.quality != "GOOD" else 1.0))
            uncommitted = max(0.05, 1.0 - eff_mass)
            bba[frozenset(["NORMAL"])] = eff_mass
            bba[frame_set] = uncommitted
            return bba

        eff_mass = min(0.95, item.normalized_score * item.reliability_score * (0.5 if item.quality != "GOOD" else 1.0))
        uncommitted = max(0.05, 1.0 - eff_mass)

        if "thermal" in item.evidence_type.lower() or "temperature" in item.evidence_type.lower() or "frp" in item.evidence_type.lower():
            bba[frozenset(["THERMAL_ESCALATION"])] = eff_mass
            bba[frame_set] = uncommitted
        elif "gas" in item.evidence_type.lower():
            bba[frozenset(["GAS_RELEASE"])] = eff_mass
            bba[frame_set] = uncommitted
        elif "press" in item.evidence_type.lower():
            bba[frozenset(["PRESSURE_ABNORMALITY"])] = eff_mass
            bba[frame_set] = uncommitted
        elif "flame" in item.evidence_type.lower() or "cctv" in item.evidence_type.lower():
            bba[frozenset(["FIRE_DEVELOPMENT"])] = eff_mass
            bba[frame_set] = uncommitted
        elif "prediction" in item.evidence_type.lower():
            bba[frozenset(["INCIDENT"])] = eff_mass
            bba[frame_set] = uncommitted
        else:
            bba[frozenset(["NORMAL"])] = 0.10
            bba[frame_set] = 0.90

        return bba

    def _dempster_combine_two(
        self,
        m1: Dict[frozenset, float],
        m2: Dict[frozenset, float]
    ) -> Tuple[Dict[frozenset, float], float]:
        """Orthogonal sum of two BBAs with conflict normalization."""
        raw_combined: Dict[frozenset, float] = {}
        conflict_k = 0.0

        for s1, val1 in m1.items():
            for s2, val2 in m2.items():
                inter = s1.intersection(s2)
                mass_product = val1 * val2
                if len(inter) == 0:
                    conflict_k += mass_product
                else:
                    raw_combined[inter] = raw_combined.get(inter, 0.0) + mass_product

        # Normalization factor: 1 / (1 - K)
        if conflict_k >= 0.999: # Total conflict
            return {frozenset(self.FRAME_OF_DISCERNMENT): 1.0}, 1.0

        denom = max(0.001, 1.0 - conflict_k)
        normalized: Dict[frozenset, float] = {
            s: (val / denom) for s, val in raw_combined.items()
        }

        return normalized, conflict_k

ds_combiner = DempsterShaferCombiner()
