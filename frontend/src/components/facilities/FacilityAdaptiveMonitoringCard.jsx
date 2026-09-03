import React, { useState, useEffect } from 'react';
import { 
  ShieldAlert, Radio, Activity, Eye, Flame, AlertTriangle, 
  CheckCircle2, Clock, RefreshCw, Cpu, Layers, ListOrdered, CheckSquare
} from 'lucide-react';
import { api } from '../../services/api';

export default function FacilityAdaptiveMonitoringCard({ facilityId = "FAC-IN-DAHEJ-001", assetId = "T-04" }) {
  const [decision, setDecision] = useState(null);
  const [nationalQueue, setNationalQueue] = useState([]);
  const [loading, setLoading] = useState(true);
  const [evaluating, setEvaluating] = useState(false);
  const [acknowledging, setAcknowledging] = useState(false);
  const [showQueue, setShowQueue] = useState(false);
  const [ackSuccess, setAckSuccess] = useState(false);
  const [error, setError] = useState(null);

  const fetchAdaptiveData = async () => {
    try {
      setLoading(true);
      setError(null);
      const [dec, queue] = await Promise.all([
        api.getFacilityAdaptiveDecision(facilityId, assetId),
        api.getNationalPriorityQueue()
      ]);
      setDecision(dec);
      setNationalQueue(queue || []);
    } catch (err) {
      console.error("Failed to load adaptive surveillance data:", err);
      setError(err.message || "Failed to load adaptive surveillance state");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAdaptiveData();
    const interval = setInterval(fetchAdaptiveData, 10000);
    return () => clearInterval(interval);
  }, [facilityId, assetId]);

  const handleSimulateScenario = async (forcedState, forcedUncertainty = null, forcedMissing = []) => {
    try {
      setEvaluating(true);
      const res = await api.evaluateFacilityAdaptiveMonitoring(facilityId, {
        facility_id: facilityId,
        asset_id: assetId,
        force_hazard_state: forcedState,
        force_uncertainty: forcedUncertainty,
        force_missing_sources: forcedMissing
      });
      setDecision(res);
    } catch (err) {
      console.error("Simulation failed:", err);
    } finally {
      setEvaluating(false);
    }
  };

  const handleAcknowledge = async () => {
    try {
      setAcknowledging(true);
      const res = await api.acknowledgeAdaptiveDecision(facilityId, {
        operator_name: "Lead Industrial Safety Officer",
        notes: "Acknowledged elevated surveillance recommendation; dispatched field inspection team."
      });
      setDecision(res);
      setAckSuccess(true);
      setTimeout(() => setAckSuccess(false), 3000);
    } catch (err) {
      console.error("Acknowledgement failed:", err);
    } finally {
      setAcknowledging(false);
    }
  };

  const getLevelBadge = (level) => {
    switch (level) {
      case 'LEVEL_5_INCIDENT':
        return { bg: 'bg-rose-500/20 text-rose-400 border-rose-500/40', label: 'LEVEL 5 — INCIDENT (ACTIVE HANDOFF)', desc: 'Emergency Response Initiated' };
      case 'LEVEL_4_CRITICAL':
        return { bg: 'bg-red-500/20 text-red-400 border-red-500/40 animate-pulse', label: 'LEVEL 4 — CRITICAL (MAX ANALYTICAL ATTENTION)', desc: 'Sub-second Continuous Processing' };
      case 'LEVEL_3_HAZARD_DEVELOPING':
        return { bg: 'bg-amber-500/20 text-amber-400 border-amber-500/40', label: 'LEVEL 3 — HAZARD DEVELOPING', desc: 'Accelerated Multimodal Cadence' };
      case 'LEVEL_2_ABNORMAL':
        return { bg: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/40', label: 'LEVEL 2 — ABNORMAL EXCURSION', desc: 'Continuous Thermal Tracking Activated' };
      case 'LEVEL_1_WATCH':
        return { bg: 'bg-blue-500/20 text-blue-400 border-blue-500/40', label: 'LEVEL 1 — WATCH (ELEVATED SAMPLING)', desc: 'Telemetry Drift Monitoring' };
      default:
        return { bg: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/40', label: 'LEVEL 0 — BASELINE SURVEILLANCE', desc: 'Routine Steady-State Cadence' };
    }
  };

  const getPriorityBadge = (priority) => {
    switch (priority) {
      case 'URGENT':
        return 'bg-red-600/30 text-red-300 border-red-500/50';
      case 'HIGH':
        return 'bg-amber-600/30 text-amber-300 border-amber-500/50';
      case 'MEDIUM':
        return 'bg-yellow-600/30 text-yellow-300 border-yellow-500/50';
      default:
        return 'bg-slate-700/40 text-slate-300 border-slate-600/40';
    }
  };

  if (loading && !decision) {
    return (
      <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-6 flex flex-col items-center justify-center min-h-[300px]">
        <RefreshCw className="w-8 h-8 text-cyan-400 animate-spin mb-3" />
        <p className="text-slate-400 text-xs font-mono">Synchronizing Adaptive Sensing Orchestration State...</p>
      </div>
    );
  }

  const levelInfo = getLevelBadge(decision?.monitoring_level);

  return (
    <div className="bg-slate-900/90 border border-slate-800/80 rounded-xl p-5 shadow-2xl space-y-5">
      {/* Top Header */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-800/60 pb-4">
        <div className="flex items-center space-x-3">
          <div className="p-2.5 rounded-lg bg-cyan-500/10 border border-cyan-500/30 text-cyan-400">
            <Cpu className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <h3 className="text-sm font-bold tracking-wider text-slate-100 uppercase">
                Adaptive Analytical Sensing Orchestrator
              </h3>
              <span className="text-[10px] px-2 py-0.5 rounded bg-cyan-950/80 text-cyan-400 border border-cyan-500/30 font-mono">
                PHASE 16 ADVISORY
              </span>
            </div>
            <p className="text-xs text-slate-400">
              Dynamic analytical compute &amp; evidence escalation based on real-time risk, trajectory, and uncertainty.
            </p>
          </div>
        </div>

        <div className="flex items-center space-x-2">
          <button
            onClick={() => setShowQueue(!showQueue)}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center space-x-1.5 transition-all border ${
              showQueue 
                ? 'bg-cyan-500 text-slate-950 border-cyan-400 shadow-lg shadow-cyan-500/20' 
                : 'bg-slate-800/80 hover:bg-slate-700/80 text-slate-200 border-slate-700'
            }`}
          >
            <ListOrdered className="w-3.5 h-3.5" />
            <span>National Queue ({nationalQueue.length})</span>
          </button>

          <button
            onClick={fetchAdaptiveData}
            disabled={evaluating}
            className="p-1.5 rounded-lg bg-slate-800/80 hover:bg-slate-700/80 text-slate-300 border border-slate-700 transition-all"
            title="Refresh Orchestration State"
          >
            <RefreshCw className={`w-4 h-4 ${evaluating ? 'animate-spin text-cyan-400' : ''}`} />
          </button>
        </div>
      </div>

      {/* National Priority Queue Drawer (when opened) */}
      {showQueue && (
        <div className="bg-slate-950/80 border border-cyan-500/30 rounded-lg p-4 space-y-3">
          <div className="flex items-center justify-between border-b border-slate-800 pb-2">
            <span className="text-xs font-bold text-cyan-400 uppercase tracking-wider flex items-center space-x-1.5">
              <Layers className="w-4 h-4" />
              <span>National Surveillance Priority Queue (Aging &amp; Starvation Guard Active)</span>
            </span>
            <span className="text-[10px] text-slate-400 font-mono">Dynamic Lambda: +15 pts/min aging</span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs font-mono">
              <thead>
                <tr className="text-slate-400 border-b border-slate-800 text-[10px] uppercase">
                  <th className="pb-1.5 pl-2">Rank</th>
                  <th className="pb-1.5">Facility / Hub</th>
                  <th className="pb-1.5">Level</th>
                  <th className="pb-1.5">State</th>
                  <th className="pb-1.5">Priority Score</th>
                  <th className="pb-1.5">Last Observed</th>
                  <th className="pb-1.5 pr-2">Evidence Requests</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-900/60">
                {nationalQueue.map((item) => (
                  <tr key={item.facility_id} className={`hover:bg-slate-900/40 ${item.facility_id === facilityId ? 'bg-cyan-950/30 font-semibold' : ''}`}>
                    <td className="py-2 pl-2 text-cyan-400 font-bold">#{item.rank}</td>
                    <td className="py-2 text-slate-200">{item.facility_name}</td>
                    <td className="py-2 text-[11px] text-slate-300">{item.monitoring_level.replace('LEVEL_', 'L')}</td>
                    <td className="py-2">
                      <span className={`px-1.5 py-0.5 rounded text-[10px] border ${
                        item.hazard_state === 'CRITICAL' ? 'bg-red-500/20 text-red-400 border-red-500/40' :
                        item.hazard_state === 'HAZARD_DEVELOPING' ? 'bg-amber-500/20 text-amber-400 border-amber-500/40' :
                        'bg-emerald-500/20 text-emerald-400 border-emerald-500/40'
                      }`}>
                        {item.hazard_state}
                      </span>
                    </td>
                    <td className="py-2 text-cyan-300">{item.priority_score} pts</td>
                    <td className="py-2 text-slate-400">{item.last_observation_age_sec}s ago</td>
                    <td className="py-2 pr-2 text-slate-300">{item.requested_evidence_count} signals</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Main Monitoring Level Card */}
      <div className={`p-4 rounded-xl border ${levelInfo.bg} flex flex-col md:flex-row md:items-center justify-between gap-4`}>
        <div className="space-y-1">
          <div className="flex items-center space-x-2">
            <span className="text-xs font-mono font-bold tracking-wide uppercase px-2 py-0.5 rounded bg-slate-950/60 border border-current">
              {decision?.monitoring_level}
            </span>
            <span className={`text-[10px] px-2 py-0.5 rounded font-mono font-bold border ${getPriorityBadge(decision?.priority)}`}>
              PRIORITY: {decision?.priority} ({decision?.priority_score} pts)
            </span>
          </div>
          <h4 className="text-base font-extrabold text-slate-100">{levelInfo.label}</h4>
          <p className="text-xs opacity-90">{levelInfo.desc}</p>
        </div>

        {/* Cooldown / Hysteresis Status */}
        {decision?.is_in_cooldown && (
          <div className="bg-slate-950/60 p-2.5 rounded-lg border border-amber-500/40 flex items-center space-x-2.5 text-xs text-amber-300">
            <Clock className="w-4 h-4 animate-spin text-amber-400" />
            <div>
              <span className="font-bold block">Hysteresis Cooldown Active</span>
              <span className="text-[11px] opacity-80">{decision.cooldown_remaining_sec}s remaining before downward transition</span>
            </div>
          </div>
        )}
      </div>

      {/* Reason & Value of Information Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Left: Decision Reason & Policy Details */}
        <div className="bg-slate-950/40 border border-slate-800 rounded-lg p-3.5 space-y-3">
          <span className="text-[11px] font-bold text-slate-300 uppercase tracking-wider block border-b border-slate-800 pb-1.5">
            Orchestration Reason &amp; Active Policy
          </span>
          <p className="text-xs text-slate-200 leading-relaxed font-sans">
            {decision?.reason}
          </p>

          <div className="grid grid-cols-2 gap-2 text-[11px] font-mono pt-1">
            <div className="bg-slate-900/80 p-2 rounded border border-slate-800">
              <span className="text-slate-400 block text-[10px]">Telemetry Window:</span>
              <span className="text-cyan-400 font-bold">{decision?.applied_policy?.telemetry_evaluation_window_sec}s</span>
            </div>
            <div className="bg-slate-900/80 p-2 rounded border border-slate-800">
              <span className="text-slate-400 block text-[10px]">Sampling Cadence:</span>
              <span className="text-cyan-400 font-bold">{decision?.applied_policy?.telemetry_sampling_interval_sec}s</span>
            </div>
            <div className="bg-slate-900/80 p-2 rounded border border-slate-800">
              <span className="text-slate-400 block text-[10px]">Thermal Vision Mode:</span>
              <span className="text-amber-400 font-bold">{decision?.applied_policy?.thermal_camera_tracking_mode}</span>
            </div>
            <div className="bg-slate-900/80 p-2 rounded border border-slate-800">
              <span className="text-slate-400 block text-[10px]">Multimodal Fusion Cadence:</span>
              <span className="text-emerald-400 font-bold">{decision?.applied_policy?.multi_modal_fusion_cadence_sec}s</span>
            </div>
          </div>
        </div>

        {/* Right: Prioritized Evidence Requests & Value of Information */}
        <div className="bg-slate-950/40 border border-slate-800 rounded-lg p-3.5 space-y-3">
          <span className="text-[11px] font-bold text-slate-300 uppercase tracking-wider block border-b border-slate-800 pb-1.5">
            Targeted Evidence Requests (Value of Information)
          </span>

          {decision?.value_of_information?.length > 0 ? (
            <div className="space-y-2">
              {decision.value_of_information.map((item, idx) => (
                <div key={idx} className="bg-slate-900/80 p-2.5 rounded-lg border border-slate-800 text-xs space-y-1">
                  <div className="flex items-center justify-between">
                    <span className="text-cyan-400 font-mono font-bold">{item.target_modality} &rarr; {item.specific_signal}</span>
                    <span className={`text-[10px] px-1.5 py-0.5 rounded font-mono border ${getPriorityBadge(item.urgency)}`}>
                      -{Math.round(item.expected_uncertainty_reduction * 100)}% UNCERTAINTY
                    </span>
                  </div>
                  <p className="text-slate-400 text-[11px]">{item.rationale}</p>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-xs text-slate-400 p-3 bg-slate-900/60 rounded border border-slate-800 flex items-center space-x-2">
              <CheckCircle2 className="w-4 h-4 text-emerald-400" />
              <span>Routine baseline observations sufficient. No targeted evidence acquisition requested.</span>
            </div>
          )}

          {/* Acknowledgement Status */}
          <div className="pt-2 flex items-center justify-between border-t border-slate-800/60">
            {decision?.acknowledged ? (
              <div className="text-xs text-emerald-400 flex items-center space-x-1.5 font-mono">
                <CheckSquare className="w-4 h-4" />
                <span>Acknowledged by {decision.acknowledged_by}</span>
              </div>
            ) : (
              <button
                onClick={handleAcknowledge}
                disabled={acknowledging}
                className="px-3 py-1.5 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-slate-950 text-xs font-bold transition-all flex items-center space-x-1.5 shadow-lg shadow-cyan-600/20"
              >
                <CheckSquare className="w-3.5 h-3.5" />
                <span>{acknowledging ? 'Acknowledging...' : 'Acknowledge Policy'}</span>
              </button>
            )}

            {ackSuccess && (
              <span className="text-xs text-emerald-400 font-mono animate-fade-in">Logged in Audit Trail</span>
            )}
          </div>
        </div>
      </div>

      {/* Interactive Scenario Simulation Strip */}
      <div className="bg-slate-950/60 border border-slate-800 rounded-lg p-3 space-y-2">
        <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">
          Simulation &amp; Hysteresis Verification Strip:
        </span>
        <div className="flex flex-wrap gap-2">
          <button
            onClick={() => handleSimulateScenario('NORMAL')}
            className="px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-mono border border-slate-700"
          >
            Nominal (Level 0)
          </button>
          <button
            onClick={() => handleSimulateScenario('WATCH')}
            className="px-2.5 py-1 rounded bg-blue-950 hover:bg-blue-900 text-blue-300 text-xs font-mono border border-blue-800"
          >
            Minor Drift (Level 1)
          </button>
          <button
            onClick={() => handleSimulateScenario('ABNORMAL')}
            className="px-2.5 py-1 rounded bg-yellow-950 hover:bg-yellow-900 text-yellow-300 text-xs font-mono border border-yellow-800"
          >
            Deviation (Level 2)
          </button>
          <button
            onClick={() => handleSimulateScenario('HAZARD_DEVELOPING')}
            className="px-2.5 py-1 rounded bg-amber-950 hover:bg-amber-900 text-amber-300 text-xs font-mono border border-amber-800"
          >
            Developing Hazard (Level 3)
          </button>
          <button
            onClick={() => handleSimulateScenario('CRITICAL')}
            className="px-2.5 py-1 rounded bg-red-950 hover:bg-red-900 text-red-300 text-xs font-mono border border-red-800"
          >
            Acute Critical (Level 4)
          </button>
          <button
            onClick={() => handleSimulateScenario('WATCH', 0.65, ['THERMAL_CAMERA', 'GAS_SNIFFER'])}
            className="px-2.5 py-1 rounded bg-purple-950 hover:bg-purple-900 text-purple-300 text-xs font-mono border border-purple-800"
          >
            High Uncertainty (+Missing Sensors)
          </button>
        </div>
      </div>
    </div>
  );
}
