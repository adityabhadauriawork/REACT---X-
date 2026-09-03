import React, { useState, useEffect } from 'react';
import { 
  Flame, Globe, ShieldAlert, AlertTriangle, CheckCircle2, 
  Layers, MapPin, Eye, Sun, Satellite, CheckSquare, Info,
  ChevronDown, ChevronUp, RefreshCw, Sparkles, Building2
} from 'lucide-react';
import { api } from '../../services/api';

export default function ThermalSourceDiscriminationCard({
  sourceId = "SRC-IN-DAHEJ-FLARE-01",
  latitude = 21.6850,
  longitude = 72.5620,
  facilityId = "FAC-IN-DAHEJ-001"
}) {
  const [assessment, setAssessment] = useState(null);
  const [loading, setLoading] = useState(true);
  const [verifyingEO, setVerifyingEO] = useState(false);
  const [showDetails, setShowDetails] = useState(false);
  const [error, setError] = useState(null);

  const fetchDiscrimination = async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await api.getSourceDiscrimination(sourceId, {
        lat: latitude,
        lon: longitude,
        facility_id: facilityId
      });
      setAssessment(res);
    } catch (err) {
      console.error("Failed to load source discrimination:", err);
      setError(err.message || "Failed to load thermal source discrimination");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDiscrimination();
  }, [sourceId, latitude, longitude, facilityId]);

  const handleTriggerEOVerification = async () => {
    try {
      setVerifyingEO(true);
      const eoRes = await api.triggerEOVerification(sourceId, {
        latitude,
        longitude,
        facility_id: facilityId
      });
      setAssessment(prev => ({
        ...prev,
        eo_verification: eoRes
      }));
    } catch (err) {
      console.error("EO verification trigger failed:", err);
    } finally {
      setVerifyingEO(false);
    }
  };

  const getClassBadge = (className, state) => {
    if (state === 'NEEDS_REVIEW' || state === 'INSUFFICIENT_EVIDENCE') {
      return { bg: 'bg-amber-500/20 text-amber-300 border-amber-500/40', label: state };
    }
    switch (className) {
      case 'GAS_FLARE':
        return { bg: 'bg-orange-500/20 text-orange-400 border-orange-500/40', label: 'GAS FLARE (PROCESS HEAT)' };
      case 'ROUTINE_PROCESS_HEAT':
        return { bg: 'bg-cyan-500/20 text-cyan-400 border-cyan-500/40', label: 'ROUTINE PROCESS HEAT' };
      case 'INDUSTRIAL_FIRE':
        return { bg: 'bg-red-500/20 text-red-400 border-red-500/40 animate-pulse', label: 'INDUSTRIAL FIRE / CONTAINMENT LOSS' };
      case 'AGRICULTURAL_BURNING':
        return { bg: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/40', label: 'AGRICULTURAL STUBBLE BURNING' };
      case 'WILDFIRE_NATURAL':
        return { bg: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/40', label: 'WILDFIRE / VEGETATIVE' };
      case 'MINING_PROCESS_HEAT':
        return { bg: 'bg-purple-500/20 text-purple-400 border-purple-500/40', label: 'MINING / SMELTING HEAT' };
      default:
        return { bg: 'bg-slate-700/40 text-slate-300 border-slate-600/40', label: 'UNCLASSIFIED THERMAL SOURCE' };
    }
  };

  if (loading && !assessment) {
    return (
      <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-6 flex flex-col items-center justify-center min-h-[220px]">
        <RefreshCw className="w-6 h-6 text-cyan-400 animate-spin mb-2" />
        <p className="text-slate-400 text-xs font-mono">Running Multimodal Thermal-Source Discrimination Pipeline...</p>
      </div>
    );
  }

  const badge = getClassBadge(assessment?.predicted_class, assessment?.classification_state);

  return (
    <div className="bg-slate-900/90 border border-slate-800/80 rounded-xl p-5 shadow-2xl space-y-4 font-mono text-xs">
      {/* Top Header */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-800/60 pb-3">
        <div className="flex items-center space-x-3">
          <div className="p-2.5 rounded-lg bg-orange-500/10 border border-orange-500/30 text-orange-400">
            <Flame className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <span className="text-sm font-bold text-slate-100 uppercase tracking-wide">
                Thermal Source Discrimination &amp; Context
              </span>
              <span className="text-[10px] px-1.5 py-0.5 rounded bg-cyan-950 text-cyan-400 border border-cyan-500/30">
                PHASE 17 EO
              </span>
            </div>
            <p className="text-[11px] text-slate-400">
              Source {assessment?.source_id} &bull; {assessment?.centroid_lat}&deg;N, {assessment?.centroid_lon}&deg;E
            </p>
          </div>
        </div>

        <button
          onClick={fetchDiscrimination}
          className="p-1.5 rounded-lg bg-slate-800/80 hover:bg-slate-700/80 text-slate-300 border border-slate-700 transition-all"
          title="Refresh Discrimination"
        >
          <RefreshCw className="w-4 h-4" />
        </button>
      </div>

      {/* Primary Classification Banner */}
      <div className={`p-4 rounded-xl border ${badge.bg} flex flex-col md:flex-row md:items-center justify-between gap-4`}>
        <div className="space-y-1">
          <div className="flex items-center space-x-2">
            <span className="text-[10px] uppercase font-bold px-2 py-0.5 rounded bg-slate-950/60 border border-current">
              {assessment?.classification_state}
            </span>
            <span className="text-[10px] text-slate-300 font-sans">
              Persistence: <strong className="text-white font-mono">{assessment?.persistence_state}</strong> ({assessment?.observation_count} passes)
            </span>
          </div>
          <h4 className="text-base font-extrabold text-white tracking-tight">{badge.label}</h4>
          {assessment?.abstention_reason && (
            <p className="text-xs text-amber-300 font-sans">{assessment.abstention_reason}</p>
          )}
        </div>

        {/* Dual-Confidence Metrics */}
        <div className="flex items-center gap-3">
          <div className="bg-slate-950/60 p-2.5 rounded-lg border border-slate-800 text-center min-w-[100px]">
            <span className="text-[9px] text-slate-400 block uppercase font-bold">Model Softmax</span>
            <span className="text-sm font-bold text-cyan-400 font-mono">
              {Math.round((assessment?.model_confidence || 0) * 100)}%
            </span>
          </div>
          <div className="bg-slate-950/60 p-2.5 rounded-lg border border-slate-800 text-center min-w-[100px]">
            <span className="text-[9px] text-slate-400 block uppercase font-bold">System Certainty</span>
            <span className="text-sm font-bold text-emerald-400 font-mono">
              {Math.round((assessment?.system_confidence || 0) * 100)}%
            </span>
          </div>
        </div>
      </div>

      {/* Multi-Context Attribute Strip */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5 text-[11px]">
        {/* Land Cover */}
        <div className="bg-slate-950/60 p-2.5 rounded-lg border border-slate-800 space-y-1">
          <span className="text-slate-500 block text-[9px] font-bold uppercase flex items-center gap-1">
            <Globe className="w-3 h-3 text-cyan-400" />
            Land Cover (10m)
          </span>
          <span className="text-slate-200 font-bold block truncate">
            {assessment?.land_cover?.land_cover_class?.replace('_', ' ')}
          </span>
          <span className="text-[9px] text-slate-400 block">
            {Math.round((assessment?.land_cover?.consistency_with_industrial || 0) * 100)}% Industrial Consistency
          </span>
        </div>

        {/* Facility Attribution */}
        <div className="bg-slate-950/60 p-2.5 rounded-lg border border-slate-800 space-y-1">
          <span className="text-slate-500 block text-[9px] font-bold uppercase flex items-center gap-1">
            <Building2 className="w-3 h-3 text-amber-400" />
            Facility Context
          </span>
          <span className="text-slate-200 font-bold block truncate">
            {assessment?.is_inside_facility ? 'Inside Boundary (0m)' : `${assessment?.facility_distance_m}m Distance`}
          </span>
          <span className="text-[9px] text-slate-400 block truncate">
            {assessment?.attributed_facility_name || 'Unattributed'}
          </span>
        </div>

        {/* Observation Geometry Quality */}
        <div className="bg-slate-950/60 p-2.5 rounded-lg border border-slate-800 space-y-1">
          <span className="text-slate-500 block text-[9px] font-bold uppercase flex items-center gap-1">
            <Sun className="w-3 h-3 text-yellow-400" />
            Solar &amp; Viewing Quality
          </span>
          <span className={`font-bold block ${assessment?.is_potential_reflection ? 'text-amber-400' : 'text-emerald-400'}`}>
            {assessment?.observation_quality}
          </span>
          <span className="text-[9px] text-slate-400 block">
            {assessment?.is_potential_reflection ? 'Specular Glint Alert' : 'Clear Transmittance'}
          </span>
        </div>

        {/* High-Resolution EO Status */}
        <div className="bg-slate-950/60 p-2.5 rounded-lg border border-slate-800 space-y-1">
          <span className="text-slate-500 block text-[9px] font-bold uppercase flex items-center gap-1">
            <Satellite className="w-3 h-3 text-cyan-400" />
            EO Verification
          </span>
          <span className="text-cyan-300 font-bold block truncate">
            {assessment?.eo_verification?.structural_match_status?.replace('_', ' ') || 'NOT CHECKED'}
          </span>
          <span className="text-[9px] text-slate-400 block">
            {assessment?.eo_verification?.imagery_source?.split(' ')[0] || 'Sentinel-2 (10m)'}
          </span>
        </div>
      </div>

      {/* High-Resolution EO Verification Footprint Box */}
      {assessment?.eo_verification && (
        <div className="bg-slate-950/80 border border-cyan-500/30 rounded-lg p-3 space-y-2">
          <div className="flex items-center justify-between border-b border-slate-800 pb-1.5">
            <span className="text-xs font-bold text-cyan-400 uppercase tracking-wider flex items-center space-x-1.5">
              <Eye className="w-3.5 h-3.5" />
              <span>High-Resolution EO Structural Footprint (Sentinel-2 / PlanetScope)</span>
            </span>
            <span className="text-[10px] text-slate-400">
              Cloud Cover: {assessment.eo_verification.cloud_cover_percent}%
            </span>
          </div>
          <p className="text-xs text-slate-300 font-sans">
            {assessment.eo_verification.verification_summary}
          </p>

          {assessment.eo_verification.detected_structures?.length > 0 && (
            <div className="flex flex-wrap gap-2 pt-1">
              {assessment.eo_verification.detected_structures.map((s, idx) => (
                <div key={idx} className="bg-slate-900 px-2 py-1 rounded border border-slate-800 text-[10px] flex items-center space-x-1.5">
                  <span className="text-cyan-400 font-bold">{s.feature_type}</span>
                  <span className="text-slate-400">({s.distance_m}m dist, {Math.round(s.confidence*100)}% conf)</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Collapsible Top Supporting & Opposing Evidence */}
      <div className="bg-slate-950/40 border border-slate-800 rounded-lg p-3 space-y-2">
        <button
          onClick={() => setShowDetails(!showDetails)}
          className="w-full flex items-center justify-between text-xs font-bold text-slate-300 hover:text-white"
        >
          <span>Evidence Decomposition &amp; Attribution Proof ({assessment?.top_supporting_evidence?.length || 0} supporting, {assessment?.top_opposing_evidence?.length || 0} opposing)</span>
          {showDetails ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
        </button>

        {showDetails && (
          <div className="space-y-3 pt-2 border-t border-slate-800/80">
            {/* Supporting */}
            <div className="space-y-1.5">
              <span className="text-[10px] text-emerald-400 font-bold uppercase block">Supporting Evidence:</span>
              {assessment?.top_supporting_evidence?.map((e, idx) => (
                <div key={idx} className="p-2 rounded bg-emerald-950/20 border border-emerald-500/20 flex items-start space-x-2 text-[11px] text-emerald-200">
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 mt-0.5 shrink-0" />
                  <div>
                    <span className="font-bold uppercase text-[10px] text-emerald-400 block">{e.evidence_type}</span>
                    <p className="text-slate-300 font-sans text-[11px]">{e.description}</p>
                  </div>
                </div>
              ))}
            </div>

            {/* Opposing */}
            {assessment?.top_opposing_evidence?.length > 0 && (
              <div className="space-y-1.5">
                <span className="text-[10px] text-amber-400 font-bold uppercase block">Contradicting / Degraded Evidence:</span>
                {assessment.top_opposing_evidence.map((e, idx) => (
                  <div key={idx} className="p-2 rounded bg-amber-950/20 border border-amber-500/20 flex items-start space-x-2 text-[11px] text-amber-200">
                    <AlertTriangle className="w-3.5 h-3.5 text-amber-400 mt-0.5 shrink-0" />
                    <div>
                      <span className="font-bold uppercase text-[10px] text-amber-400 block">{e.evidence_type}</span>
                      <p className="text-slate-300 font-sans text-[11px]">{e.description}</p>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Action Footer */}
      <div className="flex items-center justify-between pt-1 border-t border-slate-800/60">
        <span className="text-[10px] text-slate-500 font-mono">
          Engine: {assessment?.discrimination_version} &bull; Model Confidence Calibrated
        </span>
        <button
          onClick={handleTriggerEOVerification}
          disabled={verifyingEO}
          className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-cyan-400 border border-slate-700 text-xs font-bold transition-all flex items-center space-x-1.5"
        >
          <Satellite className={`w-3.5 h-3.5 ${verifyingEO ? 'animate-spin' : ''}`} />
          <span>{verifyingEO ? 'Querying EO Catalog...' : 'Trigger EO Verification'}</span>
        </button>
      </div>
    </div>
  );
}
