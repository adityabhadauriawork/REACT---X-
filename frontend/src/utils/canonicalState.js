/**
 * Canonical Incident & Thermal Intelligence State Object Builder
 * 
 * Ensures ONE AUTHORITATIVE SOURCE OF TRUTH across all presentation layers:
 * - Top Global Header
 * - Active Event Status Banner
 * - Top HUDStats Metric Bar
 * - Incident Intelligence Triage Drawer
 * - Plant Map & Popups
 * - Left Sidebar Status Badges
 * - Multi-Role Views
 * - Fire Pre-Plan & Executive Situation Brief
 */

export function determineGlobalSystemState({
  simulationResult = null,
  impactResult = null,
  thermalEvents = [],
  facilities = []
} = {}) {
  // 1. INCIDENT_ACTIVE: Downstream REACT-X Emergency Response is Active
  if (simulationResult && simulationResult.source_asset_id) {
    return {
      state: 'INCIDENT_ACTIVE',
      label: 'INCIDENT ACTIVE',
      badgeClass: 'bg-red-500/20 text-red-300 border-red-500/60 animate-pulse',
      color: '#ef4444',
      description: `Active consequence plume modeled for ${simulationResult.source_asset_id} (${simulationResult.chemical_name || 'Hazardous Chemical'}). Downwind ERPG hazard envelopes active.`,
      activeEntity: simulationResult.source_asset_id,
      isEmergency: true
    };
  }

  // 2. CRITICAL: Confirmed high-priority abnormal thermal fire event
  const criticalEvent = thermalEvents.find(e => e.risk_level === 'CRITICAL' || e.classification === 'INDUSTRIAL_FIRE');
  if (criticalEvent) {
    const isDemo = !criticalEvent.is_live_data;
    return {
      state: 'CRITICAL',
      label: isDemo ? 'CRITICAL ALERT (SIMULATION)' : 'CRITICAL FIRE ALERT',
      badgeClass: 'bg-red-500/20 text-red-300 border-red-500/60 animate-pulse',
      color: '#ef4444',
      description: `${isDemo ? '[DEMO BENCHMARK] ' : ''}High-power anomaly [${criticalEvent.event_id}] at ${criticalEvent.attributed_facility_name || 'Industrial Facility'}: FRP ${criticalEvent.frp_mw} MW exceeding critical fire thresholds.`,
      activeEntity: criticalEvent.event_id,
      isEmergency: false,
      event: criticalEvent
    };
  }

  // 3. ABNORMAL: Elevated thermal departure (Z >= 3.0 or abnormality score >= 50%)
  const abnormalEvent = thermalEvents.find(e => e.abnormality_score >= 50.0 || e.is_abnormal);
  if (abnormalEvent) {
    const isDemo = !abnormalEvent.is_live_data;
    return {
      state: 'ABNORMAL',
      label: isDemo ? 'ABNORMAL SURGE (SIMULATION)' : 'ABNORMAL THERMAL SURGE',
      badgeClass: 'bg-amber-500/20 text-amber-300 border-amber-500/50',
      color: '#f59e0b',
      description: `${isDemo ? '[DEMO BENCHMARK] ' : ''}Persistent source [${abnormalEvent.event_id}] exhibiting statistical baseline heat departure: Abnormality score ${abnormalEvent.abnormality_score.toFixed(1)}%.`,
      activeEntity: abnormalEvent.event_id,
      isEmergency: false,
      event: abnormalEvent
    };
  }

  // 4. WATCH: Candidate unclassified thermal observation detected
  if (thermalEvents.length > 0) {
    const hasLive = thermalEvents.some(e => e.is_live_data);
    return {
      state: 'WATCH',
      label: hasLive ? 'SURVEILLANCE WATCH' : 'SURVEILLANCE WATCH (DEMO)',
      badgeClass: 'bg-cyan-500/10 text-cyan-300 border-cyan-500/40',
      color: '#06b6d4',
      description: `NASA FIRMS & VIIRS telemetry continuous: ${thermalEvents.length} regional thermal observations tracked across monitored industrial corridors.`,
      activeEntity: null,
      isEmergency: false
    };
  }

  // 5. NORMAL: All thermal observations and facilities nominal
  return {
    state: 'NORMAL',
    label: 'NORMAL',
    badgeClass: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30',
    color: '#10b981',
    description: 'All monitored industrial thermal signatures and facility flares operate within nominal baseline thresholds.',
    activeEntity: null,
    isEmergency: false
  };
}

