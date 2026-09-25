const API_BASE = (typeof import.meta !== 'undefined' && import.meta.env && import.meta.env.VITE_API_BASE_URL)
  ? import.meta.env.VITE_API_BASE_URL
  : '/api';


export const api = {
  // 1. Plant Site
  async getSiteData() {
    const res = await fetch(`${API_BASE}/site`);
    if (!res.ok) throw new Error(`Failed to load plant site data: ${res.statusText}`);
    return res.json();
  },

  async getSiteGeoJSON() {
    const res = await fetch(`${API_BASE}/site/geojson`);
    if (!res.ok) throw new Error(`Failed to load site GeoJSON: ${res.statusText}`);
    return res.json();
  },

  // 2. Chemicals
  async getChemicals() {
    const res = await fetch(`${API_BASE}/chemicals`);
    if (!res.ok) throw new Error(`Failed to load chemicals: ${res.statusText}`);
    return res.json();
  },

  async getChemicalById(id) {
    const res = await fetch(`${API_BASE}/chemicals/${id}`);
    if (!res.ok) throw new Error(`Failed to load chemical ${id}: ${res.statusText}`);
    return res.json();
  },

  // 3. Scenario Presets
  async getPresets() {
    const res = await fetch(`${API_BASE}/scenarios/presets`);
    if (!res.ok) throw new Error(`Failed to load presets: ${res.statusText}`);
    return res.json();
  },

  // 3.1 Live Weather Service
  async getCurrentWeather(latitude = 21.6850, longitude = 72.5750) {
    const res = await fetch(`${API_BASE}/weather/current?latitude=${latitude}&longitude=${longitude}`);
    if (!res.ok) throw new Error(`Failed to load current weather: ${res.statusText}`);
    return res.json();
  },

  // 4. Hazard Simulation
  async runSimulation(scenarioParams) {
    const res = await fetch(`${API_BASE}/hazard/simulate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(scenarioParams)
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || 'Hazard simulation failed');
    }
    return res.json();
  },

  // 5. Impact Analysis
  async analyzeImpact(simulationResult, timeStepSec = 120) {
    const res = await fetch(`${API_BASE}/impact/analyze?time_step_sec=${timeStepSec}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(simulationResult)
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || 'Impact analysis failed');
    }
    return res.json();
  },

  // 6. Evacuation Routing
  async calculateEvacuationRoute(simulationResult, impactResult, originCoords = null, originName = null) {
    let url = `${API_BASE}/evacuation/route`;
    const params = [];
    if (originName) params.push(`origin_name=${encodeURIComponent(originName)}`);
    if (params.length) url += `?${params.join('&')}`;

    const res = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        simulation_result: simulationResult,
        impact_result: impactResult,
        origin_coords: originCoords
      })
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || 'Evacuation routing failed');
    }
    return res.json();
  },

  // 7. Resource Optimization
  async optimizeResources(simulationResult, impactResult, evacuationPlan = null) {
    const res = await fetch(`${API_BASE}/resources/optimize`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        simulation_result: simulationResult,
        impact_result: impactResult,
        evacuation_plan: evacuationPlan
      })
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || 'Resource optimization failed');
    }
    return res.json();
  },

  // 8. Fire Pre-Plan Authorization Governance
  async getAuthorizationStatus(incidentId, assetId = 'T-04', chemicalId = 'CHEM-NH3', chemicalName = 'Ammonia', scenarioHash = null) {
    let url = `${API_BASE}/preplan/authorization/${encodeURIComponent(incidentId)}?asset_id=${encodeURIComponent(assetId)}&chemical_id=${encodeURIComponent(chemicalId)}&chemical_name=${encodeURIComponent(chemicalName)}`;
    if (scenarioHash) url += `&scenario_hash=${encodeURIComponent(scenarioHash)}`;
    const res = await fetch(url);
    if (!res.ok) throw new Error('Failed to fetch authorization status');
    return res.json();
  },

  async authorizePrePlan(authPayload) {
    const res = await fetch(`${API_BASE}/preplan/authorize`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(authPayload)
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || 'Authorization failed');
    }
    return res.json();
  },

  async rejectPrePlan(rejectPayload) {
    const res = await fetch(`${API_BASE}/preplan/reject`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(rejectPayload)
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || 'Rejection failed');
    }
    return res.json();
  },

  // 9. Fire Pre-Plan PDF Download
  async downloadPrePlanPDF(payload) {
    const res = await fetch(`${API_BASE}/preplan/generate-pdf`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || 'Failed to generate Fire Pre-Plan PDF');
    }
    const blob = await res.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `Fire_PrePlan_${payload.simulation_result?.source_asset_id || 'Incident'}.pdf`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    window.URL.revokeObjectURL(url);
    return blob;
  },

  // 10. Intelligence Hub & Final Capabilities
  async compareWhatIfScenarios(payload) {
    const res = await fetch(`${API_BASE}/intelligence/whatif/compare`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || 'What-If scenario comparison failed');
    }
    return res.json();
  },

  async getHistoricalAnalyticsSummary() {
    const res = await fetch(`${API_BASE}/intelligence/analytics/summary`);
    if (!res.ok) throw new Error(`Failed to load historical analytics: ${res.statusText}`);
    return res.json();
  },

  async getPredictiveAssetHealth() {
    const res = await fetch(`${API_BASE}/intelligence/predictive/assets`);
    if (!res.ok) throw new Error(`Failed to load predictive asset health: ${res.statusText}`);
    return res.json();
  },

  async getVisionCameraPresets() {
    const res = await fetch(`${API_BASE}/intelligence/vision/presets`);
    if (!res.ok) throw new Error(`Failed to load vision presets: ${res.statusText}`);
    return res.json();
  },

  async analyzeVisionFrame(formData) {
    const res = await fetch(`${API_BASE}/intelligence/vision/detect`, {
      method: 'POST',
      body: formData
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || 'Computer vision analysis failed');
    }
    return res.json();
  },

  async chatWithCopilot(payload) {
    const res = await fetch(`${API_BASE}/intelligence/copilot/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || 'Copilot query failed');
    }
    return res.json();
  },

  // 11. Domino / Cascade Screening Risk
  async getDominoRisk(simulationResult, impactResult = null) {
    const res = await fetch(`${API_BASE}/intelligence/domino-risk`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        simulation_result: simulationResult,
        impact_result: impactResult
      })
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || 'Domino risk screening failed');
    }
    return res.json();
  },

  // 12. Incident Timeline
  async getIncidentTimeline(simulationResult, impactResult = null, evacuationPlan = null, resourcePlan = null, authStatus = null) {
    const res = await fetch(`${API_BASE}/intelligence/timeline`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        simulation_result: simulationResult,
        impact_result: impactResult,
        evacuation_plan: evacuationPlan,
        resource_plan: resourcePlan,
        authorization_status: authStatus
      })
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || 'Timeline generation failed');
    }
    return res.json();
  },

  // 13. Decision Audit Trail
  async getDecisionAuditTrail(incidentId = null, module = null, limit = 50) {
    const params = [];
    if (incidentId) params.push(`incident_id=${encodeURIComponent(incidentId)}`);
    if (module) params.push(`module=${encodeURIComponent(module)}`);
    if (limit) params.push(`limit=${limit}`);
    const queryStr = params.length ? `?${params.join('&')}` : '';

    const res = await fetch(`${API_BASE}/intelligence/audit-trail${queryStr}`);
    if (!res.ok) throw new Error(`Failed to load decision audit trail: ${res.statusText}`);
    return res.json();
  },

  async recordDecisionAudit(payload) {
    const res = await fetch(`${API_BASE}/intelligence/audit-trail/record`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || 'Failed to record audit entry');
    }
    return res.json();
  },

  // 14. Executive Situation Brief
  async getExecutiveSituationBrief(simulationResult, impactResult = null, evacuationPlan = null, resourcePlan = null, authRecord = null) {
    const res = await fetch(`${API_BASE}/intelligence/executive-brief`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        simulation_result: simulationResult,
        impact_result: impactResult,
        evacuation_plan: evacuationPlan,
        resource_plan: resourcePlan,
        authorization_record: authRecord
      })
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || 'Executive situation brief generation failed');
    }
    return res.json();
  },

  // 15. Industrial Streaming, Pre-Incident Safety & Telemetry
  async getStreamingMetrics() {
    const res = await fetch(`${API_BASE}/streaming/metrics`);
    if (!res.ok) throw new Error(`Failed to fetch streaming metrics: ${res.statusText}`);
    return res.json();
  },

  async getSystemHealth() {
    const res = await fetch(`${API_BASE}/streaming/health-overview`);
    if (!res.ok) throw new Error(`Failed to fetch system health: ${res.statusText}`);
    return res.json();
  },

  async setStreamConfig(streamCount) {
    const res = await fetch(`${API_BASE}/streaming/config`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ stream_count: streamCount })
    });
    if (!res.ok) throw new Error('Failed to update stream configuration');
    return res.json();
  },

  async injectStreamAnomaly(assetId = 'T-04', signalSuffix = 'PRESS_01', targetValue = 6.8, severity = 'CRITICAL') {
    const res = await fetch(`${API_BASE}/streaming/inject-anomaly`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        asset_id: assetId,
        signal_suffix: signalSuffix,
        target_value: targetValue,
        severity
      })
    });
    if (!res.ok) throw new Error('Failed to inject stream anomaly');
    return res.json();
  },

  async clearStreamAnomalies() {
    const res = await fetch(`${API_BASE}/streaming/clear-anomalies`, { method: 'POST' });
    if (!res.ok) throw new Error('Failed to clear stream anomalies');
    return res.json();
  },

  async getStreamTick(count = 50) {
    const res = await fetch(`${API_BASE}/streaming/tick?count=${count}`);
    if (!res.ok) throw new Error(`Failed to fetch telemetry tick: ${res.statusText}`);
    return res.json();
  },

  async getAllAssetsEarlyWarning() {
    const res = await fetch(`${API_BASE}/streaming/pre-incident/assets`);
    if (!res.ok) throw new Error(`Failed to fetch asset early warnings: ${res.statusText}`);
    return res.json();
  },

  async evaluateAssetState(payload) {
    const res = await fetch(`${API_BASE}/streaming/pre-incident/evaluate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    if (!res.ok) throw new Error('Failed to evaluate asset state');
    return res.json();
  },

  async getPreventiveInterventions(assetId, chemicalId = 'CHEM-NH3', riskScore = 75.0) {
    const res = await fetch(`${API_BASE}/streaming/preventive/interventions/${assetId}?chemical_id=${encodeURIComponent(chemicalId)}&current_risk_score=${riskScore}`);
    if (!res.ok) throw new Error(`Failed to load preventive interventions: ${res.statusText}`);
    return res.json();
  },

  async simulatePreventiveWhatIf(payload) {
    const res = await fetch(`${API_BASE}/streaming/preventive/whatif`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || 'Preventive What-If simulation failed');
    }
    return res.json();
  },

  async authorizeControlAction(payload) {
    const res = await fetch(`${API_BASE}/streaming/preventive/authorize-control`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    if (!res.ok) throw new Error('Failed to authorize control action');
    return res.json();
  },

  async getCascadePathways(assetId) {
    const res = await fetch(`${API_BASE}/streaming/risk-graph/cascade/${assetId}`);
    if (!res.ok) throw new Error(`Failed to fetch cascade pathways: ${res.statusText}`);
    return res.json();
  },

  async getEnvironmentalReceptors(assetId, windDirectionDeg = 195.0) {
    const res = await fetch(`${API_BASE}/streaming/risk-graph/environmental/${assetId}?wind_direction_deg=${windDirectionDeg}`);
    if (!res.ok) throw new Error(`Failed to fetch environmental receptors: ${res.statusText}`);
    return res.json();
  },

  async get19StageRoster() {
    const res = await fetch(`${API_BASE}/streaming/scenarios/19-stage/roster`);
    if (!res.ok) throw new Error(`Failed to fetch 19-stage roster: ${res.statusText}`);
    return res.json();
  },

  async execute19Stage(stageNum) {
    const res = await fetch(`${API_BASE}/streaming/scenarios/19-stage/${stageNum}`);
    if (!res.ok) throw new Error(`Failed to execute stage ${stageNum}: ${res.statusText}`);
    return res.json();
  },

  // 16. REACT-X SATELLITE THERMAL INTELLIGENCE SUITE
  async getThermalEvents(minConfidence = null, classification = null, facilityId = null, onlyAbnormal = false) {
    const params = [];
    if (minConfidence) params.push(`min_confidence=${encodeURIComponent(minConfidence)}`);
    if (classification && classification !== 'ALL') params.push(`classification=${encodeURIComponent(classification)}`);
    if (facilityId) params.push(`facility_id=${encodeURIComponent(facilityId)}`);
    if (onlyAbnormal) params.push(`only_abnormal=true`);
    const queryStr = params.length ? `?${params.join('&')}` : '';

    const res = await fetch(`${API_BASE}/thermal/events${queryStr}`);
    if (!res.ok) throw new Error(`Failed to load thermal events: ${res.statusText}`);
    return res.json();
  },

  async getThermalEventDetail(eventId) {
    const res = await fetch(`${API_BASE}/thermal/events/${encodeURIComponent(eventId)}`);
    if (!res.ok) throw new Error(`Failed to load thermal event detail: ${res.statusText}`);
    return res.json();
  },

  async getIndustrialFacilities() {
    const res = await fetch(`${API_BASE}/thermal/facilities`);
    if (!res.ok) throw new Error(`Failed to load industrial facilities: ${res.statusText}`);
    return res.json();
  },

  async getFacilityProfile(facilityId) {
    const res = await fetch(`${API_BASE}/thermal/facilities/${encodeURIComponent(facilityId)}`);
    if (!res.ok) throw new Error(`Failed to load facility profile: ${res.statusText}`);
    return res.json();
  },

  async getPersistentThermalSources(onlyAbnormal = false) {
    const queryStr = onlyAbnormal ? '?only_abnormal=true' : '';
    const res = await fetch(`${API_BASE}/thermal/persistent-sources${queryStr}`);
    if (!res.ok) throw new Error(`Failed to load persistent thermal sources: ${res.statusText}`);
    return res.json();
  },

  async getThermalAbnormalityWatchlist() {
    const res = await fetch(`${API_BASE}/thermal/abnormality-watchlist`);
    if (!res.ok) throw new Error(`Failed to load thermal abnormality watchlist: ${res.statusText}`);
    return res.json();
  },

  async classifyThermalEvent(eventId) {
    const res = await fetch(`${API_BASE}/thermal/classify/${encodeURIComponent(eventId)}`, {
      method: 'POST'
    });
    if (!res.ok) throw new Error(`Failed to classify thermal event: ${res.statusText}`);
    return res.json();
  },

  async getNightfireCharacterization(eventId) {
    const res = await fetch(`${API_BASE}/thermal/nightfire/${encodeURIComponent(eventId)}`);
    if (!res.ok) throw new Error(`Failed to load VIIRS Nightfire data: ${res.statusText}`);
    return res.json();
  },

  async getMultiSatelliteCorroboration(eventId) {
    const res = await fetch(`${API_BASE}/thermal/multi-satellite/${encodeURIComponent(eventId)}`);
    if (!res.ok) throw new Error(`Failed to load multi-satellite corroboration: ${res.statusText}`);
    return res.json();
  },

  async executeThermalHandoff(payload) {
    const res = await fetch(`${API_BASE}/thermal/handoff`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || 'Emergency handoff failed');
    }
    return res.json();
  },

  async getThermalGeoJSON(filters = {}) {
    const params = new URLSearchParams();
    if (filters.satellite) params.append('satellite', filters.satellite);
    if (filters.minConfidence) params.append('min_confidence', filters.minConfidence);
    if (filters.classification && filters.classification !== 'ALL') params.append('classification', filters.classification);
    if (filters.onlyAbnormal) params.append('only_abnormal', 'true');
    const queryStr = params.toString() ? `?${params.toString()}` : '';

    const res = await fetch(`${API_BASE}/thermal/events/geojson${queryStr}`);
    if (!res.ok) throw new Error(`Failed to load thermal GeoJSON: ${res.statusText}`);
    return res.json();
  },

  async getThermalStats() {
    const res = await fetch(`${API_BASE}/thermal/stats`);
    if (!res.ok) throw new Error(`Failed to load thermal stats: ${res.statusText}`);
    return res.json();
  },

  async getFIRMSFeedStatus() {
    const res = await fetch(`${API_BASE}/thermal/feed/status`);
    if (!res.ok) throw new Error(`Failed to load FIRMS feed status: ${res.statusText}`);
    return res.json();
  },

  async triggerFIRMSPoll(bbox = null, days = 1) {
    const params = new URLSearchParams();
    if (bbox) params.append('bbox', bbox);
    params.append('days', days.toString());

    const res = await fetch(`${API_BASE}/thermal/feed/poll?${params.toString()}`, {
      method: 'POST'
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || 'FIRMS manual poll failed');
    }
    return res.json();
  },

  async getSatelliteFeedHealth() {
    const res = await fetch(`${API_BASE}/thermal/health`);
    if (!res.ok) throw new Error(`Failed to load satellite feed health: ${res.statusText}`);
    return res.json();
  },

  // 17. Phase 5 Spatiotemporal Thermal Source Objects
  async getThermalSources(filters = {}) {
    const params = new URLSearchParams();
    if (filters.status) params.append('source_status', filters.status);
    if (filters.facility_id) params.append('facility_id', filters.facility_id);
    if (filters.min_frp) params.append('min_frp', filters.min_frp.toString());
    if (filters.bbox) params.append('bbox', filters.bbox);
    const queryStr = params.toString() ? `?${params.toString()}` : '';

    const res = await fetch(`${API_BASE}/thermal/sources${queryStr}`);
    if (!res.ok) throw new Error(`Failed to load thermal sources: ${res.statusText}`);
    return res.json();
  },

  async getThermalSourceDetail(sourceId) {
    const res = await fetch(`${API_BASE}/thermal/sources/${encodeURIComponent(sourceId)}`);
    if (!res.ok) throw new Error(`Failed to load thermal source detail: ${res.statusText}`);
    return res.json();
  },

  async getThermalSourceEvents(sourceId) {
    const res = await fetch(`${API_BASE}/thermal/sources/${encodeURIComponent(sourceId)}/events`);
    if (!res.ok) throw new Error(`Failed to load source observations: ${res.statusText}`);
    return res.json();
  },

  async getThermalSourceFacilities(sourceId) {
    const res = await fetch(`${API_BASE}/thermal/sources/${encodeURIComponent(sourceId)}/facilities`);
    if (!res.ok) throw new Error(`Failed to load source candidate facilities: ${res.statusText}`);
    return res.json();
  },

  async getThermalSourcesGeoJSON(filters = {}) {
    const params = new URLSearchParams();
    if (filters.status) params.append('source_status', filters.status);
    if (filters.bbox) params.append('bbox', filters.bbox);
    const queryStr = params.toString() ? `?${params.toString()}` : '';

    const res = await fetch(`${API_BASE}/thermal/sources/geojson${queryStr}`);
    if (!res.ok) throw new Error(`Failed to load thermal sources GeoJSON: ${res.statusText}`);
    return res.json();
  },

  async triggerThermalClustering() {
    const res = await fetch(`${API_BASE}/thermal/sources/cluster`, {
      method: 'POST'
    });
    if (!res.ok) throw new Error(`Failed to trigger thermal clustering: ${res.statusText}`);
    return res.json();
  },

  // 18. Phase 5 Industrial Facilities Registry
  async getFacilities(filters = {}) {
    const params = new URLSearchParams();
    if (filters.state) params.append('state', filters.state);
    if (filters.district) params.append('district', filters.district);
    if (filters.sector) params.append('sector', filters.sector);
    if (filters.source) params.append('source', filters.source);
    const queryStr = params.toString() ? `?${params.toString()}` : '';

    const res = await fetch(`${API_BASE}/facilities${queryStr}`);
    if (!res.ok) throw new Error(`Failed to load industrial facilities: ${res.statusText}`);
    return res.json();
  },

  async getFacilityDetail(facilityId) {
    const res = await fetch(`${API_BASE}/facilities/${encodeURIComponent(facilityId)}`);
    if (!res.ok) throw new Error(`Failed to load facility profile: ${res.statusText}`);
    return res.json();
  },

  async getFacilityThermalSources(facilityId) {
    const res = await fetch(`${API_BASE}/facilities/${encodeURIComponent(facilityId)}/thermal-sources`);
    if (!res.ok) throw new Error(`Failed to load facility thermal sources: ${res.statusText}`);
    return res.json();
  },

  async getFacilitiesGeoJSON() {
    const res = await fetch(`${API_BASE}/facilities/geojson`);
    if (!res.ok) throw new Error(`Failed to load facilities GeoJSON: ${res.statusText}`);
    return res.json();
  },

  // 19. Phase 6 Thermal Fingerprints & Abnormality Detection Engine
  async getThermalFingerprints(filters = {}) {
    const params = new URLSearchParams();
    if (filters.facility_id) params.append('facility_id', filters.facility_id);
    if (filters.source_id) params.append('source_id', filters.source_id);
    if (filters.data_sufficiency) params.append('data_sufficiency', filters.data_sufficiency);
    if (filters.limit) params.append('limit', filters.limit);
    const queryStr = params.toString() ? `?${params.toString()}` : '';

    const res = await fetch(`${API_BASE}/thermal/fingerprints${queryStr}`);
    if (!res.ok) throw new Error(`Failed to load thermal fingerprints: ${res.statusText}`);
    return res.json();
  },

  async getFingerprintDetail(fingerprintId) {
    const res = await fetch(`${API_BASE}/thermal/fingerprints/${encodeURIComponent(fingerprintId)}`);
    if (!res.ok) throw new Error(`Failed to load fingerprint detail: ${res.statusText}`);
    return res.json();
  },

  async getFacilityThermalHealth(facilityId) {
    const res = await fetch(`${API_BASE}/thermal/facilities/${encodeURIComponent(facilityId)}/thermal-health`);
    if (!res.ok) throw new Error(`Failed to load facility thermal health: ${res.statusText}`);
    return res.json();
  },

  async getThermalAbnormalities(filters = {}) {
    const params = new URLSearchParams();
    if (filters.status) params.append('status', filters.status);
    if (filters.min_score) params.append('min_score', filters.min_score);
    if (filters.facility_id) params.append('facility_id', filters.facility_id);
    if (filters.limit) params.append('limit', filters.limit);
    const queryStr = params.toString() ? `?${params.toString()}` : '';

    const res = await fetch(`${API_BASE}/thermal/abnormalities${queryStr}`);
    if (!res.ok) throw new Error(`Failed to load thermal abnormalities: ${res.statusText}`);
    return res.json();
  },

  async getAbnormalitiesGeoJSON(minScore = 0.0) {
    const res = await fetch(`${API_BASE}/thermal/abnormalities/geojson?min_score=${minScore}`);
    if (!res.ok) throw new Error(`Failed to load abnormalities GeoJSON: ${res.statusText}`);
    return res.json();
  },

  async getAbnormalityDetail(assessmentId) {
    const res = await fetch(`${API_BASE}/thermal/abnormalities/${encodeURIComponent(assessmentId)}`);
    if (!res.ok) throw new Error(`Failed to load abnormality detail: ${res.statusText}`);
    return res.json();
  },

  async recalculateThermalFingerprints() {
    const res = await fetch(`${API_BASE}/thermal/fingerprints/recalculate`, {
      method: 'POST'
    });
    if (!res.ok) throw new Error(`Failed to recalculate fingerprints: ${res.statusText}`);
    return res.json();
  },

  async getMLFeatures(limit = 100) {
    const res = await fetch(`${API_BASE}/thermal/ml-features?limit=${limit}`);
    if (!res.ok) throw new Error(`Failed to load ML feature vectors: ${res.statusText}`);
    return res.json();
  },

  // 20. Phase 7 Real AI/ML 7-Class Thermal Classifier & Explainability Engine
  async getThermalModelStatus() {
    const res = await fetch(`${API_BASE}/thermal/model/status`);
    if (!res.ok) throw new Error(`Failed to fetch ML model status: ${res.statusText}`);
    return res.json();
  },

  async getThermalClassification(sourceId) {
    const res = await fetch(`${API_BASE}/thermal/classification/${encodeURIComponent(sourceId)}`);
    if (!res.ok) throw new Error(`Failed to classify thermal source ${sourceId}: ${res.statusText}`);
    return res.json();
  },

  async classifyThermalEvent(eventId) {
    const res = await fetch(`${API_BASE}/thermal/classify/${encodeURIComponent(eventId)}`);
    if (!res.ok) throw new Error(`Failed to classify thermal event ${eventId}: ${res.statusText}`);
    return res.json();
  },

  async getThermalClassificationExplanation(sourceId) {
    const res = await fetch(`${API_BASE}/thermal/classification/${encodeURIComponent(sourceId)}/explanation`);
    if (!res.ok) throw new Error(`Failed to fetch classification explanation: ${res.statusText}`);
    return res.json();
  },

  async classifyThermalFeatures(payload) {
    const res = await fetch(`${API_BASE}/thermal/classify`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    if (!res.ok) throw new Error(`Failed to perform controlled feature classification: ${res.statusText}`);
    return res.json();
  },

  async listThermalClassificationResults(limit = 50, predictedClass = null) {
    const params = new URLSearchParams();
    if (limit) params.append('limit', limit);
    if (predictedClass) params.append('predicted_class', predictedClass);
    const queryStr = params.toString() ? `?${params.toString()}` : '';

    const res = await fetch(`${API_BASE}/thermal/classification/results${queryStr}`);
    if (!res.ok) throw new Error(`Failed to load classification results: ${res.statusText}`);
    return res.json();
  },

  // 21. Phase 8 Multi-Satellite Corroboration & Thermal Evidence Fusion
  async getSatelliteHealth() {
    const res = await fetch(`${API_BASE}/satellite/health`);
    if (!res.ok) throw new Error(`Failed to fetch satellite health: ${res.statusText}`);
    return res.json();
  },

  async getSatelliteAvailability() {
    const res = await fetch(`${API_BASE}/satellite/availability`);
    if (!res.ok) throw new Error(`Failed to fetch satellite availability matrix: ${res.statusText}`);
    return res.json();
  },

  async getThermalSourceEvidence(sourceId, includeOptical = true) {
    const res = await fetch(`${API_BASE}/thermal/sources/${encodeURIComponent(sourceId)}/evidence?include_optical=${includeOptical}`);
    if (!res.ok) throw new Error(`Failed to fetch thermal evidence bundle for source ${sourceId}: ${res.statusText}`);
    return res.json();
  },

  async getThermalSourceCorroboration(sourceId) {
    const res = await fetch(`${API_BASE}/thermal/sources/${encodeURIComponent(sourceId)}/corroboration`);
    if (!res.ok) throw new Error(`Failed to fetch source corroboration summary: ${res.statusText}`);
    return res.json();
  },

  async corroborateThermalSource(sourceId, payload = {}) {
    const res = await fetch(`${API_BASE}/thermal/sources/${encodeURIComponent(sourceId)}/corroborate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ source_id: sourceId, ...payload })
    });
    if (!res.ok) throw new Error(`Failed to trigger source corroboration: ${res.statusText}`);
    return res.json();
  },

  async requestImageConfirmation(sourceId) {
    const res = await fetch(`${API_BASE}/thermal/sources/${encodeURIComponent(sourceId)}/request-image-confirmation`, {
      method: 'POST'
    });
    if (!res.ok) throw new Error(`Failed to request on-demand image confirmation: ${res.statusText}`);
    return res.json();
  },

  async getThermalEventEvidence(eventId) {
    const res = await fetch(`${API_BASE}/thermal/events/${encodeURIComponent(eventId)}/evidence`);
    if (!res.ok) throw new Error(`Failed to fetch event evidence: ${res.statusText}`);
    return res.json();
  },

  async listEvidenceBundles(limit = 25, status = null) {
    const params = new URLSearchParams();
    if (limit) params.append('limit', limit);
    if (status) params.append('status', status);
    const queryStr = params.toString() ? `?${params.toString()}` : '';

    const res = await fetch(`${API_BASE}/thermal/evidence/bundles${queryStr}`);
    if (!res.ok) throw new Error(`Failed to load evidence bundles: ${res.statusText}`);
    return res.json();
  },

  // ==========================================
  // PHASE 9: INDUSTRIAL THERMAL ASSESSMENT & REACT-X INTEGRATION
  // ==========================================
  async getThermalSourceAssessment(sourceId) {
    const res = await fetch(`${API_BASE}/thermal/sources/${encodeURIComponent(sourceId)}/assessment`);
    if (!res.ok) throw new Error(`Failed to fetch assessment for source ${sourceId}: ${res.statusText}`);
    return res.json();
  },

  async assessThermalSource(sourceId, payload = {}) {
    const res = await fetch(`${API_BASE}/thermal/sources/${encodeURIComponent(sourceId)}/assess`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ source_id: sourceId, ...payload })
    });
    if (!res.ok) throw new Error(`Failed to run assessment for source ${sourceId}: ${res.statusText}`);
    return res.json();
  },

  async listThermalAssessments(riskLevel = null, handoffEligibility = null, status = null, limit = 50) {
    const params = new URLSearchParams();
    if (riskLevel) params.append('risk_level', riskLevel);
    if (handoffEligibility) params.append('handoff_eligibility', handoffEligibility);
    if (status) params.append('status', status);
    if (limit) params.append('limit', limit);
    const queryStr = params.toString() ? `?${params.toString()}` : '';

    const res = await fetch(`${API_BASE}/thermal/assessments${queryStr}`);
    if (!res.ok) throw new Error(`Failed to list thermal assessments: ${res.statusText}`);
    return res.json();
  },

  async getAssessmentById(assessmentId) {
    const res = await fetch(`${API_BASE}/thermal/assessments/${encodeURIComponent(assessmentId)}`);
    if (!res.ok) throw new Error(`Failed to fetch assessment ${assessmentId}: ${res.statusText}`);
    return res.json();
  },

  async getAssessmentHistory(assessmentId) {
    const res = await fetch(`${API_BASE}/thermal/assessments/${encodeURIComponent(assessmentId)}/history`);
    if (!res.ok) throw new Error(`Failed to fetch history for assessment ${assessmentId}: ${res.statusText}`);
    return res.json();
  },

  async promoteAssessmentToIncident(assessmentId, payload) {
    const res = await fetch(`${API_BASE}/thermal/assessments/${encodeURIComponent(assessmentId)}/promote-incident`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || `Failed to promote assessment ${assessmentId} to incident`);
    }
    return res.json();
  },

  async rejectAssessmentDraft(assessmentId, payload) {
    const res = await fetch(`${API_BASE}/thermal/assessments/${encodeURIComponent(assessmentId)}/reject-draft`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || `Failed to reject assessment draft ${assessmentId}`);
    }
    return res.json();
  },

  async getAssessmentExecutiveBrief(assessmentId) {
    const res = await fetch(`${API_BASE}/thermal/assessments/${encodeURIComponent(assessmentId)}/executive-brief`);
    if (!res.ok) throw new Error(`Failed to fetch executive brief for assessment ${assessmentId}: ${res.statusText}`);
    return res.json();
  },

  // Phase 12: Real-Time Facility Telemetry
  async getTelemetryHealth() {
    const res = await fetch(`${API_BASE}/telemetry/health`);
    if (!res.ok) throw new Error(`Failed to fetch telemetry health: ${res.statusText}`);
    return res.json();
  },

  async getFacilityLatestTelemetry(facilityId) {
    const res = await fetch(`${API_BASE}/telemetry/facilities/${encodeURIComponent(facilityId)}/latest`);
    if (!res.ok) throw new Error(`Failed to fetch telemetry for facility ${facilityId}: ${res.statusText}`);
    return res.json();
  },

  async getFacilityTelemetryHistory(facilityId, params = {}) {
    const query = new URLSearchParams(params).toString();
    const res = await fetch(`${API_BASE}/telemetry/facilities/${encodeURIComponent(facilityId)}/history?${query}`);
    if (!res.ok) throw new Error(`Failed to fetch history for facility ${facilityId}: ${res.statusText}`);
    return res.json();
  },

  async getSensorLatestTelemetry(sensorId) {
    const res = await fetch(`${API_BASE}/telemetry/sensors/${encodeURIComponent(sensorId)}/latest`);
    if (!res.ok) throw new Error(`Failed to fetch sensor telemetry ${sensorId}: ${res.statusText}`);
    return res.json();
  },

  async setSimulatorScenario(scenarioName) {
    const res = await fetch(`${API_BASE}/telemetry/simulator/scenario`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ scenario_name: scenarioName })
    });
    if (!res.ok) throw new Error(`Failed to set simulation scenario: ${res.statusText}`);
    return res.json();
  },

  async triggerSimulatorTick() {
    const res = await fetch(`${API_BASE}/telemetry/simulator/tick`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' }
    });
    if (!res.ok) throw new Error(`Failed to trigger simulator tick: ${res.statusText}`);
    return res.json();
  },

  async getRegisteredGateways() {
    const res = await fetch(`${API_BASE}/telemetry/gateways`);
    if (!res.ok) throw new Error(`Failed to fetch edge gateways: ${res.statusText}`);
    return res.json();
  },

  // Phase 13: Facility Thermal Vision & CCTV Intelligence
  async getVisionHealth() {
    const res = await fetch(`${API_BASE}/vision/health`);
    if (!res.ok) throw new Error(`Failed to fetch vision health: ${res.statusText}`);
    return res.json();
  },

  async getFacilityLatestVision(facilityId) {
    const res = await fetch(`${API_BASE}/vision/facilities/${encodeURIComponent(facilityId)}/latest`);
    if (!res.ok) throw new Error(`Failed to fetch vision state for facility ${facilityId}: ${res.statusText}`);
    return res.json();
  },

  async getFacilityVisionEvents(facilityId, params = {}) {
    const query = new URLSearchParams(params).toString();
    const res = await fetch(`${API_BASE}/vision/facilities/${encodeURIComponent(facilityId)}/events?${query}`);
    if (!res.ok) throw new Error(`Failed to fetch vision events for facility ${facilityId}: ${res.statusText}`);
    return res.json();
  },

  async getCameraLatestVision(cameraId) {
    const res = await fetch(`${API_BASE}/vision/cameras/${encodeURIComponent(cameraId)}/latest`);
    if (!res.ok) throw new Error(`Failed to fetch vision state for camera ${cameraId}: ${res.statusText}`);
    return res.json();
  },

  async getRegisteredCameras() {
    const res = await fetch(`${API_BASE}/vision/cameras`);
    if (!res.ok) throw new Error(`Failed to fetch registered cameras: ${res.statusText}`);
    return res.json();
  },

  async getCorrelatedVisualAndTelemetry(assetId) {
    const res = await fetch(`${API_BASE}/vision/correlated/${encodeURIComponent(assetId)}`);
    if (!res.ok) throw new Error(`Failed to fetch correlated visual and telemetry for ${assetId}: ${res.statusText}`);
    return res.json();
  },

  async setVisionSimulatorScenario(scenarioName) {
    const res = await fetch(`${API_BASE}/vision/simulator/scenario`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ scenario_name: scenarioName })
    });
    if (!res.ok) throw new Error(`Failed to set vision simulation scenario: ${res.statusText}`);
    return res.json();
  },

  async triggerVisionSimulatorTick() {
    const res = await fetch(`${API_BASE}/vision/simulator/tick`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' }
    });
    if (!res.ok) throw new Error(`Failed to trigger vision simulator tick: ${res.statusText}`);
    return res.json();
  },

  // Phase 14: Hazard Trajectory & Early-Warning Engine
  async getFacilityCurrentPrediction(facilityId, assetId = 'T-04', horizon = '10m') {
    const res = await fetch(`${API_BASE}/prediction/facilities/${encodeURIComponent(facilityId)}/current?asset_id=${encodeURIComponent(assetId)}&horizon=${encodeURIComponent(horizon)}`);
    if (!res.ok) throw new Error(`Failed to fetch current prediction for ${facilityId}: ${res.statusText}`);
    return res.json();
  },

  async getFacilityPredictionHistory(facilityId, params = {}) {
    const query = new URLSearchParams(params).toString();
    const res = await fetch(`${API_BASE}/prediction/facilities/${encodeURIComponent(facilityId)}/history?${query}`);
    if (!res.ok) throw new Error(`Failed to fetch prediction history for ${facilityId}: ${res.statusText}`);
    return res.json();
  },

  async getFacilityPredictionTimeline(facilityId, assetId = 'T-04') {
    const res = await fetch(`${API_BASE}/prediction/facilities/${encodeURIComponent(facilityId)}/timeline?asset_id=${encodeURIComponent(assetId)}`);
    if (!res.ok) throw new Error(`Failed to fetch prediction timeline for ${facilityId}: ${res.statusText}`);
    return res.json();
  },

  async getFacilityPredictionExplanation(facilityId, assetId = 'T-04') {
    const res = await fetch(`${API_BASE}/prediction/facilities/${encodeURIComponent(facilityId)}/explanation?asset_id=${encodeURIComponent(assetId)}`);
    if (!res.ok) throw new Error(`Failed to fetch prediction explanation for ${facilityId}: ${res.statusText}`);
    return res.json();
  },

  async evaluateFacilityPrediction(facilityId, req) {
    const res = await fetch(`${API_BASE}/prediction/facilities/${encodeURIComponent(facilityId)}/evaluate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(req)
    });
    if (!res.ok) throw new Error(`Failed to evaluate prediction for ${facilityId}: ${res.statusText}`);
    return res.json();
  },

  async runPredictiveBacktest(scenarioName = 'THERMAL_ESCALATION', durationMinutes = 15) {
    const res = await fetch(`${API_BASE}/prediction/backtest`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ scenario_name: scenarioName, duration_minutes: durationMinutes })
    });
    if (!res.ok) throw new Error(`Failed to run predictive backtest: ${res.statusText}`);
    return res.json();
  },

  // Phase 15: Multimodal Evidence Fusion & Trusted Hazard Assessment
  async getFacilityCurrentFusion(facilityId, assetId = 'T-04') {
    const res = await fetch(`${API_BASE}/fusion/facilities/${encodeURIComponent(facilityId)}/current?asset_id=${encodeURIComponent(assetId)}`);
    if (!res.ok) throw new Error(`Failed to fetch current multimodal fusion for ${facilityId}: ${res.statusText}`);
    return res.json();
  },

  async getFacilityFusionHistory(facilityId, params = {}) {
    const query = new URLSearchParams(params).toString();
    const res = await fetch(`${API_BASE}/fusion/facilities/${encodeURIComponent(facilityId)}/history?${query}`);
    if (!res.ok) throw new Error(`Failed to fetch fusion history for ${facilityId}: ${res.statusText}`);
    return res.json();
  },

  async getFacilityFusionEvidence(facilityId, assetId = 'T-04') {
    const res = await fetch(`${API_BASE}/fusion/facilities/${encodeURIComponent(facilityId)}/evidence?asset_id=${encodeURIComponent(assetId)}`);
    if (!res.ok) throw new Error(`Failed to fetch fusion evidence for ${facilityId}: ${res.statusText}`);
    return res.json();
  },

  async getFacilityFusionExplanation(facilityId, assetId = 'T-04') {
    const res = await fetch(`${API_BASE}/fusion/facilities/${encodeURIComponent(facilityId)}/explanation?asset_id=${encodeURIComponent(assetId)}`);
    if (!res.ok) throw new Error(`Failed to fetch fusion explanation for ${facilityId}: ${res.statusText}`);
    return res.json();
  },

  async evaluateFacilityFusion(facilityId, req) {
    const res = await fetch(`${API_BASE}/fusion/facilities/${encodeURIComponent(facilityId)}/evaluate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(req)
    });
    if (!res.ok) throw new Error(`Failed to evaluate fusion for ${facilityId}: ${res.statusText}`);
    return res.json();
  },

  async runMultimodalAblation() {
    const res = await fetch(`${API_BASE}/fusion/ablation`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' }
    });
    if (!res.ok) throw new Error(`Failed to run multimodal ablation: ${res.statusText}`);
    return res.json();
  },

  // ==========================================
  // PHASE 16: ADAPTIVE SENSING & ORCHESTRATION
  // ==========================================
  async getFacilityAdaptiveDecision(facilityId, assetId = 'T-04') {
    const res = await fetch(`${API_BASE}/adaptive/facilities/${encodeURIComponent(facilityId)}/current?asset_id=${encodeURIComponent(assetId)}`);
    if (!res.ok) throw new Error(`Failed to fetch adaptive decision for ${facilityId}: ${res.statusText}`);
    return res.json();
  },

  async getFacilityAdaptiveHistory(facilityId, params = {}) {
    const query = new URLSearchParams(params).toString();
    const res = await fetch(`${API_BASE}/adaptive/facilities/${encodeURIComponent(facilityId)}/history?${query}`);
    if (!res.ok) throw new Error(`Failed to fetch adaptive history for ${facilityId}: ${res.statusText}`);
    return res.json();
  },

  async getFacilityAdaptiveExplanation(facilityId, assetId = 'T-04') {
    const res = await fetch(`${API_BASE}/adaptive/facilities/${encodeURIComponent(facilityId)}/explanation?asset_id=${encodeURIComponent(assetId)}`);
    if (!res.ok) throw new Error(`Failed to fetch adaptive explanation for ${facilityId}: ${res.statusText}`);
    return res.json();
  },

  async getNationalPriorityQueue() {
    const res = await fetch(`${API_BASE}/adaptive/priority`);
    if (!res.ok) throw new Error(`Failed to fetch national priority queue: ${res.statusText}`);
    return res.json();
  },

  async evaluateFacilityAdaptiveMonitoring(facilityId, req) {
    const res = await fetch(`${API_BASE}/adaptive/facilities/${encodeURIComponent(facilityId)}/evaluate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(req)
    });
    if (!res.ok) throw new Error(`Failed to evaluate adaptive monitoring for ${facilityId}: ${res.statusText}`);
    return res.json();
  },

  async acknowledgeAdaptiveDecision(facilityId, req) {
    const res = await fetch(`${API_BASE}/adaptive/facilities/${encodeURIComponent(facilityId)}/acknowledge`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(req)
    });
    if (!res.ok) throw new Error(`Failed to acknowledge adaptive decision for ${facilityId}: ${res.statusText}`);
    return res.json();
  },

  // ==========================================
  // PHASE 17: ADVANCED THERMAL DISCRIMINATION
  // ==========================================
  async getSourceDiscrimination(sourceId, params = {}) {
    const query = new URLSearchParams(params).toString();
    const res = await fetch(`${API_BASE}/discrimination/sources/${encodeURIComponent(sourceId)}?${query}`);
    if (!res.ok) throw new Error(`Failed to fetch discrimination for source ${sourceId}: ${res.statusText}`);
    return res.json();
  },

  async getSourceLandCoverContext(sourceId, params = {}) {
    const query = new URLSearchParams(params).toString();
    const res = await fetch(`${API_BASE}/discrimination/sources/${encodeURIComponent(sourceId)}/land-cover?${query}`);
    if (!res.ok) throw new Error(`Failed to fetch land cover for source ${sourceId}: ${res.statusText}`);
    return res.json();
  },

  async getSourceEOVerification(sourceId, params = {}) {
    const query = new URLSearchParams(params).toString();
    const res = await fetch(`${API_BASE}/discrimination/sources/${encodeURIComponent(sourceId)}/eo-verification?${query}`);
    if (!res.ok) throw new Error(`Failed to fetch EO verification for source ${sourceId}: ${res.statusText}`);
    return res.json();
  },

  async triggerEOVerification(sourceId, payload) {
    const res = await fetch(`${API_BASE}/discrimination/sources/${encodeURIComponent(sourceId)}/verify-eo`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    if (!res.ok) throw new Error(`Failed to trigger EO verification for ${sourceId}: ${res.statusText}`);
    return res.json();
  },

  // ==========================================
  // PHASE 19: END-TO-END SYSTEM ORCHESTRATION
  // ==========================================
  async executePipeline(params = {}) {
    const query = new URLSearchParams(params).toString();
    const res = await fetch(`${API_BASE}/orchestration/pipeline/execute?${query}`, {
      method: 'POST'
    });
    if (!res.ok) throw new Error(`Pipeline execution failed: ${res.statusText}`);
    return res.json();
  },

  async getPipelineTrace(traceId) {
    const res = await fetch(`${API_BASE}/orchestration/pipeline/traces/${encodeURIComponent(traceId)}`);
    if (!res.ok) throw new Error(`Failed to fetch trace ${traceId}: ${res.statusText}`);
    return res.json();
  },

  async getIncidentPacket(incidentId) {
    const res = await fetch(`${API_BASE}/orchestration/incident-packets/${encodeURIComponent(incidentId)}`);
    if (!res.ok) throw new Error(`Failed to fetch incident packet ${incidentId}: ${res.statusText}`);
    return res.json();
  },

  async getSystemReadiness() {
    const res = await fetch(`${API_BASE}/orchestration/readiness`);
    if (!res.ok) throw new Error(`Failed to fetch system readiness: ${res.statusText}`);
    return res.json();
  },

  async listUnifiedSources() {
    const res = await fetch(`${API_BASE}/orchestration/sources`);
    if (!res.ok) throw new Error(`Failed to list unified sources: ${res.statusText}`);
    return res.json();
  },

  async runGoldenScenario(scenarioId, facilityId = 'FAC-IN-DAHEJ-001') {
    const res = await fetch(`${API_BASE}/orchestration/scenarios/${encodeURIComponent(scenarioId)}?facility_id=${encodeURIComponent(facilityId)}`);
    if (!res.ok) throw new Error(`Failed to run scenario ${scenarioId}: ${res.statusText}`);
    return res.json();
  },

  // ==========================================
  // ACTION HELPERS: EVACUATION & PREPLAN PDF
  // ==========================================
  async generateEvacuationRoute(facilityId = 'FAC-IN-DAHEJ-001', assetId = 'T-04', customOrigin = null) {
    const simRes = await this.runSimulation({
      facility_id: facilityId,
      asset_id: assetId,
      chemical_id: 'CHEM-NH3',
      release_type: 'CONTINUOUS_TOXIC_PLUME',
      release_rate_kg_s: 15.0,
      release_duration_sec: 1800,
      ambient_temperature_c: 32.0,
      wind_speed_m_s: 2.2,
      wind_direction_deg: 45.0,
      atmospheric_stability: 'D'
    });
    const impactRes = await this.analyzeImpact(simRes, 120);
    const originCoords = customOrigin || (simRes.source_coordinates || [21.6850, 72.5750]);
    return await this.calculateEvacuationRoute(simRes, impactRes, originCoords, `Asset ${assetId} Staging`);
  },

  async exportPrePlanPDF(facilityId = 'FAC-IN-DAHEJ-001', assetId = 'T-04', chemicalId = 'CHEM-NH3') {
    const cleanChemId = chemicalId.startsWith('CHEM-') ? chemicalId : `CHEM-${chemicalId.replace('CH-', '')}`;
    const simRes = await this.runSimulation({
      title: `${facilityId} Emergency Pre-Plan Response`,
      asset_id: assetId,
      chemical_id: cleanChemId,
      incident_type: 'TOXIC_RELEASE',
      release_rate_kg_s: 15.0,
      release_duration_min: 30,
      ambient_temp_c: 32.0,
      wind_speed_kmh: 12.0,
      wind_direction_deg: 45.0,
      atmospheric_stability: 'D'
    });
    const impactRes = await this.analyzeImpact(simRes, 120);
    const evacPlan = await this.calculateEvacuationRoute(simRes, impactRes, simRes.source_coordinates, `Asset ${assetId}`);
    const resourcePlan = await this.optimizeResources(simRes, impactRes, evacPlan);
    
    return await this.downloadPrePlanPDF({
      simulation_result: simRes,
      impact_result: impactRes,
      evacuation_plan: evacPlan,
      resource_plan: resourcePlan,
      author_name: 'REACT-X National Industrial Safety Engine',
      facility_ref: `${facilityId} Emergency Response Plan`
    });
  },

  // ==========================================
  // DATA GATEWAY & DEMO REPLAY SUBSYSTEM
  // ==========================================
  async getDataGatewayStatus() {
    const res = await fetch(`${API_BASE}/data-gateway/status`);
    if (!res.ok) throw new Error(`Failed to load Data Gateway status: ${res.statusText}`);
    return res.json();
  },

  async getDataGatewaySources() {
    const res = await fetch(`${API_BASE}/data-gateway/sources`);
    if (!res.ok) throw new Error(`Failed to load Data Gateway sources: ${res.statusText}`);
    return res.json();
  },

  async getDataGatewayCatalog() {
    const res = await fetch(`${API_BASE}/data-gateway/catalog`);
    if (!res.ok) throw new Error(`Failed to load Data Gateway catalog: ${res.statusText}`);
    return res.json();
  },

  async getDataGatewayQuality() {
    const res = await fetch(`${API_BASE}/data-gateway/quality`);
    if (!res.ok) throw new Error(`Failed to load Data Gateway quality: ${res.statusText}`);
    return res.json();
  },

  async getDemoScenarios() {
    const res = await fetch(`${API_BASE}/data-gateway/demo/scenarios`);
    if (!res.ok) throw new Error(`Failed to load demo scenarios: ${res.statusText}`);
    return res.json();
  },

  async getDemoState() {
    const res = await fetch(`${API_BASE}/data-gateway/demo/state`);
    if (!res.ok) throw new Error(`Failed to load demo replay state: ${res.statusText}`);
    return res.json();
  },

  async startDemoReplay(scenarioId = 'SCENARIO-DAHEJ-AMMONIA-CRYO-01', speed = 1.0) {
    const res = await fetch(`${API_BASE}/data-gateway/demo/start?scenario_id=${encodeURIComponent(scenarioId)}&speed=${speed}`, {
      method: 'POST'
    });
    if (!res.ok) throw new Error(`Failed to start demo replay: ${res.statusText}`);
    return res.json();
  },

  async pauseDemoReplay() {
    const res = await fetch(`${API_BASE}/data-gateway/demo/pause`, { method: 'POST' });
    if (!res.ok) throw new Error(`Failed to pause demo replay: ${res.statusText}`);
    return res.json();
  },

  async resetDemoReplay() {
    const res = await fetch(`${API_BASE}/data-gateway/demo/reset`, { method: 'POST' });
    if (!res.ok) throw new Error(`Failed to reset demo replay: ${res.statusText}`);
    return res.json();
  },

  async stepDemoReplay() {
    const res = await fetch(`${API_BASE}/data-gateway/demo/step`, { method: 'POST' });
    if (!res.ok) throw new Error(`Failed to advance demo step: ${res.statusText}`);
    return res.json();
  },

  async injectDemoFailure(failureFlags) {
    const res = await fetch(`${API_BASE}/data-gateway/demo/failure-injection`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(failureFlags)
    });
    if (!res.ok) throw new Error(`Failed to inject failure flags: ${res.statusText}`);
    return res.json();
  }
};


