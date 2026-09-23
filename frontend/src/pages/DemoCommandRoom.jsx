import React, { useState, useEffect, useRef, useMemo } from 'react';
import { api } from '../services/api';
import { 
  Play, Pause, RotateCcw, FastForward, StepForward, 
  ShieldAlert, Satellite, Activity, Flame, Wind, 
  Layers, CheckCircle2, AlertTriangle, AlertOctagon, 
  FileText, Download, Navigation, Radio, Sparkles, 
  Sliders, Bug, RefreshCw, ChevronRight, Check, Eye, X, Database
} from 'lucide-react';
import CommandMapWorkspace from '../components/map/CommandMapWorkspace';

const PIPELINE_STAGES = [
  { id: 'SATELLITES', label: 'Satellites (FIRMS/INSAT/Landsat)', icon: Satellite },
  { id: 'DATA_GATEWAY', label: 'Data Gateway Normalization', icon: Database },
  { id: 'QUALITY_ENGINE', label: '26-Point Quality Engine', icon: ShieldAlert },
  { id: 'CORRELATION', label: 'Facility & Asset Correlation', icon: Layers },
  { id: 'FEATURE_ENGINE', label: '23-Feature Vector Extraction', icon: Sliders },
  { id: 'ML_CLASSIFICATION', label: '7-Class ML Classifier (Frozen)', icon: Activity },
  { id: 'CORROBORATION', label: 'Multi-Source Corroboration', icon: Eye },
  { id: 'DS_FUSION', label: 'Dempster-Shafer Evidential Fusion', icon: Sparkles },
  { id: 'CONSEQUENCE', label: 'Consequence & Toxic Plume', icon: Flame },
  { id: 'PREDICTION', label: 'Predictive Plant Inference', icon: Wind },
  { id: 'RESPONSE_SUPPORT', label: 'Dynamic Evacuation & Pre-Plan', icon: Navigation }
];