export function getCanonicalIncidentState(arg1 = {}, ...rest) {
  let simulationResult = null;
  let impactResult = null;
  let evacuationPlan = null;
  let resourcePlan = null;
  let activeWeather = null;
  let authorizationRecord = null;
  let plantInfo = null;

  // Flexible argument normalization
  if (arg1 && typeof arg1 === 'object' && ('simulationResult' in arg1 || 'impactResult' in arg1 || 'activeWeather' in arg1 || 'plantInfo' in arg1)) {
    simulationResult = arg1.simulationResult || null;
    impactResult = arg1.impactResult || null;
    evacuationPlan = arg1.evacuationPlan || null;
    resourcePlan = arg1.resourcePlan || null;
    activeWeather = arg1.activeWeather || null;
    authorizationRecord = arg1.authorizationRecord || null;
    plantInfo = arg1.plantInfo || null;
  } else {
    plantInfo = (arg1 && typeof arg1 === 'object' && arg1.name) ? arg1 : null;
    if (rest.length > 0) {
      [simulationResult, impactResult, evacuationPlan, resourcePlan, activeWeather, , authorizationRecord] = rest;
    }
  }

  const hasIncident = !!simulationResult;

  // 1. Asset & Chemical
  const incident_id = simulationResult?.id || (simulationResult?.source_asset_id ? `INC-${simulationResult.source_asset_id}` : 'INC-STANDBY');
  const source_asset = simulationResult?.source_asset_id || 'T-04';
  const chemical = simulationResult?.chemical_name || (hasIncident ? 'Ammonia (Anhydrous)' : 'None (Standby)');
  const chemical_id = simulationResult?.chemical_id || 'CHEM-NH3';
  const incident_type = simulationResult?.incident_type || (hasIncident ? 'PIPELINE_LEAK' : 'STANDBY');
  const release_rate_kg_s = simulationResult?.effective_release_rate_kg_s ?? simulationResult?.release_rate_kg_s ?? (hasIncident ? 15.0 : 0.0);
  const release_duration_min = simulationResult?.release_duration_min ?? 30;
  const facility_name = plantInfo?.name || 'PetroChem Complex Alpha';
  const facility_sector = simulationResult?.source_sector || 'Sector A (Cryogenic Tank Farm)';

  // 2. Weather & Bearing Geometry (Explicit METEOROLOGICAL: FROM -> PLUME: TOWARD)
  const wind_from_deg = activeWeather?.wind_direction_deg ?? simulationResult?.wind_direction_deg ?? 45.0;
  const wind_from_cardinal = activeWeather?.wind_direction_cardinal ?? simulationResult?.wind_direction_cardinal ?? 'NE';
  const wind_speed_kmh = activeWeather?.wind_speed_kmh ?? simulationResult?.wind_speed_kmh ?? 8.0;
  const ambient_temp_c = activeWeather?.temperature_c ?? simulationResult?.ambient_temp_c ?? 32.0;
  const weather_mode = simulationResult?.weather_mode || activeWeather?.mode || 'LIVE';
  const weather_source = simulationResult?.weather_source || activeWeather?.source || 'Open-Meteo';
  
  const plume_toward_deg = (wind_from_deg + 180) % 360;
  const cardinalMap = {
    'N': 'S', 'NE': 'SW', 'E': 'W', 'SE': 'NW',
    'S': 'N', 'SW': 'NE', 'W': 'E', 'NW': 'SE'
  };
  const plume_toward_cardinal = cardinalMap[wind_from_cardinal] || `${plume_toward_deg.toFixed(0)}°`;
  const upwind_staging_deg = wind_from_deg;

  // 3. Canonical Risk & Severity
  const risk = impactResult?.risk_assessment;
  const canonical_risk_score = risk?.overall_score ?? (hasIncident ? 55.3 : 0.0);
  const canonical_severity = risk?.risk_category ?? (hasIncident ? 'HIGH' : 'NORMAL');
  const canonical_severity_color = risk?.color || (
    canonical_severity === 'CRITICAL' ? '#ef4444' :
    canonical_severity === 'HIGH' ? '#f97316' :
    canonical_severity === 'MODERATE' ? '#f59e0b' : '#10b981'
  );

  // 4. People & Infrastructure Impact
  const exposed_personnel = impactResult?.affected_workers_count ?? 0;
  const total_personnel_at_site = impactResult?.total_workers_at_site ?? 28;
  const red_zone_workers = impactResult?.red_zone_workers_count ?? 0;
  const orange_zone_workers = impactResult?.orange_zone_workers_count ?? 0;
  const yellow_zone_workers = impactResult?.yellow_zone_workers_count ?? 0;
  
  const threatened_assets_count = impactResult?.affected_assets_count ?? 0;
  const threatened_assets_list = impactResult?.affected_assets || [];
  const blocked_roads_count = impactResult?.blocked_roads_count ?? 0;
  const blocked_roads_list = impactResult?.blocked_road_segments || [];

  // 5. Hazard Envelope Reaches
  const summary_zones = simulationResult?.summary_zones || [];
  const max_red_reach_m = simulationResult?.max_red_reach_m ?? (summary_zones[0]?.max_downwind_distance_m ?? 0);
  const max_orange_reach_m = simulationResult?.max_orange_reach_m ?? (summary_zones[1]?.max_downwind_distance_m ?? 0);
  const max_yellow_reach_m = simulationResult?.max_yellow_reach_m ?? (summary_zones[2]?.max_downwind_distance_m ?? 0);
  const total_threat_area_m2 = simulationResult?.total_threat_area_m2 ?? 0;

  // 6. Safe Evacuation Routing
  const prim = evacuationPlan?.primary_evacuation_route;
  const recommended_assembly_point = prim?.recommended_assembly_point_name || 'Assembly Point 3 - West Perimeter Zone';
  const recommended_exit_gate = prim?.recommended_gate_name || 'Gate 2 - South Commercial & Tanker Logistics Gate';
  const evacuation_distance_m = prim?.total_distance_m ?? 624.0;
  const evacuation_time_min = prim?.estimated_evac_time_min ?? 8.7;
  const evacuation_status = evacuationPlan?.evacuation_status || (hasIncident ? 'ACTIVE_EVACUATION' : 'STANDBY');
  const rejected_routes_count = evacuationPlan?.rejected_routes_count ?? (evacuationPlan?.rejected_routes?.length ?? 0);

  // 7. Tactical Response & Resources
  const fw = resourcePlan?.foam_water_requirements;
  const recRes = resourcePlan?.recommended_resources || [];
  const lead_unit = recRes[0] || {
    resource_name: 'High-Volume Water Curtain Bowser',
    estimated_arrival_min: 2.5,
    resource_id: 'RES-01'
  };
  const firewater_demand_lpm = fw?.firewater_demand_lpm ?? (hasIncident ? 6100.0 : 0.0);
  const foam_demand_liters = fw?.foam_concentrate_liters ?? (hasIncident ? 0.0 : 0.0);
  const mandatory_ppe = fw?.ppe_required || 'Level A Fully Encapsulated Gas-Tight Suit';
  const standoff_m = resourcePlan?.standoff_upwind_m ?? 250.0;
  const units_deployed_count = recRes.length;

  // 8. Governance & Authorization
  const human_authorization_state = authorizationRecord?.status || 'PENDING_HUMAN_AUTHORIZATION';
  const approver_name = authorizationRecord?.approver_name || null;
  const approver_role = authorizationRecord?.approver_role || null;
  const approval_timestamp = authorizationRecord?.approval_timestamp || null;

  // 9. Containment State
  const containment_state = hasIncident ? 'SUPPRESSION_ACTIVE' : 'SYSTEM_STANDBY';

  return {
    hasIncident,
    incident_id,
    source_asset,
    chemical,
    chemical_id,
    incident_type,
    release_rate_kg_s,
    release_duration_min,
    facility_name,
    facility_sector,

    // Meteorology & Bearings
    weather_snapshot: {
      wind_speed_kmh,
      wind_from_deg,
      wind_from_cardinal,
      temperature_c: ambient_temp_c,
      mode: weather_mode,
      source: weather_source
    },
    wind_from_deg,
    wind_from_cardinal,
    wind_speed_kmh,
    ambient_temp_c,
    weather_mode,
    weather_source,
    plume_toward_deg,
    plume_toward_cardinal,
    upwind_staging_deg,

    // Canonical Risk
    canonical_risk_score,
    canonical_severity,
    canonical_severity_color,

    // Impact
    exposed_personnel,
    total_personnel_at_site,
    red_zone_workers,
    orange_zone_workers,
    yellow_zone_workers,
    threatened_assets_count,
    threatened_assets_list,
    blocked_roads_count,
    blocked_roads_list,

    // Hazard Envelope
    hazard_envelope: {
      max_red_reach_m,
      max_orange_reach_m,
      max_yellow_reach_m,
      total_threat_area_m2,
      summary_zones
    },
    max_red_reach_m,
    max_orange_reach_m,
    max_yellow_reach_m,

    // Evacuation Routing
    evacuation: {
      status: evacuation_status,
      recommended_assembly_point,
      recommended_exit_gate,
      distance_m: evacuation_distance_m,
      time_min: evacuation_time_min,
      rejected_routes_count
    },
    recommended_assembly_point,
    recommended_exit_gate,
    evacuation_distance_m,
    evacuation_time_min,
    evacuation_status,

    // Tactical Resources
    tactical: {
      lead_unit_name: lead_unit.resource_name,
      lead_unit_eta_min: lead_unit.estimated_arrival_min,
      firewater_demand_lpm,
      foam_demand_liters,
      standoff_m,
      units_deployed_count,
      mandatory_ppe
    },
    lead_unit_name: lead_unit.resource_name,
    lead_unit_eta_min: lead_unit.estimated_arrival_min,
    firewater_demand_lpm,
    foam_demand_liters,
    standoff_m,
    units_deployed_count,
    mandatory_ppe,

    // Governance & SIS
    governance: {
      human_authorization_state,
      approver_name,
      approver_role,
      approval_timestamp
    },
    human_authorization_state,
    approver_name,
    approver_role,
    approval_timestamp,
    containment_state
  };
}
