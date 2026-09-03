import React, { useState } from 'react';
import { 
  Sliders, Play, RefreshCw, CheckCircle2, AlertTriangle, 
  Flame, Satellite, Building2, Siren, ArrowRight, Eye,
  Sparkles, Layers, ShieldAlert, Radio, Activity
} from 'lucide-react';
import { api } from '../../services/api';

export default function SimulationLab({ onNavigate }) {
  const [selectedScenario, setSelectedScenario] = useState('SCENARIO_D');
  const [activeStep, setActiveStep] = useState(1);
  const [running, setRunning] = useState(false);
  const [executionResult, setExecutionResult] = useState(null);
  const [error, setError] = useState(null);

  const scenarios = [
    {
      id: 'SCENARIO_A',
      title: 'Scenario A: Normal Baseline',
      desc: 'Facility operating within nominal empirical parameters. (18 MW, Level 1 Routine).',
      severity: 'NOMINAL',
      badgeColor: 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40'
    },
    {
      id: 'SCENARIO_B',
      title: 'Scenario B: New Satellite Thermal Anomaly',
      desc: 'Unattributed thermal hotspot detected; spatial attribution engine links to nearest boundary.',
      severity: 'WATCH',
      badgeColor: 'bg-cyan-500/20 text-cyan-300 border-cyan-500/40'
    },
    {
      id: 'SCENARIO_C',
      title: 'Scenario C: Persistent Industrial Source',
      desc: 'Empirical fingerprint baseline comparison confirms routine petrochemical flare.',
      severity: 'ROUTINE',
      badgeColor: 'bg-orange-500/20 text-orange-300 border-orange-500/40'
    },
    {
      id: 'SCENARIO_D',
      title: 'Scenario D: Developing Telemetry Hazard',
      desc: 'High-frequency telemetry exhibits acute CUSUM pressure drift (+1.45 bar/min).',
      severity: 'ABNORMAL',
      badgeColor: 'bg-amber-500/20 text-amber-300 border-amber-500/40'
    },
    {
      id: 'SCENARIO_E',
      title: 'Scenario E: Cross-Modal Confirmation',
      desc: 'Telemetry pressure surge corroborated by radiometric thermal camera hotspot (94% confidence).',
      severity: 'HIGH CERTAINTY',
      badgeColor: 'bg-purple-500/20 text-purple-300 border-purple-500/40'
    },
    {
      id: 'SCENARIO_F',
      title: 'Scenario F: Conflicting Evidence',
      desc: 'Satellite flags extreme spike while on-site sensors report nominal; system rejects false alarm.',
      severity: 'CONFLICT',
      badgeColor: 'bg-slate-700 text-slate-300 border-slate-600'
    },
    {
      id: 'SCENARIO_H',
      title: 'Scenario H: Sensor Loss / Abstention',
      desc: 'Critical telemetry and cameras disconnected; system explicitly abstains (NEEDS_REVIEW).',
      severity: 'ABSTAIN',
      badgeColor: 'bg-amber-500/20 text-amber-300 border-amber-500/40'
    },
    {
      id: 'SCENARIO_I',
      title: 'Scenario I: Confirmed Critical Incident',
      desc: 'Confirmed industrial fire triggering ALOHA plume dispersion, evacuation routes, and resource dispatch.',
      severity: 'CRITICAL',
      badgeColor: 'bg-red-500/20 text-red-300 border-red-500/40'
    },
    {
      id: 'SCENARIO_J',
      title: 'Scenario J: Hazard Cooldown & Recovery',
      desc: 'Thermal and process values subside; hysteresis dwell timer safely steps down surveillance.',
      severity: 'RECOVERY',
      badgeColor: 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40'
    }
  ];

  const demoSteps = [
    { step: 1, title: 'Thermal Anomaly Detected', desc: 'Raw VIIRS/MODIS radiative detection normalized into canonical event.', icon: Satellite },
    { step: 2, title: 'Spatiotemporal Source Identified', desc: 'Hotspots clustered with H3 Level-9 indexing to track persistence and dispersion.', icon: Flame },
    { step: 3, title: 'Industrial Context & Land Cover', desc: '10m Copernicus ESA WorldCover confirms industrial built-up area and facility polygon.', icon: Building2 },
    { step: 4, title: 'Process Telemetry Ingested', desc: 'High-frequency read-only process stream received via OPC-UA/MQTT gateway.', icon: Activity },
    { step: 5, title: 'Hazard Trajectory Predicted', desc: 'CUSUM change-point trend models short-horizon deviation (10m, 30m, 60m).', icon: Radio },
    { step: 6, title: 'Dempster-Shafer Evidential Fusion', desc: 'Mathematical evidence combination across all active sensing modalities.', icon: Layers },
    { step: 7, title: 'Adaptive Surveillance Orchestrated', desc: 'Surveillance level escalated with state hysteresis and national priority ranking.', icon: Sliders },
    { step: 8, title: 'Incident Packet & Response Action', desc: 'ALOHA chemical plume modeled, evacuation routes computed, human review requested.', icon: Siren }
  ];

  const handleRunScenario = async () => {
    try {
      setRunning(true);
      setError(null);
      const res = await api.runGoldenScenario(selectedScenario, 'FAC-IN-DAHEJ-001');
      setExecutionResult(res);
    } catch (err) {
      console.error('Scenario execution failed:', err);
      setError(err.message || 'Failed to execute scenario');
    } finally {
      setRunning(false);
    }
  };

  return (
    <div className="space-y-6 font-mono p-1">
      {/* Prominent Reference Environment Banner */}
      <div className="bg-gradient-to-r from-purple-950/80 via-slate-900/90 to-slate-950 border border-purple-500/40 rounded-2xl p-5 shadow-2xl flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="space-y-1">
          <div className="flex items-center space-x-2">
            <span className="text-[10px] font-bold px-2.5 py-0.5 rounded-full bg-purple-900/60 border border-purple-500/40 text-purple-300">
              SIMULATION LAB
            </span>
            <span className="text-[10px] text-slate-400 font-sans">
              Reference Environment: <strong className="text-white font-mono">Dahej Petrochemical Complex Alpha</strong>
            </span>
          </div>
          <h2 className="text-xl font-extrabold text-white tracking-tight">
            Controlled Industrial Simulation &amp; Verification
          </h2>
          <p className="text-xs text-slate-400 font-sans max-w-2xl">
            Execute deterministic industrial scenarios through the real 11-stage backend pipeline. Simulated data is strictly tagged and never leaks into live production monitoring.
          </p>
        </div>

        <button
          onClick={handleRunScenario}
          disabled={running}
          className="px-5 py-3 rounded-xl bg-purple-600 hover:bg-purple-500 text-white font-bold text-xs shadow-lg shadow-purple-600/30 transition-all flex items-center space-x-2 shrink-0 self-start md:self-auto disabled:opacity-50"
        >
          <Play className={`w-4 h-4 ${running ? 'animate-spin' : ''}`} />
          <span>{running ? 'Executing Pipeline...' : 'Run Selected Scenario'}</span>
        </button>
      </div>

      {/* 8-Stage Step-by-Step Guided Technical Demo */}
      <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-5 shadow-xl space-y-4">
        <div className="flex items-center justify-between border-b border-slate-800 pb-3">
          <div className="flex items-center space-x-2.5">
            <Sparkles className="w-4 h-4 text-cyan-400" />
            <h3 className="text-xs font-bold text-white uppercase tracking-wider">
              Step-by-Step Guided Technical Demonstration
            </h3>
          </div>
          <span className="text-[10px] text-slate-500">8 Canonical Architecture Stages</span>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-8 gap-2">
          {demoSteps.map((s) => {
            const Icon = s.icon;
            const isCurrent = activeStep === s.step;
            const isCompleted = activeStep > s.step;

            return (
              <button
                key={s.step}
                onClick={() => setActiveStep(s.step)}
                className={`p-3 rounded-xl border text-left transition-all flex flex-col justify-between min-h-[110px] ${
                  isCurrent 
                    ? 'bg-cyan-950/60 border-cyan-500/60 text-white shadow-md'
                    : (isCompleted ? 'bg-slate-950/80 border-slate-800 text-slate-300' : 'bg-slate-950/40 border-slate-800/60 text-slate-500')
                }`}
              >
                <div className="flex items-center justify-between w-full">
                  <span className="text-[10px] font-bold font-mono">Step {s.step}</span>
                  <Icon className={`w-3.5 h-3.5 ${isCurrent ? 'text-cyan-400' : 'text-slate-500'}`} />
                </div>
                <div>
                  <h4 className="text-[11px] font-bold leading-tight">{s.title}</h4>
                </div>
              </button>
            );
          })}
        </div>

        {/* Selected Step Explanation Card */}
        <div className="bg-slate-950/80 border border-cyan-500/30 rounded-xl p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="space-y-1">
            <span className="text-[10px] text-cyan-400 font-bold uppercase">
              Active Demonstration Stage: Step {activeStep} of 8
            </span>
            <h4 className="text-sm font-bold text-white">{demoSteps[activeStep - 1].title}</h4>
            <p className="text-xs text-slate-300 font-sans">{demoSteps[activeStep - 1].desc}</p>
          </div>

          <div className="flex items-center space-x-2 shrink-0">
            <button
              onClick={() => setActiveStep(prev => Math.max(1, prev - 1))}
              disabled={activeStep === 1}
              className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-bold disabled:opacity-40"
            >
              Previous
            </button>
            <button
              onClick={() => setActiveStep(prev => Math.min(8, prev + 1))}
              disabled={activeStep === 8}
              className="px-3 py-1.5 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-white text-xs font-bold disabled:opacity-40"
            >
              Next Step
            </button>
          </div>
        </div>
      </div>

      {/* Scenario Selection Matrix */}
      <div className="space-y-3">
        <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider">
          Predefined Industrial Scenarios
        </h3>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
          {scenarios.map((scen) => (
            <div
              key={scen.id}
              onClick={() => setSelectedScenario(scen.id)}
              className={`p-4 rounded-xl border cursor-pointer transition-all ${
                selectedScenario === scen.id
                  ? 'bg-slate-900 border-cyan-500 shadow-lg shadow-cyan-500/10'
                  : 'bg-slate-900/60 border-slate-800 hover:border-slate-700'
              }`}
            >
              <div className="flex items-start justify-between gap-2 mb-2">
                <h4 className="text-xs font-bold text-white">{scen.title}</h4>
                <span className={`text-[9px] px-2 py-0.5 rounded-full font-bold border shrink-0 ${scen.badgeColor}`}>
                  {scen.severity}
                </span>
              </div>
              <p className="text-xs text-slate-400 font-sans">{scen.desc}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Execution Results Strip (When Run) */}
      {executionResult && (
        <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-5 shadow-2xl space-y-4">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3">
            <div className="space-y-0.5">
              <span className="text-[10px] text-emerald-400 font-bold uppercase flex items-center gap-1.5">
                <CheckCircle2 className="w-3.5 h-3.5" />
                Pipeline Execution Trace: {executionResult.trace_id}
              </span>
              <h4 className="text-xs font-bold text-white font-mono">
                Duration: {executionResult.total_duration_ms} ms &bull; Status: {executionResult.overall_status}
              </h4>
            </div>

            <button
              onClick={() => onNavigate && onNavigate('impact')}
              className="px-3 py-1.5 rounded-lg bg-red-600 hover:bg-red-500 text-white text-xs font-bold flex items-center space-x-1.5"
            >
              <span>Open Response Analysis</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>

          {/* 11 Stages Timeline Summary */}
          <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-6 gap-2 text-[10px]">
            {executionResult.stages_executed?.map((st) => (
              <div key={st.stage_index} className="bg-slate-950 p-2 rounded-lg border border-slate-800 space-y-1">
                <span className="text-slate-500 font-bold block">{st.stage_index}. {st.stage_name.replace(/_/g, ' ')}</span>
                <span className="text-emerald-400 font-bold block">{st.status} ({st.duration_ms}ms)</span>
                <p className="text-slate-400 font-sans text-[9px] truncate">{st.summary}</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