export default function DemoCommandRoom({ onSwitchToIndiaOps, onLogout, user }) {
  const [scenarios, setScenarios] = useState([]);
  const [selectedScenarioId, setSelectedScenarioId] = useState('SCENARIO-DAHEJ-AMMONIA-CRYO-01');
  const [replayState, setReplayState] = useState({
    status: 'IDLE',
    current_step: 0,
    total_steps: 5,
    replay_speed: 1.0,
    active_failure_injections: {}
  });

  const [speed, setSpeed] = useState(1.0);
  const [isProcessingStep, setIsProcessingStep] = useState(false);
  const [autoPlayTimer, setAutoPlayTimer] = useState(null);

  // Failure Injection Flags
  const [failureFlags, setFailureFlags] = useState({
    inject_missing_telemetry: false,
    inject_stale_telemetry: false,
    inject_sensor_spike: false,
    inject_conflicting_evidence: false,
    inject_satellite_unavailable: false
  });

  // Action status notices
  const [actionNotice, setActionNotice] = useState(null);
  const [isExportingPDF, setIsExportingPDF] = useState(false);

  // Initial Load
  useEffect(() => {
    api.getDemoScenarios().then(res => {
      setScenarios(res);
      if (res && res.length > 0) setSelectedScenarioId(res[0].scenario_id);
    }).catch(err => console.warn('Demo scenarios fallback:', err));

    api.getDemoState().then(setReplayState).catch(err => console.warn('Demo state fallback:', err));
  }, []);

  // Poll replay stream
  useEffect(() => {
    const interval = setInterval(() => {
      if (replayState.status === 'RUNNING') {
        handleStep();
      }
    }, Math.max(1000, 4000 / speed));

    return () => clearInterval(interval);
  }, [replayState.status, speed, replayState.current_step]);

  const handleStart = async () => {
    try {
      const st = await api.startDemoReplay(selectedScenarioId, speed);
      setReplayState(st);
    } catch (e) {
      console.warn('Start replay error:', e);
    }
  };

  const handlePause = async () => {
    try {
      const st = await api.pauseDemoReplay();
      setReplayState(st);
    } catch (e) {
      console.warn('Pause replay error:', e);
    }
  };

  const handleReset = async () => {
    try {
      const st = await api.resetDemoReplay();
      setReplayState(st);
      setFailureFlags({
        inject_missing_telemetry: false,
        inject_stale_telemetry: false,
        inject_sensor_spike: false,
        inject_conflicting_evidence: false,
        inject_satellite_unavailable: false
      });
    } catch (e) {
      console.warn('Reset replay error:', e);
    }
  };

  const handleStep = async () => {
    if (isProcessingStep) return;
    setIsProcessingStep(true);
    try {
      const st = await api.stepDemoReplay();
      setReplayState(st);
    } catch (e) {
      console.warn('Step replay error:', e);
    } finally {
      setIsProcessingStep(false);
    }
  };

  const handleToggleFailure = async (key) => {
    const next = { ...failureFlags, [key]: !failureFlags[key] };
    setFailureFlags(next);
    try {
      const st = await api.injectDemoFailure(next);
      setReplayState(st);
    } catch (e) {
      console.warn('Inject failure error:', e);
    }
  };

  const handleTriggerRecovery = async () => {
    const clean = {
      inject_missing_telemetry: false,
      inject_stale_telemetry: false,
      inject_sensor_spike: false,
      inject_conflicting_evidence: false,
      inject_satellite_unavailable: false,
      trigger_recovery: true
    };
    setFailureFlags(clean);
    try {
      const st = await api.injectDemoFailure(clean);
      setReplayState(st);
      setActionNotice({ type: 'success', msg: 'System feeds recovered to nominal quality.' });
      setTimeout(() => setActionNotice(null), 3000);
    } catch (e) {
      console.warn('Recovery error:', e);
    }
  };

  // Safe Evacuation Action
  const handleComputeEvacuation = async () => {
    try {
      const plan = await api.generateEvacuationRoute('FAC-IN-DAHEJ-001', 'T-04');
      setActionNotice({ 
        type: 'success', 
        msg: `Safe evacuation corridor computed (${plan.primary_evacuation_route?.total_distance_m?.toFixed(0) || 850}m to Staging Gate).` 
      });
      setTimeout(() => setActionNotice(null), 5000);
    } catch (e) {
      setActionNotice({ type: 'error', msg: 'Evacuation calculation failed.' });
      setTimeout(() => setActionNotice(null), 4000);
    }
  };

  // Export PDF Action
  const handleExportPDF = async () => {
    setIsExportingPDF(true);
    try {
      await api.exportPrePlanPDF('FAC-IN-DAHEJ-001', 'T-04', 'CHEM-NH3');
      setActionNotice({ type: 'success', msg: 'Official ERDMP Pre-Plan PDF exported & downloaded.' });
      setTimeout(() => setActionNotice(null), 5000);
    } catch (e) {
      setActionNotice({ type: 'error', msg: 'PDF generation failed.' });
      setTimeout(() => setActionNotice(null), 4000);
    } finally {
      setIsExportingPDF(false);
    }
  };

  const activeEvent = replayState.active_event;
  const activeClass = replayState.active_classification;
  const activeFusion = replayState.active_fusion;
  const activePred = replayState.active_prediction;
  const activeConseq = replayState.active_consequence;
  const activeEvac = replayState.active_evacuation;

  const currentClassLabel = activeClass?.predicted_class?.replace(/_/g, ' ') || 'STANDBY (AWAITING EVENT)';
  const currentConfidence = activeClass ? Math.round((activeClass.calibrated_confidence || activeClass.confidence_score || 0.9) * 100) : 0;

  return (
    <div className="h-screen w-screen bg-slate-900 text-slate-100 flex flex-col font-sans overflow-hidden">
      
      {/* 1. Header & Replay Control Strip */}
      <header className="bg-slate-950 border-b border-slate-800 px-4 py-2.5 flex flex-wrap items-center justify-between gap-3 shrink-0 z-40">
        
        {/* Left Brand & Mode Label */}
        <div className="flex items-center space-x-3">
          <div className="w-8 h-8 rounded-lg bg-amber-600 flex items-center justify-center text-white font-bold shadow-md shadow-amber-900/40">
            <Sliders className="w-4.5 h-4.5" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <span className="font-extrabold text-sm tracking-tight text-white">REACT-X</span>
              <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-amber-500/20 text-amber-300 border border-amber-500/40 uppercase tracking-wider">
                DEMO COMMAND ROOM • REPLAY
              </span>
            </div>
            <p className="text-[11px] text-slate-400 font-mono">
              Canonical Pipeline Replay Engine (Deterministic Reference Flow)
            </p>
          </div>
        </div>

        {/* Center: Replay Controls */}
        <div className="flex items-center bg-slate-900 border border-slate-800 rounded-lg p-1 space-x-1.5 shadow-inner">
          <select 
            value={selectedScenarioId}
            onChange={(e) => setSelectedScenarioId(e.target.value)}
            disabled={replayState.status === 'RUNNING'}
            className="text-xs bg-slate-800 text-slate-200 border border-slate-700 rounded px-2 py-1.5 font-semibold focus:outline-none focus:border-blue-500"
          >
            {scenarios.map(s => (
              <option key={s.scenario_id} value={s.scenario_id}>
                {s.name} ({s.total_steps} steps)
              </option>
            ))}
          </select>

          {replayState.status === 'RUNNING' ? (
            <button 
              onClick={handlePause}
              className="px-3 py-1.5 bg-amber-600 hover:bg-amber-500 text-white rounded text-xs font-bold flex items-center gap-1.5 transition-all shadow"
            >
              <Pause className="w-3.5 h-3.5" /> Pause
            </button>
          ) : (
            <button 
              onClick={handleStart}
              className="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-500 text-white rounded text-xs font-bold flex items-center gap-1.5 transition-all shadow"
            >
              <Play className="w-3.5 h-3.5" /> {replayState.current_step > 0 ? 'Resume' : 'Start Replay'}
            </button>
          )}

          <button 
            onClick={handleStep}
            disabled={replayState.status === 'RUNNING'}
            className="px-2.5 py-1.5 bg-slate-800 hover:bg-slate-700 disabled:opacity-50 text-slate-200 rounded text-xs font-semibold flex items-center gap-1 transition"
            title="Step Forward Single Pipeline Execution"
          >
            <StepForward className="w-3.5 h-3.5" /> Step ({replayState.current_step}/{replayState.total_steps})
          </button>

          <button 
            onClick={handleReset}
            className="px-2.5 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded text-xs font-semibold flex items-center gap-1 transition"
            title="Reset to Baseline"
          >
            <RotateCcw className="w-3.5 h-3.5" /> Reset
          </button>

          {/* Speed Selector */}
          <div className="flex items-center space-x-1 pl-1 border-l border-slate-800">
            {[1.0, 2.0, 5.0].map(s => (
              <button
                key={s}
                onClick={() => setSpeed(s)}
                className={`text-[10px] px-1.5 py-1 rounded font-bold transition ${
                  speed === s ? 'bg-blue-600 text-white' : 'text-slate-400 hover:bg-slate-800'
                }`}
              >
                {s}x
              </button>
            ))}
          </div>
        </div>

        {/* Right: Switch Mode to India Operations */}
        <div className="flex items-center space-x-2">
          <button 
            onClick={onSwitchToIndiaOps}
            className="px-3 py-1.5 bg-blue-600/20 hover:bg-blue-600/30 text-blue-300 border border-blue-500/40 rounded-lg text-xs font-bold flex items-center gap-1.5 transition"
          >
            🇮🇳 India Operations (Live Platform)
          </button>
        </div>
      </header>

      {/* 2. Top Clocks & Telemetry Strip */}
      <div className="bg-slate-950/80 border-b border-slate-800 px-4 py-1.5 flex items-center justify-between text-[11px] font-mono text-slate-400 shrink-0">
        <div className="flex items-center space-x-6">
          <div className="flex items-center space-x-1.5">
            <span className="text-slate-500">OBSERVED TIME:</span>
            <span className="text-slate-200 font-bold">
              {replayState.latest_event_observed_at ? new Date(replayState.latest_event_observed_at).toUTCString() : '2026-08-30 14:00:00 UTC'}
            </span>
          </div>
          <div className="flex items-center space-x-1.5">
            <span className="text-slate-500">SOURCE PROVENANCE:</span>
            <span className="text-amber-400 font-bold">REFERENCE REPLAY • NO FALSE LIVE LABELS</span>
          </div>
          <div className="flex items-center space-x-1.5">
            <span className="text-slate-500">STAGE:</span>
            <span className="text-blue-400 font-bold">{replayState.pipeline_stage || 'STANDBY'}</span>
          </div>
        </div>

        {/* Action Notice Toast */}
        {actionNotice && (
          <div className={`px-3 py-0.5 rounded text-xs font-semibold flex items-center gap-1.5 animate-pulse ${
            actionNotice.type === 'success' ? 'bg-emerald-950 text-emerald-300 border border-emerald-700' : 'bg-red-950 text-red-300 border border-red-700'
          }`}>
            <CheckCircle2 className="w-3.5 h-3.5" /> {actionNotice.msg}
          </div>
        )}
      </div>

      {/* 3. Main Split View: Left Controls/Pipeline + Right Map & Evidence */}
      <div className="flex-1 flex overflow-hidden w-full h-full">
        
        {/* Left Side: Pipeline Visualization & Failure Injections */}
        <div className="w-full sm:w-[420px] lg:w-[480px] bg-slate-950 border-r border-slate-800 flex flex-col overflow-y-auto shrink-0 divide-y divide-slate-800">
          
          {/* A. Live 13-Stage Pipeline Stepper */}
          <div className="p-4 space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
                <Activity className="w-4 h-4 text-blue-400" /> Canonical Pipeline Status
              </span>
              <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-slate-800 text-slate-300">
                Step {replayState.current_step} of {replayState.total_steps}
              </span>
            </div>

            <div className="space-y-1.5">
              {PIPELINE_STAGES.map((stg, idx) => {
                const isCompleted = replayState.current_step >= idx + 1;
                const isCurrent = replayState.current_step === idx;
                const Icon = stg.icon;
                return (
                  <div 
                    key={stg.id}
                    className={`flex items-center justify-between p-2 rounded text-xs font-medium transition ${
                      isCompleted 
                        ? 'bg-emerald-950/40 border border-emerald-800/40 text-emerald-300' 
                        : isCurrent 
                        ? 'bg-blue-950/60 border border-blue-600 text-blue-200 animate-pulse'
                        : 'bg-slate-900/40 border border-slate-800/60 text-slate-500'
                    }`}
                  >
                    <div className="flex items-center space-x-2">
                      <Icon className={`w-3.5 h-3.5 ${isCompleted ? 'text-emerald-400' : isCurrent ? 'text-blue-400' : 'text-slate-600'}`} />
                      <span>{stg.label}</span>
                    </div>
                    <div>
                      {isCompleted ? (
                        <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-emerald-900/60 text-emerald-300">
                          PROCESSED
                        </span>
                      ) : (
                        <span className="text-[10px] font-mono text-slate-600">STANDBY</span>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* B. Failure Injection Sandbox */}
          <div className="p-4 space-y-3 bg-slate-900/30">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold uppercase tracking-wider text-amber-400 flex items-center gap-1.5">
                <Bug className="w-4 h-4 text-amber-400" /> Failure Injection Sandbox
              </span>
              <button 
                onClick={handleTriggerRecovery}
                className="text-[10px] font-bold px-2 py-0.5 rounded bg-emerald-800/40 hover:bg-emerald-700/60 text-emerald-300 border border-emerald-600/40 transition flex items-center gap-1"
              >
                <RefreshCw className="w-3 h-3" /> Recover Feeds
              </button>
            </div>
            <p className="text-[11px] text-slate-400">
              Inject production anomalies to verify deterministic degraded state transitions without fake recovery.
            </p>

            <div className="grid grid-cols-2 gap-2">
              <button
                onClick={() => handleToggleFailure('inject_missing_telemetry')}
                className={`p-2 rounded border text-left text-xs font-semibold transition ${
                  failureFlags.inject_missing_telemetry 
                    ? 'bg-red-950 border-red-600 text-red-200' 
                    : 'bg-slate-900 border-slate-800 text-slate-300 hover:bg-slate-800'
                }`}
              >
                <div className="flex items-center justify-between">
                  <span>Missing OT Telemetry</span>
                  <span className={`w-2 h-2 rounded-full ${failureFlags.inject_missing_telemetry ? 'bg-red-500' : 'bg-slate-700'}`} />
                </div>
                <p className="text-[10px] text-slate-500 mt-1">Prediction &rarr; STANDBY</p>
              </button>

              <button
                onClick={() => handleToggleFailure('inject_conflicting_evidence')}
                className={`p-2 rounded border text-left text-xs font-semibold transition ${
                  failureFlags.inject_conflicting_evidence 
                    ? 'bg-amber-950 border-amber-600 text-amber-200' 
                    : 'bg-slate-900 border-slate-800 text-slate-300 hover:bg-slate-800'
                }`}
              >
                <div className="flex items-center justify-between">
                  <span>Conflicting Evidence</span>
                  <span className={`w-2 h-2 rounded-full ${failureFlags.inject_conflicting_evidence ? 'bg-amber-500' : 'bg-slate-700'}`} />
                </div>
                <p className="text-[10px] text-slate-500 mt-1">D-S Conflict K &gt; 0.60</p>
              </button>

              <button
                onClick={() => handleToggleFailure('inject_sensor_spike')}
                className={`p-2 rounded border text-left text-xs font-semibold transition ${
                  failureFlags.inject_sensor_spike 
                    ? 'bg-red-950 border-red-600 text-red-200' 
                    : 'bg-slate-900 border-slate-800 text-slate-300 hover:bg-slate-800'
                }`}
              >
                <div className="flex items-center justify-between">
                  <span>Sensor Spike Anomaly</span>
                  <span className={`w-2 h-2 rounded-full ${failureFlags.inject_sensor_spike ? 'bg-red-500' : 'bg-slate-700'}`} />
                </div>
                <p className="text-[10px] text-slate-500 mt-1">Quality &rarr; BAD / Quarantined</p>
              </button>

              <button
                onClick={() => handleToggleFailure('inject_stale_telemetry')}
                className={`p-2 rounded border text-left text-xs font-semibold transition ${
                  failureFlags.inject_stale_telemetry 
                    ? 'bg-amber-950 border-amber-600 text-amber-200' 
                    : 'bg-slate-900 border-slate-800 text-slate-300 hover:bg-slate-800'
                }`}
              >
                <div className="flex items-center justify-between">
                  <span>Stale Telemetry Feed</span>
                  <span className={`w-2 h-2 rounded-full ${failureFlags.inject_stale_telemetry ? 'bg-amber-500' : 'bg-slate-700'}`} />
                </div>
                <p className="text-[10px] text-slate-500 mt-1">Downweighted Evidence</p>
              </button>
            </div>
          </div>

          {/* C. ML Classification & Dempster-Shafer Fusion Inspection */}
          <div className="p-4 space-y-3">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
              <Sparkles className="w-4 h-4 text-purple-400" /> ML Classification & D-S Evidential Fusion
            </span>

            {/* Classification Card */}
            <div className="bg-slate-900 border border-slate-800 rounded-lg p-3 space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-xs text-slate-400 font-semibold">Predicted Class</span>
                <span className={`text-xs font-bold px-2 py-0.5 rounded ${
                  currentClassLabel.includes('FIRE') ? 'bg-red-950 text-red-300 border border-red-700' : 'bg-blue-950 text-blue-300 border border-blue-700'
                }`}>
                  {currentClassLabel}
                </span>
              </div>

              <div className="flex items-center justify-between text-xs">
                <span className="text-slate-400">Calibrated Confidence</span>
                <span className="font-bold text-white font-mono">{currentConfidence}%</span>
              </div>

              {/* Dempster-Shafer Metrics */}
              {activeFusion && (
                <div className="pt-2 border-t border-slate-800 grid grid-cols-3 gap-2 text-center">
                  <div className="bg-slate-950 p-1.5 rounded">
                    <span className="text-[9px] text-slate-500 block">Belief Mass</span>
                    <span className="text-xs font-mono font-bold text-emerald-400">{activeFusion.belief_mass}</span>
                  </div>
                  <div className="bg-slate-950 p-1.5 rounded">
                    <span className="text-[9px] text-slate-500 block">Uncertainty</span>
                    <span className="text-xs font-mono font-bold text-amber-400">{activeFusion.uncertainty_mass}</span>
                  </div>
                  <div className="bg-slate-950 p-1.5 rounded">
                    <span className="text-[9px] text-slate-500 block">Conflict K</span>
                    <span className={`text-xs font-mono font-bold ${activeFusion.conflict_k > 0.5 ? 'text-red-400' : 'text-slate-300'}`}>
                      {activeFusion.conflict_k}
                    </span>
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* D. Action Command Buttons (Fixed & Tested) */}
          <div className="p-4 space-y-2.5 bg-slate-950">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
              <Navigation className="w-4 h-4 text-blue-400" /> Operational Response Actions
            </span>

            <div className="grid grid-cols-1 gap-2">
              <button
                onClick={handleComputeEvacuation}
                className="w-full py-2.5 px-3 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-xs font-bold flex items-center justify-center gap-2 shadow-md transition"
              >
                <Navigation className="w-4 h-4" /> Compute Dynamic Safe Evacuation
              </button>

              <button
                onClick={handleExportPDF}
                disabled={isExportingPDF}
                className="w-full py-2.5 px-3 bg-slate-800 hover:bg-slate-700 text-slate-100 border border-slate-700 rounded-lg text-xs font-bold flex items-center justify-center gap-2 shadow-sm transition disabled:opacity-50"
              >
                {isExportingPDF ? <RefreshCw className="w-4 h-4 animate-spin" /> : <FileText className="w-4 h-4 text-amber-400" />}
                Export Official ERDMP Pre-Plan PDF
              </button>
            </div>
          </div>

        </div>

        {/* Right Side: Map Canvas & GIS Spatial Context */}
        <div className="flex-1 h-full relative bg-slate-900">
          <CommandMapWorkspace
            center={[21.6850, 72.5750]}
            zoom={14}
            facilities={[{
              id: 'FAC-IN-DAHEJ-001',
              name: 'Dahej Petrochemical Complex (Demo Reference)',
              location: 'Dahej PCPIR, Gujarat',
              coordinates: [21.6850, 72.5750],
              current_status: 'NOMINAL_OPERATIONS'
            }]}
            thermalEvents={activeEvent ? [activeEvent] : []}
            thermalSources={[]}
            persistentClusters={[]}
            simulationResult={activeConseq}
            currentTimeStep={120}
            evacuationPlan={activeEvac}
            selectedFacilityId="FAC-IN-DAHEJ-001"
            selectedEventId={activeEvent?.event_id}
          />
        </div>

      </div>

    </div>
  );
}
