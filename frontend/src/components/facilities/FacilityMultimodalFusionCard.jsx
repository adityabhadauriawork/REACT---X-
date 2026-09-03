import React, { useState, useEffect } from 'react';
import { 
  Layers, ShieldAlert, AlertTriangle, ShieldCheck, 
  Activity, Clock, RefreshCw, BarChart2, CheckCircle2,
  Flame, Radio, Eye, Compass, Info, AlertOctagon, HelpCircle,
  TrendingUp, Sparkles, Filter
} from 'lucide-react';
import { api } from '../../services/api';

export default function FacilityMultimodalFusionCard({ facilityId = 'FAC-IN-DAHEJ-001', assetId = 'T-04' }) {
  const [assessment, setAssessment] = useState(null);
  const [loading, setLoading] = useState(true);
  const [showAblation, setShowAblation] = useState(false);
  const [ablationData, setAblationData] = useState([]);
  const [ablationLoading, setAblationLoading] = useState(false);

  const fetchFusionData = async () => {
    try {
      setLoading(true);
      const data = await api.getFacilityCurrentFusion(facilityId, assetId);
      setAssessment(data);
    } catch (err) {
      console.error('Failed to fetch multimodal fusion:', err);
    } finally {
      setLoading(false);
    }
  };

  const fetchAblationBenchmarks = async () => {
    try {
      setAblationLoading(true);
      const res = await api.runMultimodalAblation();
      setAblationData(res);
      setShowAblation(true);
    } catch (err) {
      console.error('Failed to run ablation benchmarks:', err);
    } finally {
      setAblationLoading(false);
    }
  };

  useEffect(() => {
    fetchFusionData();
  }, [facilityId, assetId]);

  if (loading && !assessment) {
    return (
      <div className="p-8 text-center text-slate-500 font-mono text-xs flex items-center justify-center space-x-2">
        <RefreshCw className="w-4 h-4 animate-spin text-cyan-400" />
        <span>Synthesizing multimodal evidence across satellite, telemetry & vision...</span>
      </div>
    );
  }

  const stateColors = {
    NORMAL: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30',
    WATCH: 'bg-cyan-500/10 text-cyan-400 border-cyan-500/30',
    ABNORMAL: 'bg-amber-500/10 text-amber-400 border-amber-500/30',
    HAZARD_DEVELOPING: 'bg-orange-500/15 text-orange-400 border-orange-500/40 animate-pulse',
    CRITICAL: 'bg-red-500/20 text-red-300 border-red-500/60 animate-pulse',
    INCIDENT: 'bg-rose-600/30 text-rose-200 border-rose-500 animate-pulse',
    CONFLICTING_EVIDENCE: 'bg-amber-950/50 text-amber-300 border-amber-500 animate-pulse',
    INSUFFICIENT_EVIDENCE: 'bg-slate-800 text-slate-400 border-slate-700',
    UNAVAILABLE: 'bg-slate-900 text-slate-500 border-slate-800'
  };

  const fusedState = assessment?.fused_state || 'NORMAL';
  const conflictK = assessment?.conflict_mass_k || 0.0;
  const isConflicted = conflictK >= 0.40 || fusedState === 'CONFLICTING_EVIDENCE';

  return (
    <div className="space-y-4 font-mono text-xs text-slate-200">
      
      {/* 1. Header Banner & Key Metrics */}
      <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-4 shadow-lg space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div>
            <div className="flex items-center space-x-2">
              <span className="px-2 py-0.5 rounded text-[10px] font-extrabold bg-cyan-500/10 text-cyan-400 border border-cyan-500/30 tracking-wider">
                DECISION-LEVEL DEMPSTER-SHAFER FUSION
              </span>
              <span className="text-[10px] text-slate-400 font-bold">Target: {facilityId} • Asset: {assetId}</span>
            </div>
            <h3 className="text-sm font-bold text-white mt-1 flex items-center gap-1.5">
              <Layers className="w-4 h-4 text-cyan-400" />
              TRUSTED MULTIMODAL HAZARD ASSESSMENT
            </h3>
          </div>

          <div className="flex items-center space-x-2">
            <button
              onClick={() => (showAblation ? setShowAblation(false) : fetchAblationBenchmarks())}
              className="px-2.5 py-1 bg-slate-800 hover:bg-slate-700 text-cyan-300 rounded border border-slate-700 font-bold text-[10.5px] transition flex items-center gap-1"
            >
              <BarChart2 className="w-3.5 h-3.5" />
              {showAblation ? 'HIDE ABLATION' : 'VIEW ABLATION BENCHMARKS'}
            </button>

            <button
              onClick={fetchFusionData}
              className="p-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded transition"
              title="Refresh Fused State"
            >
              <RefreshCw className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>

        {/* Core Fused Status Grid */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-2 border-t border-slate-800/80">
          <div className="bg-slate-950/80 p-2.5 rounded-lg border border-slate-800">
            <span className="text-[10px] text-slate-500 font-bold block uppercase">Fused Hazard State</span>
            <span className={`inline-block mt-1 px-2 py-0.5 rounded text-[11px] font-extrabold border ${stateColors[fusedState] || stateColors.NORMAL}`}>
              {fusedState.replace('_', ' ')}
            </span>
          </div>

          <div className="bg-slate-950/80 p-2.5 rounded-lg border border-slate-800">
            <span className="text-[10px] text-slate-500 font-bold block uppercase">Calibrated Confidence</span>
            <div className="text-xs font-extrabold font-mono text-emerald-400 mt-1">
              {assessment ? `${(assessment.confidence * 100).toFixed(0)}%` : '95%'}
            </div>
            <span className="text-[10px] text-slate-400">Dempster-Shafer Belief</span>
          </div>

          <div className="bg-slate-950/80 p-2.5 rounded-lg border border-slate-800">
            <span className="text-[10px] text-slate-500 font-bold block uppercase">Conflict Metric (K)</span>
            <div className={`text-xs font-extrabold font-mono mt-1 ${isConflicted ? 'text-amber-400' : 'text-slate-300'}`}>
              {conflictK.toFixed(3)} {isConflicted ? '(HIGH CONFLICT)' : '(LOW)'}
            </div>
            <span className="text-[10px] text-slate-400">Orthogonal Mass Divergence</span>
          </div>

          <div className="bg-slate-950/80 p-2.5 rounded-lg border border-slate-800">
            <span className="text-[10px] text-slate-500 font-bold block uppercase">Total Uncertainty m(Θ)</span>
            <div className="text-xs font-extrabold font-mono text-cyan-400 mt-1">
              {assessment ? `${(assessment.uncertainty_score * 100).toFixed(0)}%` : '5%'}
            </div>
            <span className="text-[10px] text-slate-400">Unassigned Belief Mass</span>
          </div>
        </div>

        {/* Discrepancy / Conflict Alert Box if K >= 0.40 */}
        {isConflicted && (
          <div className="p-3 bg-amber-950/40 border border-amber-500/60 rounded-lg flex items-start space-x-2.5 text-amber-200">
            <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
            <div>
              <span className="font-bold block text-[11px]">CROSS-MODAL SENSOR DISCREPANCY DETECTED:</span>
              <p className="text-[10.5px] text-amber-300/90 mt-0.5 leading-relaxed">
                {assessment?.conflict_explanation || "Satellite thermal anomaly reported, but local high-frequency telemetry and thermal vision indicate nominal conditions."}
              </p>
            </div>
          </div>
        )}
      </div>

      {/* 2. Ablation Comparison Benchmark Panel (if toggled) */}
      {showAblation && (
        <div className="bg-slate-900/90 border border-cyan-500/40 rounded-xl p-4 shadow-lg space-y-3 animate-in fade-in">
          <div className="flex justify-between items-center border-b border-slate-800 pb-2">
            <span className="font-bold text-white text-xs flex items-center gap-1.5">
              <BarChart2 className="w-4 h-4 text-cyan-400" />
              SYSTEMATIC MULTIMODAL ABLATION PERFORMANCE
            </span>
            <span className="text-[10px] text-slate-400">Ground Truth Validation Set</span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-[10.5px]">
              <thead className="bg-slate-950 text-slate-400 border-b border-slate-800">
                <tr>
                  <th className="p-2">Modality Combination</th>
                  <th className="p-2 text-right">Precision</th>
                  <th className="p-2 text-right">Recall</th>
                  <th className="p-2 text-right">FAR</th>
                  <th className="p-2 text-right">Miss Rate</th>
                  <th className="p-2 text-right">Lead Time</th>
                  <th className="p-2 text-right">Brier</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {ablationData.map((row, idx) => {
                  const isFull = row.modality_combination.includes('Full Multimodal');
                  return (
                    <tr key={idx} className={isFull ? 'bg-cyan-500/10 font-bold text-cyan-300' : 'text-slate-300'}>
                      <td className="p-2">{row.modality_combination}</td>
                      <td className="p-2 text-right">{(row.precision * 100).toFixed(1)}%</td>
                      <td className="p-2 text-right">{(row.recall * 100).toFixed(1)}%</td>
                      <td className="p-2 text-right">{(row.false_alarm_rate * 100).toFixed(1)}%</td>
                      <td className="p-2 text-right">{(row.miss_rate * 100).toFixed(1)}%</td>
                      <td className="p-2 text-right">{row.warning_lead_time_min.toFixed(1)} min</td>
                      <td className="p-2 text-right">{row.brier_score.toFixed(3)}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* 3. Main Content: Evidence Agreement Matrix & Timeline */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-3">
        
        {/* Left Column: Evidence Agreement Matrix (7 cols) */}
        <div className="lg:col-span-7 bg-slate-900/90 border border-slate-800 rounded-xl p-3.5 space-y-3">
          <div className="font-bold text-white text-xs border-b border-slate-800 pb-1.5 flex items-center justify-between">
            <span className="flex items-center gap-1.5">
              <CheckCircle2 className="w-3.5 h-3.5 text-cyan-400" />
              EVIDENCE AGREEMENT MATRIX
            </span>
            <span className="text-[10px] text-slate-400">
              {assessment?.data_lineage?.evidence_count || 0} Evaluated Signals
            </span>
          </div>

          {/* Supporting Signals */}
          <div className="space-y-1.5">
            <span className="text-[10px] text-emerald-400 font-bold uppercase block">
              Supporting Escalation ({assessment?.agreement_matrix?.supporting_signals?.length || 0}):
            </span>
            {assessment?.agreement_matrix?.supporting_signals?.map((ev, idx) => (
              <div key={idx} className="bg-slate-950/80 p-2 rounded-lg border border-emerald-500/20 flex items-center justify-between text-[11px]">
                <div className="flex items-center space-x-2">
                  <span className="px-1.5 py-0.2 rounded text-[9.5px] font-bold bg-emerald-500/20 text-emerald-300">
                    {ev.source_type}
                  </span>
                  <span className="text-white font-bold">{ev.evidence_type}</span>
                  <span className="text-slate-400 font-mono">({ev.raw_value} {ev.unit})</span>
                </div>
                <span className="text-emerald-400 font-bold text-[10.5px]">
                  Score: {(ev.normalized_score * 100).toFixed(0)}%
                </span>
              </div>
            ))}
          </div>

          {/* Contradicting / Nominal Signals */}
          <div className="space-y-1.5 pt-1">
            <span className="text-[10px] text-slate-400 font-bold uppercase block">
              Nominal / Contradicting ({assessment?.agreement_matrix?.contradicting_signals?.length || 0}):
            </span>
            {assessment?.agreement_matrix?.contradicting_signals?.map((ev, idx) => (
              <div key={idx} className="bg-slate-950/50 p-2 rounded-lg border border-slate-800 flex items-center justify-between text-[11px] text-slate-400">
                <div className="flex items-center space-x-2">
                  <span className="px-1.5 py-0.2 rounded text-[9.5px] font-bold bg-slate-800 text-slate-300">
                    {ev.source_type}
                  </span>
                  <span>{ev.evidence_type}: {ev.raw_value} {ev.unit}</span>
                </div>
                <span className="text-slate-500 text-[10px]">NOMINAL BASELINE</span>
              </div>
            ))}
          </div>

          {/* Stale Context & Missing */}
          {assessment?.agreement_matrix?.stale_signals?.length > 0 && (
            <div className="space-y-1.5 pt-1">
              <span className="text-[10px] text-amber-400/80 font-bold uppercase block">
                {"Stale Context (Aged > TTL):"}
              </span>
              {assessment.agreement_matrix.stale_signals.map((ev, idx) => (
                <div key={idx} className="bg-slate-950/40 p-2 rounded-lg border border-amber-500/20 flex items-center justify-between text-[11px] text-slate-400">
                  <span>{ev.source_type} ({ev.evidence_type}): {ev.freshness_age_sec}s old</span>
                  <span className="text-amber-400 text-[10px] font-bold">STALE</span>
                </div>
              ))}
            </div>
          )}

          {/* Recommended Action Box */}
          <div className="p-3 rounded-lg bg-slate-950 border border-slate-800 space-y-1 pt-2">
            <span className="text-[10px] text-slate-400 font-bold uppercase block">Operational Action Recommendation:</span>
            <div className="text-xs font-extrabold text-cyan-300">
              {assessment?.recommended_action?.replace('_', ' ')}
            </div>
            <p className="text-[11px] text-slate-300 leading-relaxed">
              {assessment?.recommended_action_detail}
            </p>
          </div>
        </div>

        {/* Right Column: Synchronized Evidence Timeline (5 cols) */}
        <div className="lg:col-span-5 bg-slate-900/90 border border-slate-800 rounded-xl p-3.5 space-y-3">
          <div className="font-bold text-white text-xs border-b border-slate-800 pb-1.5 flex items-center justify-between">
            <span className="flex items-center gap-1.5">
              <Clock className="w-3.5 h-3.5 text-cyan-400" />
              SYNCHRONIZED EVIDENCE TIMELINE
            </span>
            <span className="text-[10px] text-emerald-400">Unified Multi-Sensor Clock</span>
          </div>

          <div className="space-y-2">
            {assessment?.evidence_timeline?.length === 0 ? (
              <div className="p-6 text-center text-slate-500 text-[11px]">
                No recent anomaly transitions recorded in observation window.
              </div>
            ) : (
              assessment?.evidence_timeline?.map((evt, idx) => (
                <div key={idx} className="bg-slate-950/80 p-2.5 rounded-lg border border-slate-800 space-y-1 text-[11px]">
                  <div className="flex justify-between items-center text-[10px]">
                    <span className="font-bold text-cyan-300">{evt.relative_time}</span>
                    <span className="px-1.5 py-0.2 rounded bg-slate-800 text-slate-400 font-mono">
                      {evt.source_type}
                    </span>
                  </div>
                  <div className="text-white font-medium">{evt.description}</div>
                  <div className="text-[9.5px] text-slate-400">{evt.state_impact}</div>
                </div>
              ))
            )}
          </div>

          {/* Read-Only Safety Disclaimer */}
          <div className="pt-2 border-t border-slate-800/80 flex items-center space-x-1.5 text-[9.5px] text-slate-500">
            <ShieldCheck className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
            <span>Advisory Multimodal Fusion — Zero Direct Plant Actuation or ESD Access</span>
          </div>
        </div>

      </div>

    </div>
  );
}
