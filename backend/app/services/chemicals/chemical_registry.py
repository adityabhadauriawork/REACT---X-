from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field

class ChemicalProfile(BaseModel):
    chemical_id: str
    common_name: str
    cas_number: str
    formula: str
    physical_state: str  # GAS, LIQUEFIED_GAS, LIQUID, SOLID
    molecular_weight: float
    boiling_point_c: float
    flash_point_c: Optional[float] = None
    vapor_density_rel_air: float
    liquid_density_kg_m3: float
    lfl_percent: Optional[float] = None
    ufl_percent: Optional[float] = None
    erpg_1_ppm: float
    erpg_2_ppm: float
    erpg_3_ppm: float
    idlh_ppm: float
    hazard_class: str
    incompatibilities: List[str]
    decomposition_products: List[str]
    primary_medical_antidote: str
    tactical_firefighting_guidance: str
    authoritative_source: str
    source_reference_url: str

class ChemicalRegistry:
    """
    Authoritative Industrial Chemical Knowledge Layer:
    Provides verified physical, toxicological, and reactivity data from NIOSH, OSHA, EPA, and PubChem.
    """
    REGISTRY: Dict[str, ChemicalProfile] = {
        "CHEM-NH3": ChemicalProfile(
            chemical_id="CHEM-NH3",
            common_name="Ammonia (Anhydrous)",
            cas_number="7664-41-7",
            formula="NH3",
            physical_state="LIQUEFIED_GAS",
            molecular_weight=17.03,
            boiling_point_c=-33.34,
            flash_point_c=None,
            vapor_density_rel_air=0.59,
            liquid_density_kg_m3=682.0,
            lfl_percent=15.0,
            ufl_percent=28.0,
            erpg_1_ppm=25.0,
            erpg_2_ppm=150.0,
            erpg_3_ppm=750.0,
            idlh_ppm=300.0,
            hazard_class="Toxic Inhalation Hazard (TIH) / Corrosive / Flammable Gas",
            incompatibilities=["Acids", "Halogens (Chlorine/Fluorine/Bromine)", "Bleach", "Oxidizing Agents", "Silver/Mercury alloys"],
            decomposition_products=["Nitrogen Oxides (NOx)", "Hydrogen Gas"],
            primary_medical_antidote="Humidified Oxygen therapy; 2.5% nebulized sodium bicarbonate; ocular irrigation",
            tactical_firefighting_guidance="Deploy high-volume wide-angle water fog curtains for vapor knockdown. Do NOT direct straight water jet into liquid pools.",
            authoritative_source="NIOSH Pocket Guide to Chemical Hazards / OSHA 29 CFR 1910.1200",
            source_reference_url="https://www.cdc.gov/niosh/npg/npgd0028.html"
        ),
        "CHEM-LPG": ChemicalProfile(
            chemical_id="CHEM-LPG",
            common_name="Liquefied Petroleum Gas (LPG - Propane/Butane)",
            cas_number="68476-85-7",
            formula="C3H8 / C4H10",
            physical_state="LIQUEFIED_GAS",
            molecular_weight=44.10,
            boiling_point_c=-42.10,
            flash_point_c=-104.0,
            vapor_density_rel_air=1.55,
            liquid_density_kg_m3=510.0,
            lfl_percent=2.1,
            ufl_percent=9.5,
            erpg_1_ppm=1000.0,
            erpg_2_ppm=5000.0,
            erpg_3_ppm=10000.0,
            idlh_ppm=2000.0,
            hazard_class="Extremely Flammable Gas / BLEVE Risk / Vapor Cloud Explosion",
            incompatibilities=["Strong Oxidizers", "Chlorine Dioxide", "Halogens", "Ignition Sources"],
            decomposition_products=["Carbon Monoxide (CO)", "Carbon Dioxide (CO2)", "Dense Carbon Soot"],
            primary_medical_antidote="Fresh air removal; positive pressure SCBA; thermal burn dressings",
            tactical_firefighting_guidance="Continuous high-capacity deluge cooling (min 10.2 L/min/m2) on vessel shell to prevent BLEVE. Apply 3% AFFF foam.",
            authoritative_source="NFPA 58 Standard for LP-Gas / PubChem CID 6334",
            source_reference_url="https://pubchem.ncbi.nlm.nih.gov/compound/Liquefied-petroleum-gas"
        ),
        "CHEM-CL2": ChemicalProfile(
            chemical_id="CHEM-CL2",
            common_name="Chlorine (Liquefied)",
            cas_number="7782-50-5",
            formula="Cl2",
            physical_state="LIQUEFIED_GAS",
            molecular_weight=70.90,
            boiling_point_c=-34.04,
            flash_point_c=None,
            vapor_density_rel_air=2.49,
            liquid_density_kg_m3=1468.0,
            lfl_percent=None,
            ufl_percent=None,
            erpg_1_ppm=1.0,
            erpg_2_ppm=3.0,
            erpg_3_ppm=20.0,
            idlh_ppm=10.0,
            hazard_class="Severe Toxic Inhalation Hazard (TIH) / Strong Oxidizer",
            incompatibilities=["Ammonia", "Combustible Hydrocarbons", "Finely divided metals", "Hydrogen"],
            decomposition_products=["Hydrogen Chloride (HCl) gas", "Phosgene (in presence of organic compounds)"],
            primary_medical_antidote="Inhaled corticosteroids, bronchodilators, high-flow oxygen, dermal calcium gluconate",
            tactical_firefighting_guidance="Caustic soda alkaline neutralizing fog scrubbers. Level A encapsulating suits mandatory.",
            authoritative_source="EPA Chemical Emergency Preparedness / NIOSH NPG 0115",
            source_reference_url="https://www.cdc.gov/niosh/npg/npgd0115.html"
        ),
        "CHEM-H2S": ChemicalProfile(
            chemical_id="CHEM-H2S",
            common_name="Hydrogen Sulfide (Acid Gas)",
            cas_number="7783-06-4",
            formula="H2S",
            physical_state="GAS",
            molecular_weight=34.08,
            boiling_point_c=-60.28,
            flash_point_c=-60.0,
            vapor_density_rel_air=1.19,
            liquid_density_kg_m3=993.0,
            lfl_percent=4.0,
            ufl_percent=44.0,
            erpg_1_ppm=0.1,
            erpg_2_ppm=30.0,
            erpg_3_ppm=100.0,
            idlh_ppm=100.0,
            hazard_class="Extremely Toxic / Flammable Gas / Rapid Olfactory Paralysis",
            incompatibilities=["Strong Oxidizers", "Metals (Copper/Lead)", "Nitric Acid", "Peroxides"],
            decomposition_products=["Sulfur Dioxide (SO2)", "Toxic Sulfate fumes"],
            primary_medical_antidote="100% Hyperbaric/Normobaric Oxygen; Sodium Nitrite injection / Hydroxocobalamin",
            tactical_firefighting_guidance="Emergency flare divert; alkaline scrubber absorption; minimum 300m standoff upwind.",
            authoritative_source="OSHA Safety and Health Topics: Hydrogen Sulfide",
            source_reference_url="https://www.osha.gov/hydrogen-sulfide"
        ),
        "CHEM-C6H6": ChemicalProfile(
            chemical_id="CHEM-C6H6",
            common_name="Benzene (Pure Grade)",
            cas_number="71-43-2",
            formula="C6H6",
            physical_state="LIQUID",
            molecular_weight=78.11,
            boiling_point_c=80.1,
            flash_point_c=-11.1,
            vapor_density_rel_air=2.77,
            liquid_density_kg_m3=876.0,
            lfl_percent=1.2,
            ufl_percent=7.8,
            erpg_1_ppm=50.0,
            erpg_2_ppm=150.0,
            erpg_3_ppm=1000.0,
            idlh_ppm=500.0,
            hazard_class="Class 1A Known Carcinogen / Flammable Liquid / Toxic Vapor",
            incompatibilities=["Oxidizing Materials", "Halogens", "Perchlorates", "Ozone"],
            decomposition_products=["Carbon Monoxide", "Carbon Dioxide", "Aromatic Carcinogenic Particulates"],
            primary_medical_antidote="Gastric lavage (if ingested), respiratory resuscitation, activated charcoal",
            tactical_firefighting_guidance="Apply Alcohol-Resistant AFFF foam blanket; contain industrial effluent runoffs.",
            authoritative_source="IARC Monographs / NIOSH NPG 0049",
            source_reference_url="https://www.cdc.gov/niosh/npg/npgd0049.html"
        )
    }

    @classmethod
    def get_chemical(cls, chemical_id: str) -> Optional[ChemicalProfile]:
        return cls.REGISTRY.get(chemical_id)

    @classmethod
    def check_incompatibility(cls, chem_a_id: str, chem_b_id: str) -> Dict[str, Any]:
        """Check reactivity / dangerous incompatibility between two chemical agents."""
        cA = cls.get_chemical(chem_a_id)
        cB = cls.get_chemical(chem_b_id)
        if not cA or not cB:
            return {"incompatible": False, "reason": "Chemical not registered"}

        # Direct known dangerous pairs
        known_dangerous = [
            ({"CHEM-NH3", "CHEM-CL2"}, "CRITICAL", "Explosive Nitrogen Trichloride (NCl3) and toxic chloramine vapors formed upon contact."),
            ({"CHEM-H2S", "CHEM-CL2"}, "CRITICAL", "Violent exothermic oxidation and spontaneous ignition."),
            ({"CHEM-C6H6", "CHEM-CL2"}, "HIGH", "Exothermic halogenation releasing dense acidic HCl gas.")
        ]
        pair = {chem_a_id, chem_b_id}
        for dangerous_pair, severity, reason in known_dangerous:
            if pair == dangerous_pair:
                return {
                    "incompatible": True,
                    "severity": severity,
                    "reason": reason,
                    "chemicals": [cA.common_name, cB.common_name]
                }
        return {"incompatible": False, "severity": "NONE", "reason": "No violent direct incompatibility identified"}

chemical_registry = ChemicalRegistry()
