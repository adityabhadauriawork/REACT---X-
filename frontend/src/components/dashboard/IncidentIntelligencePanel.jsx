import React, { useState } from 'react';
import {
  ShieldAlert, Wind, Thermometer, Flame, Users,
  Navigation, Siren, FileText, CheckCircle2, AlertTriangle,
  ArrowRight, ShieldCheck, DoorOpen, Clock, RefreshCw, Zap,
  Satellite, Building2, Radio, Cpu, Activity, ChevronDown, ChevronUp, Eye,
  Compass, Info, Layers
} from 'lucide-react';

export default function IncidentIntelligencePanel({
  simulationResult,
  impactResult,
  evacuationPlan,
  resourcePlan,
  activeWeather,
  liveTelemetry,
  weatherMode,
  onWeatherModeChange,
  presets = [],
  onSelectPreset,
  onNavigateTab,
  onRunSimulation,
  loading,
  selectedThermalEvent,
  selectedFacility,
  onOpenFacilityProfile,
  onInitiateHandoff
}) {
  const [showAdvancedEvidence, setShowAdvancedEvidence] = useState(false);

  const hasSimulation = !!simulationResult;
  const risk = impactResult?.risk_assessment;
  const primRoute = evacuationPlan?.primary_evacuation_route;
  const topResource = resourcePlan?.recommended_resources?.[0];
  const fw = resourcePlan?.foam_water_requirements;

  // Helper flags for selected thermal hotspot
  const isAbnormal = selectedThermalEvent?.abnormality_score >= 50.0 || selectedThermalEvent?.is_abnormal;
  const isFire = selectedThermalEvent?.classification === 'INDUSTRIAL_FIRE' || selectedThermalEvent?.risk_level === 'CRITICAL';
  const isClassified = selectedThermalEvent?.classification && selectedThermalEvent.classification !== 'UNCLASSIFIED';

  return (
    <div className="flex flex-col h-full bg-slate-900/90 border border-slate-800 rounded-xl overflow-hidden shadow-2xl font-mono text-xs">

      {/* 1. Panel Header */}
      <div className="bg-slate-950 px-3.5 py-2.5 border-b border-slate-800 flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <span className={`w-2 h-2 rounded-full ${hasSimulation || isFire ? 'bg-red-400 animate-ping' : 'bg-cyan-400'}`} />
          <span className="font-bold text-white uppercase tracking-wider text-[11px]">
            {hasSimulation ? 'Incident Command Feed' : 'Thermal Anomaly Triage'}
          </span>
        </div>
        <span className={`px-2 py-0.5 rounded text-[10px] font-bold border ${hasSimulation
            ? 'bg-red-500/20 text-red-300 border-red-500/40'
            : (isFire ? 'bg-red-500/20 text-red-300 border-red-500/40' : (isAbnormal ? 'bg-amber-500/20 text-amber-300 border-amber-500/40' : 'bg-cyan-500/10 text-cyan-300 border-cyan-500/30'))
          }`}>
          {hasSimulation
            ? (risk?.risk_category || 'INCIDENT ACTIVE')
            : (isFire ? 'CRITICAL FIRE' : (isAbnormal ? 'ABNORMAL SURGE' : 'SURVEILLANCE'))}
        </span>
      </div>

      {/* 2. Scrollable Body */}
      <div className="flex-1 overflow-y-auto p-3 space-y-3 custom-scrollbar">

        {/* A. SATELLITE THERMAL HOTSPOT TRIAGE CARD (OBSERVED -> ATTRIBUTION -> PERSISTENCE -> CLASSIFICATION -> RISK) */}
        {!hasSimulation && selectedThermalEvent && (
          <div className="bg-slate-950/80 p-3 rounded-xl border border-slate-800 space-y-2.5">
            <div className="flex justify-between items-center border-b border-slate-800 pb-1.5">
              <span className="text-slate-400 font-bold text-[10px] uppercase flex items-center gap-1.5">
                <Flame className="w-3.5 h-3.5 text-amber-400" />
                Target Thermal Anomaly
              </span>
              <span className="text-cyan-400 font-bold text-[10px]">
                {selectedThermalEvent.event_id}
              </span>
            </div>

            {/* Pipeline Stage 1: OBSERVED */}
            <div className="space-y-1 bg-slate-900/60 p-2 rounded-lg border border-slate-800">
              <div className="text-[9px] text-slate-500 uppercase font-bold flex justify-between">
                <span>1. Spaceborne Radiometry</span>
                <span className={selectedThermalEvent.is_live_data ? 'text-cyan-400' : 'text-amber-400'}>
                  {selectedThermalEvent.is_live_data ? 'LIVE NASA FIRMS' : 'DEMO BENCHMARK'}
                </span>
              </div>
              <div className="grid grid-cols-2 gap-2 text-[11px] pt-0.5">
                <div>
                  <span className="text-slate-500 text-[9px] block">SATELLITE & SENSOR</span>
                  <span className="font-bold text-white truncate block">
                    {selectedThermalEvent.source_satellite} ({selectedThermalEvent.sensor_name || 'VIIRS'})
                  </span>
                </div>
                <div>
                  <span className="text-slate-500 text-[9px] block">FIRE POWER (FRP)</span>
                  <span className="font-bold text-amber-400 text-xs">
                    {selectedThermalEvent.frp_mw} MW
                  </span>
                </div>
                <div>
                  <span className="text-slate-500 text-[9px] block">BRIGHTNESS TEMP</span>
                  <span className="font-bold text-slate-200">
                    {selectedThermalEvent.brightness_temp_k ? `${selectedThermalEvent.brightness_temp_k} K` : 'N/A'}
                  </span>
                </div>
                <div>
                  <span className="text-slate-500 text-[9px] block">CONFIDENCE</span>
                  <span className="font-bold text-emerald-400">
                    {selectedThermalEvent.confidence} ({selectedThermalEvent.confidence_pct || 90}%)
                  </span>
                </div>
              </div>
            </div>

            {/* Pipeline Stage 2: ATTRIBUTION */}
            <div className="bg-slate-900/60 p-2 rounded-lg border border-slate-800 text-[11px] space-y-0.5">
              <div className="text-[9px] text-slate-500 uppercase font-bold">2. Industrial Attribution</div>
              {selectedThermalEvent.attributed_facility_name ? (
                <div>
                  <div className="font-bold text-cyan-300 truncate">
                    {selectedThermalEvent.attributed_facility_name}
                  </div>
                  <div className="text-[10px] text-slate-400">
                    {selectedThermalEvent.is_inside_facility_boundary ? '● Inside Unit Boundary' : `~${selectedThermalEvent.facility_distance_m || 200}m buffer perimeter`}
                  </div>
                </div>
              ) : (
                <div className="text-slate-500 italic text-[10px]">
                  Attribution: Pending Spatial KD-Tree Index
                </div>
              )}
            </div>

            {/* Pipeline Stage 3 & 4: PERSISTENCE & CLASSIFICATION */}
            <div className="grid grid-cols-2 gap-1.5 text-[10px]">
              <div className="bg-slate-900/60 p-2 rounded-lg border border-slate-800">
                <span className="text-slate-500 block text-[9px] font-bold uppercase">3. Persistence</span>
                <span className={`font-bold block pt-0.5 ${isAbnormal ? 'text-red-400' : 'text-slate-300'}`}>
                  {selectedThermalEvent.abnormality_score ? `${selectedThermalEvent.abnormality_score.toFixed(1)}% (Z=${(selectedThermalEvent.abnormality_score / 15).toFixed(1)})` : 'Pending Baseline'}
                </span>
              </div>

              <div className="bg-slate-900/60 p-2 rounded-lg border border-slate-800">
                <span className="text-slate-500 block text-[9px] font-bold uppercase">4. AI Classification</span>
                <span className={`font-bold block pt-0.5 ${isFire ? 'text-red-400' : (isClassified ? 'text-amber-300' : 'text-slate-400')}`}>
                  {isClassified ? selectedThermalEvent.classification.replace(/_/g, ' ') : 'Pending ML Model'}
                </span>
              </div>
            </div>

            {/* Contextual Actions Strip */}
            <div className="space-y-1.5 pt-1">
              <div className="grid grid-cols-2 gap-1.5">
                {selectedFacility ? (
                  <button
                    type="button"
                    onClick={() => onOpenFacilityProfile && onOpenFacilityProfile(selectedFacility)}
                    className="px-2 py-1.5 rounded bg-slate-900 hover:bg-slate-800 text-cyan-300 border border-slate-700 text-[10px] font-bold transition-all text-center flex items-center justify-center gap-1"
                  >
                    <Building2 className="w-3 h-3" />
                    <span>View Facility</span>
                  </button>
                ) : (
                  <button
                    type="button"
                    onClick={() => onNavigateTab && onNavigateTab('context_facilities')}
                    className="px-2 py-1.5 rounded bg-slate-900 hover:bg-slate-800 text-slate-300 border border-slate-700 text-[10px] font-bold transition-all text-center flex items-center justify-center gap-1"
                  >
                    <Building2 className="w-3 h-3 text-slate-400" />
                    <span>Facilities</span>
                  </button>
                )}

                <button
                  type="button"
                  onClick={() => onNavigateTab && onNavigateTab('thermal_classification')}
                  className="px-2 py-1.5 rounded bg-slate-900 hover:bg-slate-800 text-slate-200 border border-slate-700 text-[10px] font-bold transition-all text-center flex items-center justify-center gap-1"
                >
                  <Cpu className="w-3 h-3 text-cyan-400" />
                  <span>View Evidence</span>
                </button>
              </div>

              <div className="grid grid-cols-2 gap-1.5">
                <button
                  type="button"
                  onClick={() => onNavigateTab && onNavigateTab('simulator')}
                  className="px-2 py-1.5 rounded bg-slate-900 hover:bg-slate-800 text-slate-200 border border-slate-700 text-[10px] font-bold transition-all text-center"
                >
                  Run What-If
                </button>

                <button
                  type="button"
                  onClick={() => onInitiateHandoff && onInitiateHandoff(selectedFacility || { id: 'FAC-01', name: 'PetroChem Alpha' }, selectedThermalEvent)}
                  className="px-2 py-1.5 rounded bg-gradient-to-r from-red-600 to-amber-600 hover:from-red-500 hover:to-amber-500 text-white font-bold text-[10px] shadow transition-all flex items-center justify-center gap-1"
                >
                  <Siren className="w-3 h-3" />
                  <span>Open Response Workspace</span>
                </button>
              </div>
            </div>

            {/* Progressive Disclosure Toggle */}
            <button
              type="button"
              onClick={() => setShowAdvancedEvidence(!showAdvancedEvidence)}
              className="w-full pt-1 text-[10px] text-slate-400 hover:text-cyan-300 flex items-center justify-between border-t border-slate-800/80 transition-colors"
            >
              <span>Advanced Radiometry & Sensor Telemetry</span>
              {showAdvancedEvidence ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
            </button>

            {showAdvancedEvidence && (
              <div className="bg-slate-900/60 p-2 rounded-lg border border-slate-800 text-[10px] space-y-1 text-slate-300">
                <div>Acquisition Time: <b className="text-white">{new Date(selectedThermalEvent.acquisition_timestamp).toUTCString()}</b></div>
                <div>Diurnal Overpass: <b className="text-cyan-300">{selectedThermalEvent.day_night === 'D' ? 'Day' : 'Night'}</b></div>
                <div>H3 Hex Index (Res 7): <b className="text-cyan-300">{selectedThermalEvent.h3_index || 'h3_872c02829ffffff'}</b></div>
                <div>Physics Dedup Key: <b className="text-slate-400 font-mono text-[9px] truncate block">{selectedThermalEvent.dedup_key}</b></div>
              </div>
            )}
          </div>
        )}

        {/* Quick Scenario Preset Launcher */}
        <div className="bg-slate-950/70 p-2.5 rounded-lg border border-slate-800 space-y-2">
          <div className="flex justify-between items-center text-[10px] text-slate-400 font-bold uppercase">
            <span>Downstream Consequence Simulation</span>
            <span className="text-cyan-400">1-Click Test</span>
          </div>
          <div className="grid grid-cols-3 gap-1.5">
            {presets.map(p => {
              const isSelected = simulationResult?.source_asset_id === p.asset_id;
              return (
                <button
                  key={p.id}
                  type="button"
                  onClick={() => onSelectPreset && onSelectPreset(p)}
                  className={`px-2 py-1.5 rounded text-[10px] font-bold transition-all border text-center ${isSelected
                      ? 'bg-cyan-500/20 text-cyan-300 border-cyan-400/80 shadow-sm shadow-cyan-500/20'
                      : 'bg-slate-900 text-slate-400 border-slate-700 hover:text-white hover:border-slate-600'
                    }`}
                >
                  <div>{p.asset_id}</div>
                  <div className="text-[8px] opacity-75 truncate">{p.chemical_id.replace('CHEM-', '')}</div>
                </button>
              );
            })}
          </div>
        </div>

        {/* B. ACTIVE INCIDENT / CONSEQUENCE EMERGENCY FEED */}
        {hasSimulation && (
          <>
            {/* Active Incident Summary Card */}
            <div className="bg-slate-950/80 p-3 rounded-lg border border-slate-800 space-y-2">
              <div className="flex justify-between items-center border-b border-slate-800 pb-1.5">
                <span className="text-slate-400 font-bold text-[10px] uppercase flex items-center gap-1.5">
                  <Flame className="w-3.5 h-3.5 text-rose-400" />
                  Active Consequence Plume
                </span>
                <span className="text-rose-400 font-bold text-[10px]">
                  {simulationResult.source_asset_id}
                </span>
              </div>

              <div className="grid grid-cols-2 gap-2 text-[11px]">
                <div>
                  <span className="text-slate-500 text-[10px] block">SUBSTANCE</span>
                  <span className="font-bold text-white truncate block" title={simulationResult.chemical_name}>
                    {simulationResult.chemical_name.split('(')[0]}
                  </span>
                </div>
                <div>
                  <span className="text-slate-500 text-[10px] block">EMISSION RATE</span>
                  <span className="font-bold text-cyan-300">
                    {simulationResult.effective_release_rate_kg_s} kg/s
                  </span>
                </div>
                <div>
                  <span className="text-slate-500 text-[10px] block">WIND VECTOR</span>
                  <span className="font-bold text-slate-200">
                    {activeWeather?.wind_speed_kmh} km/h {activeWeather?.wind_direction_cardinal}
                  </span>
                </div>
                <div>
                  <span className="text-slate-500 text-[10px] block">PLUME REACH</span>
                  <span className="font-bold text-cyan-400">
                    {simulationResult.summary_zones?.[0]?.max_downwind_distance_m}m Red
                  </span>
                </div>
              </div>
            </div>

            {/* Primary Action Directive: Evacuation Egress */}
            {primRoute && (
              <div className="bg-emerald-950/30 p-3 rounded-lg border border-emerald-500/40 space-y-2">
                <div className="flex justify-between items-center border-b border-emerald-500/30 pb-1.5">
                  <span className="text-emerald-300 font-bold text-[10px] uppercase flex items-center gap-1.5">
                    <Navigation className="w-3.5 h-3.5 text-emerald-400" />
                    Recommended Evacuation
                  </span>
                  <span className="text-emerald-400 font-bold text-[10px]">
                    {primRoute.route_status}
                  </span>
                </div>

                <div className="space-y-1 text-[11px]">
                  <div>
                    <span className="text-slate-400 text-[10px] block">SAFE MUSTER POINT:</span>
                    <span className="font-bold text-white text-xs">{primRoute.recommended_assembly_point_name}</span>
                  </div>
                  <div className="flex justify-between items-center text-slate-300 pt-0.5">
                    <span>Gate: <b className="text-cyan-300">{primRoute.recommended_gate_name}</b></span>
                    <span>Distance: <b className="text-amber-300">{primRoute.total_distance_m}m</b> (~{primRoute.estimated_evac_time_min}m)</span>
                  </div>
                </div>

                <button
                  onClick={() => onNavigateTab && onNavigateTab('evacuation')}
                  className="w-full text-center text-[10px] text-emerald-400 hover:text-emerald-300 hover:underline pt-1 flex items-center justify-center gap-1"
                >
                  <span>Inspect Dijkstra Route Scoring</span>
                  <ArrowRight className="w-3 h-3" />
                </button>
              </div>
            )}

            {/* Tactical Resource Dispatch Directive */}
            {resourcePlan && (
              <div className="bg-slate-950/80 p-3 rounded-lg border border-slate-800 space-y-2">
                <div className="flex justify-between items-center border-b border-slate-800 pb-1.5">
                  <span className="text-slate-400 font-bold text-[10px] uppercase flex items-center gap-1.5">
                    <Siren className="w-3.5 h-3.5 text-cyan-400" />
                    Tactical Resource Dispatch
                  </span>
                  <span className="text-cyan-400 font-bold text-[10px]">
                    {resourcePlan.recommended_resources?.length} Units
                  </span>
                </div>

                <div className="space-y-1.5 text-[11px]">
                  {topResource && (
                    <div className="bg-slate-900/90 p-2 rounded border border-slate-800">
                      <div className="flex justify-between items-center">
                        <span className="font-bold text-white">{topResource.resource_name}</span>
                        <span className="text-[10px] px-1.5 py-0.2 rounded bg-red-500/20 text-red-300 border border-red-500/40 font-bold">
                          {topResource.priority} • ETA {topResource.estimated_arrival_min}m
                        </span>
                      </div>
                    </div>
                  )}

                  <div className="grid grid-cols-2 gap-2 text-[10px] text-slate-300 pt-0.5">
                    <div>Firewater: <b className="text-blue-400">{fw?.firewater_demand_lpm?.toLocaleString()} LPM</b></div>
                    <div>Standoff: <b className="text-cyan-400">{resourcePlan.standoff_upwind_m}m</b></div>
                  </div>
                </div>

                <button
                  onClick={() => onNavigateTab && onNavigateTab('resources')}
                  className="w-full text-center text-[10px] text-cyan-400 hover:text-cyan-300 hover:underline pt-1 flex items-center justify-center gap-1"
                >
                  <span>View Full Resource Dispatch</span>
                  <ArrowRight className="w-3 h-3" />
                </button>
              </div>
            )}
          </>
        )}

      </div>

      {/* 3. Panel Footer Quick Actions */}
      <div className="bg-slate-950 p-2.5 border-t border-slate-800 flex items-center justify-between gap-2">
        <button
          type="button"
          onClick={() => onNavigateTab && onNavigateTab('simulator')}
          className="flex-1 bg-slate-800 hover:bg-slate-700 text-slate-200 py-1.5 rounded text-[11px] font-bold border border-slate-700 transition-all text-center"
        >
          What-If Simulator
        </button>

        <button
          type="button"
          onClick={() => onNavigateTab && onNavigateTab('preplan')}
          className="flex-1 bg-gradient-to-r from-red-600 to-rose-600 hover:from-red-500 hover:to-rose-500 text-white py-1.5 rounded text-[11px] font-bold border border-red-400/50 shadow-sm transition-all text-center flex items-center justify-center gap-1"
        >
          <FileText className="w-3.5 h-3.5" />
          <span>Fire Pre-Plan</span>
        </button>
      </div>

    </div>
  );
}
