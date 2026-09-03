import React, { useState } from 'react';
import { 
  Building2, X, AlertTriangle, ShieldCheck, Flame, 
  Activity, Radio, Compass, FileText, ChevronRight, Siren, CheckCircle2,
  BarChart2, Layers
} from 'lucide-react';
import FacilityThermalHealthCard from '../facilities/FacilityThermalHealthCard';
import FacilityTelemetryCard from '../facilities/FacilityTelemetryCard';
import FacilityHazardPredictionCard from '../facilities/FacilityHazardPredictionCard';
import FacilityMultimodalFusionCard from '../facilities/FacilityMultimodalFusionCard';
import FacilityAdaptiveMonitoringCard from '../facilities/FacilityAdaptiveMonitoringCard';
import { Cpu } from 'lucide-react';

export default function FacilityProfileModal({
  isOpen,
  onClose,
  facility,
  activeHotspots = [],
  onInitiateHandoff
}) {
  const [activeTab, setActiveTab] = useState('multimodal_fusion'); // multimodal_fusion, thermal_profile, hazard_trajectory, facility_telemetry, infrastructure, active_hotspots

  if (!isOpen || !facility) return null;

  const isAbnormal = facility.current_status !== 'NOMINAL_OPERATIONS' || facility.current_abnormality_score > 30.0;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4 animate-in fade-in duration-200 font-mono text-xs text-slate-200">
      <div className="bg-[#090d16] border border-slate-700/90 rounded-2xl w-full max-w-5xl max-h-[92vh] flex flex-col shadow-2xl overflow-hidden">
        
        {/* Header */}
        <div className="p-4 border-b border-slate-800 flex items-center justify-between bg-gradient-to-r from-slate-950 to-[#0e1626]">
          <div className="flex items-center space-x-3">
            <div className={`p-2.5 rounded-xl border ${
              isAbnormal 
                ? 'bg-red-950/60 border-red-500/60 text-red-400 animate-pulse' 
                : 'bg-cyan-950/60 border-cyan-500/40 text-cyan-400'
            }`}>
              <Building2 className="w-6 h-6" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <span className="px-1.5 py-0.5 rounded bg-cyan-500/10 text-cyan-300 font-bold border border-cyan-500/30 text-[10px]">
                  {facility.id}
                </span>
                <span className={`px-2 py-0.5 rounded text-[10px] font-bold border ${
                  isAbnormal
                    ? 'bg-red-500/20 text-red-300 border-red-500/50'
                    : 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40'
                }`}>
                  {facility.current_status.replace('_', ' ')}
                </span>
                <span className="text-slate-400 text-[11px] font-bold">{facility.sector}</span>
              </div>
              <h2 className="text-sm sm:text-base font-extrabold text-white tracking-tight uppercase">
                {facility.name}
              </h2>
            </div>
          </div>

          <button
            type="button"
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Navigation Sub-Tabs */}
        <div className="flex items-center space-x-2 px-4 py-2 bg-slate-950 border-b border-slate-800 text-xs overflow-x-auto">
          {[
            { id: 'adaptive_sensing', label: 'ADAPTIVE SENSING', icon: Cpu },
            { id: 'multimodal_fusion', label: 'MULTIMODAL FUSION', icon: Layers },
            { id: 'thermal_profile', label: 'THERMAL PROFILE', icon: Activity },
            { id: 'hazard_trajectory', label: 'HAZARD TRAJECTORY & EARLY-WARNING', icon: Flame },
            { id: 'facility_telemetry', label: 'TELEMETRY', icon: Radio },
            { id: 'infrastructure', label: 'INFRASTRUCTURE', icon: Layers },
            { id: 'active_hotspots', label: `SATELLITE PASSES (${activeHotspots.length})`, icon: Radio }
          ].map((t) => {
            const Icon = t.icon;
            const isActive = activeTab === t.id;
            return (
              <button
                key={t.id}
                type="button"
                onClick={() => setActiveTab(t.id)}
                className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-lg font-bold transition-all text-xs whitespace-nowrap ${
                  isActive
                    ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/50 shadow-sm'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900/60'
                }`}
              >
                <Icon className={`w-3.5 h-3.5 ${isActive ? 'text-cyan-400' : 'text-slate-500'}`} />
                <span>{t.label}</span>
              </button>
            );
          })}
        </div>

        {/* Content Body */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          
          {/* TAB 0: ADAPTIVE SENSING ORCHESTRATION */}
          {activeTab === 'adaptive_sensing' && (
            <div className="space-y-4">
              <FacilityAdaptiveMonitoringCard facilityId={facility.id} assetId="T-04" />
            </div>
          )}

          {/* TAB 1: MULTIMODAL FUSION */}
          {activeTab === 'multimodal_fusion' && (
            <div className="space-y-4">
              <FacilityMultimodalFusionCard facilityId={facility.id} assetId="T-04" />
            </div>
          )}

          {/* TAB 2: FACILITY THERMAL PROFILE */}
          {activeTab === 'thermal_profile' && (
            <div className="space-y-4">
              <FacilityThermalHealthCard facilityId={facility.id} />
            </div>
          )}

          {/* TAB 3: HAZARD TRAJECTORY & EARLY-WARNING */}
          {activeTab === 'hazard_trajectory' && (
            <div className="space-y-4">
              <FacilityHazardPredictionCard facilityId={facility.id} assetId="T-04" />
            </div>
          )}

          {/* TAB 4: FACILITY TELEMETRY */}
          {activeTab === 'facility_telemetry' && (
            <div className="space-y-4">
              <FacilityTelemetryCard facilityId={facility.id} />
            </div>
          )}

          {/* TAB 2: INFRASTRUCTURE & CHEMICALS */}
          {activeTab === 'infrastructure' && (
            <div className="space-y-4">
              {/* Quick Stats Grid */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                <div className="bg-slate-900/80 p-2.5 rounded-xl border border-slate-800">
                  <span className="text-[10px] text-slate-500 block uppercase font-bold">Operator</span>
                  <span className="text-white font-bold text-xs truncate block">{facility.operator_name}</span>
                  <span className="text-[9px] text-slate-400">{facility.cluster_name}</span>
                </div>

                <div className="bg-slate-900/80 p-2.5 rounded-xl border border-slate-800">
                  <span className="text-[10px] text-slate-500 block uppercase font-bold">Coordinates</span>
                  <span className="text-cyan-300 font-bold text-xs">
                    {facility.coordinates[0].toFixed(4)}°N, {facility.coordinates[1].toFixed(4)}°E
                  </span>
                  <span className="text-[9px] text-slate-400">{facility.district}, {facility.state}</span>
                </div>

                <div className="bg-slate-900/80 p-2.5 rounded-xl border border-slate-800">
                  <span className="text-[10px] text-slate-500 block uppercase font-bold">Fence Perimeter</span>
                  <span className="text-white font-bold text-xs">{facility.fence_radius_m || 600}m Radius</span>
                  <span className="text-[9px] text-slate-400">OSM Polygon Verified</span>
                </div>

                <div className="bg-slate-900/80 p-2.5 rounded-xl border border-slate-800">
                  <span className="text-[10px] text-slate-500 block uppercase font-bold">PESO License</span>
                  <span className="text-cyan-300 font-bold text-xs truncate block">{facility.erdmp_license || 'PESO/IND/2024/01'}</span>
                  <span className="text-[9px] text-slate-400">ERDMP Verified</span>
                </div>
              </div>

              {/* Infrastructure Breakdown */}
              <div className="bg-slate-950/60 p-3.5 rounded-xl border border-slate-800 space-y-3">
                <span className="font-bold text-white text-xs flex items-center gap-1.5 uppercase">
                  <Flame className="w-3.5 h-3.5 text-amber-400" />
                  Thermal Units & Flare Headers
                </span>

                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-[11px]">
                  <div className="bg-slate-900/60 p-2 rounded border border-slate-800">
                    <span className="text-slate-500 block text-[9px]">REGISTERED FLARES</span>
                    <span className="text-white font-bold">{facility.known_flares_count} Hydrocarbon Stacks</span>
                  </div>
                  <div className="bg-slate-900/60 p-2 rounded border border-slate-800">
                    <span className="text-slate-500 block text-[9px]">PROCESS FURNACES</span>
                    <span className="text-white font-bold">{facility.known_furnaces_count} High-Temp Thermal Units</span>
                  </div>
                  <div className="bg-slate-900/60 p-2 rounded border border-slate-800">
                    <span className="text-slate-500 block text-[9px]">OPERATING SCHEDULE</span>
                    <span className="text-cyan-300 font-bold">Continuous 24/7 (365d)</span>
                  </div>
                  <div className="bg-slate-900/60 p-2 rounded border border-slate-800">
                    <span className="text-slate-500 block text-[9px]">HISTORICAL DETECTIONS</span>
                    <span className="text-slate-300 font-bold">{facility.historical_detections_count || 85} Observations</span>
                  </div>
                </div>

                {/* Major Chemicals */}
                <div>
                  <span className="text-slate-500 block text-[9px] mb-1.5 font-bold uppercase">HAZARDOUS CHEMICAL INVENTORY</span>
                  <div className="flex flex-wrap gap-1.5">
                    {facility.major_chemicals_stored.map((chem, idx) => (
                      <span key={idx} className="px-2.5 py-1 rounded-lg bg-slate-900 text-rose-300 border border-rose-500/30 text-[10px] font-bold">
                        {chem}
                      </span>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* TAB 3: ACTIVE SATELLITE PASSES */}
          {activeTab === 'active_hotspots' && (
            <div className="space-y-3">
              <div className="flex items-center justify-between border-b border-slate-800 pb-2">
                <span className="font-bold text-white text-xs flex items-center gap-1.5 uppercase">
                  <Radio className="w-3.5 h-3.5 text-cyan-400" />
                  Recent NASA FIRMS & Satellite Overpasses
                </span>
                <span className="text-[10px] text-slate-500">Telemetry Stream</span>
              </div>

              {activeHotspots.length === 0 ? (
                <div className="text-center py-8 text-slate-500 text-xs bg-slate-950/60 rounded-xl border border-slate-800">
                  No active thermal anomalies currently recorded inside this facility boundary.
                </div>
              ) : (
                <div className="space-y-2 max-h-80 overflow-y-auto">
                  {activeHotspots.map((hotspot) => (
                    <div key={hotspot.event_id} className="bg-slate-900/80 p-3 rounded-lg border border-slate-800 space-y-1.5">
                      <div className="flex items-center justify-between">
                        <span className="font-bold text-cyan-300 text-xs">{hotspot.event_id}</span>
                        <span className={`px-1.5 py-0.2 rounded text-[9px] font-bold border ${
                          hotspot.classification === 'INDUSTRIAL_FIRE'
                            ? 'bg-red-500/20 text-red-300 border-red-500/50'
                            : 'bg-amber-500/20 text-amber-300 border-amber-500/40'
                        }`}>
                          {hotspot.classification ? hotspot.classification.replace('_', ' ') : 'OBSERVED HOTSPOT'}
                        </span>
                      </div>

                      <div className="grid grid-cols-3 gap-2 text-[10px]">
                        <div>
                          <span className="text-slate-500 block">SATELLITE</span>
                          <span className="text-white font-bold">{hotspot.source_satellite}</span>
                        </div>
                        <div>
                          <span className="text-slate-500 block">FRP (HEAT)</span>
                          <span className="text-amber-400 font-bold">{hotspot.frp_mw} MW</span>
                        </div>
                        <div>
                          <span className="text-slate-500 block">BRIGHTNESS TEMP</span>
                          <span className="text-slate-300">{hotspot.brightness_temp_k ? `${hotspot.brightness_temp_k} K` : 'N/A'}</span>
                        </div>
                      </div>

                      <div className="flex items-center justify-between text-[9px] text-slate-500 pt-1 border-t border-slate-800">
                        <span>CONFIDENCE: <b className="text-emerald-400">{hotspot.confidence}</b> ({hotspot.confidence_pct || 95}%)</span>
                        <span>{new Date(hotspot.acquisition_timestamp).toLocaleTimeString()} UTC</span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

        </div>

        {/* Footer Action Controls */}
        <div className="p-3 border-t border-slate-800 flex items-center justify-between bg-slate-950/80">
          <span className="text-[10px] text-slate-500">
            REACT-X Industrial Intelligence Platform
          </span>

          <div className="flex items-center space-x-2">
            <button
              type="button"
              onClick={onClose}
              className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg text-xs font-bold transition-all"
            >
              Close Profile
            </button>
            {isAbnormal && (
              <button
                type="button"
                onClick={() => onInitiateHandoff && onInitiateHandoff(facility, activeHotspots[0])}
                className="px-4 py-1.5 bg-gradient-to-r from-red-600 to-amber-600 hover:from-red-500 hover:to-amber-500 text-white rounded-lg text-xs font-bold flex items-center space-x-1.5 shadow-lg transition-all"
              >
                <Siren className="w-3.5 h-3.5" />
                <span>Initiate Emergency Handoff</span>
              </button>
            )}
          </div>
        </div>

      </div>
    </div>
  );
}
