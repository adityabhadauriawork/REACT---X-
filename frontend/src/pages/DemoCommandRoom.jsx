import React, { useState, useEffect, useRef, useMemo } from 'react';
import { api } from '../services/api';
import { 
  Play, Pause, RotateCcw, FastForward, StepForward, 
  ShieldAlert, Satellite, Activity, Flame, Wind, 
  Layers, CheckCircle2, AlertTriangle, AlertOctagon, 
  FileText, Download, Navigation, Radio, Sparkles, 
  Sliders, Bug, RefreshCw, ChevronRight, Check, Eye, X, Database,
  Lock, ShieldCheck, CheckCircle
} from 'lucide-react';
import CommandMapWorkspace from '../components/map/CommandMapWorkspace';

const PIPELINE_STAGES = [
  { id: 'INGESTION', label: '1. Ingestion & Data Gateway', sub: 'NASA FIRMS / ISRO MOSDAC / OT Gateway', icon: Database },
  { id: 'CLASSIFICATION', label: '2. 23-Feature & 7-Class ML', sub: 'Frozen HistGradientBoosting Classifier', icon: Activity },
  { id: 'FUSION', label: '3. Corroboration & D-S Fusion', sub: 'Multi-Source Evidential Conflict (K)', icon: Sparkles },
  { id: 'CONSEQUENCE', label: '4. Consequence & Dispersion', sub: 'Gaussian Plume & Toxic Threat Zones', icon: Flame },
  { id: 'RESPONSE', label: '5. Response & Pre-Plan Auth', sub: 'Dynamic Safe Evacuation & ERDMP PDF', icon: Navigation }
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
  const [isComputingEvac, setIsComputingEvac] = useState(false);
  const [isExportingPDF, setIsExportingPDF] = useState(false);

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
      setActionNotice(null);
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
      setTimeout(() => setActionNotice(null), 3500);
    } catch (e) {
      console.warn('Recovery error:', e);
    }
  };

  // Safe Evacuation Action (Fixed & Live Connected)
  const handleComputeEvacuation = async () => {
    if (replayState.current_step < 4) return;
    setIsComputingEvac(true);
    try {
      const plan = await api.generateEvacuationRoute('FAC-IN-DAHEJ-001', 'T-04');
      setReplayState(prev => ({
        ...prev,
        active_evacuation: plan
      }));
      const dist = plan.primary_evacuation_route?.total_distance_m?.toFixed(0) || '850';
      const gate = plan.primary_evacuation_route?.recommended_assembly_point_name || 'Staging Gate 3';
      setActionNotice({ 
        type: 'success', 
        msg: `Safe evacuation corridor computed (${dist}m to ${gate}).` 
      });
      setTimeout(() => setActionNotice(null), 5000);
    } catch (e) {
      console.error('Evacuation calculation failed:', e);
      setActionNotice({ type: 'error', msg: `Evacuation calculation failed: ${e.message || 'Check backend service'}` });
      setTimeout(() => setActionNotice(null), 4000);
    } finally {
      setIsComputingEvac(false);
    }
  };

  // Export PDF Action (Fixed & Live Connected)
  const handleExportPDF = async () => {
    if (replayState.current_step < 4) return;
    setIsExportingPDF(true);
    try {
      await api.exportPrePlanPDF('FAC-IN-DAHEJ-001', 'T-04', 'CHEM-NH3');
      setActionNotice({ type: 'success', msg: 'Official ERDMP Pre-Plan PDF exported & downloaded successfully.' });
      setTimeout(() => setActionNotice(null), 5000);
    } catch (e) {
      console.error('PDF export failed:', e);
      setActionNotice({ type: 'error', msg: `PDF generation failed: ${e.message || 'Check backend service'}` });
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

  const currentClassLabel = activeClass?.predicted_class?.replace(/_/g, ' ') || (replayState.current_step === 0 ? 'STANDBY (AWAITING EVENT)' : 'PROCESSING');
  const currentConfidence = activeClass ? Math.round((activeClass.calibrated_confidence || activeClass.confidence_score || 0.9) * 100) : null;
  const isContextAvailable = replayState.current_step >= 4 && activeConseq;

  return (
    <div className="h-screen w-screen bg-slate-100 text-slate-900 flex flex-col font-sans overflow-hidden antialiased">
      
      {/* 1. Header & Replay Control Strip */}
      <header className="bg-white border-b border-slate-200 px-4 py-2.5 flex flex-wrap items-center justify-between gap-3 shrink-0 z-30 shadow-2xs">
        
        {/* Left Brand & Mode Label */}
        <div className="flex items-center space-x-3">
          <div className="w-8 h-8 rounded-lg bg-amber-600 flex items-center justify-center text-white font-bold shadow-xs">
            <Sliders className="w-4.5 h-4.5" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <span className="font-extrabold text-sm tracking-tight text-slate-900">REACT-X</span>
              <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-amber-100 text-amber-800 border border-amber-300 uppercase tracking-wider">
                DEMO REPLAY • REFERENCE
              </span>
            </div>
            <p className="text-[11px] text-slate-500 font-mono">
              Canonical Pipeline Replay Engine (Deterministic Reference Flow)
            </p>
          </div>
        </div>

        {/* Center: Replay Controls */}
        <div className="flex items-center bg-slate-50 border border-slate-300 rounded-lg p-1 space-x-1.5 shadow-2xs">
          <select 
            value={selectedScenarioId}
            onChange={(e) => setSelectedScenarioId(e.target.value)}
            disabled={replayState.status === 'RUNNING'}
            className="text-xs bg-white text-slate-800 border border-slate-300 rounded px-2.5 py-1.5 font-semibold focus:outline-none focus:border-blue-500 cursor-pointer shadow-2xs"
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
              className="px-3 py-1.5 bg-amber-600 hover:bg-amber-700 text-white rounded text-xs font-bold flex items-center gap-1.5 transition-all shadow-2xs cursor-pointer"
            >
              <Pause className="w-3.5 h-3.5" /> Pause
            </button>
          ) : (
            <button 
              onClick={handleStart}
              className="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded text-xs font-bold flex items-center gap-1.5 transition-all shadow-2xs cursor-pointer"
            >
              <Play className="w-3.5 h-3.5" /> {replayState.current_step > 0 ? 'Resume' : 'Start Replay'}
            </button>
          )}

          <button 
            onClick={handleStep}
            disabled={replayState.status === 'RUNNING' || isProcessingStep}
            className="px-2.5 py-1.5 bg-white hover:bg-slate-100 disabled:opacity-50 text-slate-700 border border-slate-300 rounded text-xs font-semibold flex items-center gap-1 transition shadow-2xs cursor-pointer"
            title="Step Forward Single Pipeline Execution"
          >
            {isProcessingStep ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <StepForward className="w-3.5 h-3.5 text-blue-600" />}
            <span>Step ({replayState.current_step}/{replayState.total_steps})</span>
          </button>

          <button 
            onClick={handleReset}
            className="px-2.5 py-1.5 bg-white hover:bg-slate-100 text-slate-700 border border-slate-300 rounded text-xs font-semibold flex items-center gap-1 transition shadow-2xs cursor-pointer"
            title="Reset to Baseline"
          >
            <RotateCcw className="w-3.5 h-3.5 text-slate-500" /> Reset
          </button>

          {/* Speed Selector */}
          <div className="flex items-center space-x-1 pl-1 border-l border-slate-300">
            {[1.0, 2.0, 5.0].map(s => (
              <button
                key={s}
                onClick={() => setSpeed(s)}
                className={`text-[10px] px-2 py-1 rounded font-bold transition cursor-pointer ${
                  speed === s ? 'bg-blue-600 text-white shadow-2xs' : 'text-slate-600 hover:bg-slate-200'
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
            className="px-3 py-1.5 bg-blue-50 hover:bg-blue-100 text-blue-700 border border-blue-300 rounded-lg text-xs font-bold flex items-center gap-1.5 transition cursor-pointer shadow-2xs"
          >
            🇮🇳 India Operations (Live Platform)
          </button>
        </div>
      </header>

      {/* 2. Top Clocks & Telemetry Strip */}
      <div className="bg-slate-50 border-b border-slate-200 px-4 py-1.5 flex items-center justify-between text-[11px] font-mono text-slate-600 shrink-0">
        <div className="flex items-center space-x-6">
          <div className="flex items-center space-x-1.5">
            <span className="text-slate-400 font-semibold">OBSERVED TIME:</span>
            <span className="text-slate-800 font-bold">
              {replayState.latest_event_observed_at ? new Date(replayState.latest_event_observed_at).toUTCString() : '2026-08-30 14:00:00 UTC'}
            </span>
          </div>
          <div className="flex items-center space-x-1.5">
            <span className="text-slate-400 font-semibold">SOURCE PROVENANCE:</span>
            <span className="text-amber-700 font-bold">REFERENCE REPLAY • NO FALSE LIVE LABELS</span>
          </div>
          <div className="flex items-center space-x-1.5">
            <span className="text-slate-400 font-semibold">STAGE:</span>
            <span className="text-blue-700 font-bold">{replayState.pipeline_stage || (replayState.current_step === 0 ? 'WAITING FOR REPLAY' : 'STANDBY')}</span>
          </div>
        </div>

        {/* Action Notice Toast */}
        {actionNotice && (
          <div className={`px-3 py-0.5 rounded text-xs font-semibold flex items-center gap-1.5 animate-in fade-in duration-200 ${
            actionNotice.type === 'success' ? 'bg-emerald-100 text-emerald-800 border border-emerald-300' : 'bg-red-100 text-red-800 border border-red-300'
          }`}>
            {actionNotice.type === 'success' ? <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" /> : <AlertTriangle className="w-3.5 h-3.5 text-red-600" />}
            <span>{actionNotice.msg}</span>
          </div>
        )}
      </div>

      {/* 3. Main Split View: Left Controls/Pipeline + Right Map & Evidence */}
      <div className="flex-1 flex overflow-hidden w-full h-full">
        
        {/* Left Side: Pipeline Visualization & Failure Injections */}
        <div className="w-full sm:w-[440px] lg:w-[480px] bg-white border-r border-slate-200 flex flex-col overflow-y-auto shrink-0 divide-y divide-slate-200 shadow-sm">
          
          {/* A. Live 5-Stage Deterministic Pipeline Stepper */}
          <div className="p-4 space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold uppercase tracking-wider text-slate-600 flex items-center gap-1.5">
                <Activity className="w-4 h-4 text-blue-600" /> Canonical Pipeline Status
              </span>
              <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-slate-100 text-slate-700 border border-slate-200">
                Step {replayState.current_step} of {replayState.total_steps}
              </span>
            </div>

            <div className="space-y-2">
              {PIPELINE_STAGES.map((stg, idx) => {
                const isCompleted = replayState.current_step >= idx + 1;
                const isCurrent = replayState.current_step === idx && replayState.status === 'RUNNING';
                const Icon = stg.icon;

                return (
                  <div 
                    key={stg.id}
                    className={`flex items-center justify-between p-2.5 rounded-lg border text-xs font-medium transition-all ${
                      isCompleted 
                        ? 'bg-emerald-50 border-emerald-200 text-emerald-900' 
                        : isCurrent 
                        ? 'bg-blue-50 border-blue-400 text-blue-900 shadow-xs'
                        : 'bg-slate-50/70 border-slate-200 text-slate-400'
                    }`}
                  >
                    <div className="flex items-center space-x-2.5">
                      <div className={`p-1 rounded ${isCompleted ? 'bg-emerald-100 text-emerald-700' : isCurrent ? 'bg-blue-100 text-blue-700' : 'bg-slate-100 text-slate-400'}`}>
                        <Icon className="w-4 h-4" />
                      </div>
                      <div>
                        <span className="font-semibold block text-slate-800">{stg.label}</span>
                        <span className="text-[10px] text-slate-500">{stg.sub}</span>
                      </div>
                    </div>
                    <div>
                      {isCompleted ? (
                        <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-emerald-200/80 text-emerald-800 flex items-center gap-1">
                          <Check className="w-3 h-3" /> PROCESSED
                        </span>
                      ) : isCurrent ? (
                        <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-blue-200 text-blue-800 animate-pulse">
                          EXECUTING
                        </span>
                      ) : (
                        <span className="text-[10px] font-mono text-slate-400">STANDBY</span>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* B. Failure Injection Sandbox */}
          <div className="p-4 space-y-3 bg-slate-50/50">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold uppercase tracking-wider text-amber-800 flex items-center gap-1.5">
                <Bug className="w-4 h-4 text-amber-600" /> Failure Injection Sandbox
              </span>
              <button 
                onClick={handleTriggerRecovery}
                className="text-[10px] font-bold px-2.5 py-1 rounded-md bg-emerald-50 hover:bg-emerald-100 text-emerald-800 border border-emerald-300 transition flex items-center gap-1 cursor-pointer shadow-2xs"
              >
                <RefreshCw className="w-3 h-3" /> Recover Feeds
              </button>
            </div>
            <p className="text-[11px] text-slate-500">
              Inject production anomalies to verify deterministic degraded state transitions without fake recovery.
            </p>

            <div className="grid grid-cols-2 gap-2">
              <button
                onClick={() => handleToggleFailure('inject_missing_telemetry')}
                className={`p-2.5 rounded-lg border text-left text-xs font-semibold transition cursor-pointer ${
                  failureFlags.inject_missing_telemetry 
                    ? 'bg-red-50 border-red-300 text-red-900 shadow-xs' 
                    : 'bg-white border-slate-200 text-slate-700 hover:bg-slate-50'
                }`}
              >
                <div className="flex items-center justify-between">
                  <span>Missing OT Telemetry</span>
                  <span className={`w-2.5 h-2.5 rounded-full ${failureFlags.inject_missing_telemetry ? 'bg-red-600' : 'bg-slate-300'}`} />
                </div>
                <p className="text-[10px] text-slate-500 mt-1 font-mono">Prediction &rarr; STANDBY</p>
              </button>

              <button
                onClick={() => handleToggleFailure('inject_conflicting_evidence')}
                className={`p-2.5 rounded-lg border text-left text-xs font-semibold transition cursor-pointer ${
                  failureFlags.inject_conflicting_evidence 
                    ? 'bg-amber-50 border-amber-300 text-amber-900 shadow-xs' 
                    : 'bg-white border-slate-200 text-slate-700 hover:bg-slate-50'
                }`}
              >
                <div className="flex items-center justify-between">
                  <span>Conflicting Evidence</span>
                  <span className={`w-2.5 h-2.5 rounded-full ${failureFlags.inject_conflicting_evidence ? 'bg-amber-500' : 'bg-slate-300'}`} />
                </div>
                <p className="text-[10px] text-slate-500 mt-1 font-mono">Conflict K &gt; 0.60</p>
              </button>

              <button
                onClick={() => handleToggleFailure('inject_sensor_spike')}
                className={`p-2.5 rounded-lg border text-left text-xs font-semibold transition cursor-pointer ${
                  failureFlags.inject_sensor_spike 
                    ? 'bg-red-50 border-red-300 text-red-900 shadow-xs' 
                    : 'bg-white border-slate-200 text-slate-700 hover:bg-slate-50'
                }`}
              >
                <div className="flex items-center justify-between">
                  <span>Sensor Spike Anomaly</span>
                  <span className={`w-2.5 h-2.5 rounded-full ${failureFlags.inject_sensor_spike ? 'bg-red-600' : 'bg-slate-300'}`} />
                </div>
                <p className="text-[10px] text-slate-500 mt-1 font-mono">Quality &rarr; BAD / Quarantined</p>
              </button>

              <button
                onClick={() => handleToggleFailure('inject_stale_telemetry')}
                className={`p-2.5 rounded-lg border text-left text-xs font-semibold transition cursor-pointer ${
                  failureFlags.inject_stale_telemetry 
                    ? 'bg-amber-50 border-amber-300 text-amber-900 shadow-xs' 
                    : 'bg-white border-slate-200 text-slate-700 hover:bg-slate-50'
                }`}
              >
                <div className="flex items-center justify-between">
                  <span>Stale Telemetry Feed</span>
                  <span className={`w-2.5 h-2.5 rounded-full ${failureFlags.inject_stale_telemetry ? 'bg-amber-500' : 'bg-slate-300'}`} />
                </div>
                <p className="text-[10px] text-slate-500 mt-1 font-mono">Downweighted Evidence</p>
              </button>
            </div>
          </div>

          {/* C. ML Classification & Dempster-Shafer Fusion Inspection */}
          <div className="p-4 space-y-3">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-600 flex items-center gap-1.5">
              <Sparkles className="w-4 h-4 text-purple-600" /> ML Classification & D-S Evidential Fusion
            </span>

            {/* Classification Card */}
            <div className="bg-slate-50 border border-slate-200 rounded-xl p-3.5 space-y-2.5">
              <div className="flex items-center justify-between">
                <span className="text-xs text-slate-600 font-semibold">Predicted Class</span>
                <span className={`text-xs font-bold px-2.5 py-0.5 rounded-full border ${
                  currentClassLabel.includes('FIRE') 
                    ? 'bg-red-100 text-red-800 border-red-200' 
                    : currentClassLabel.includes('STANDBY')
                    ? 'bg-slate-100 text-slate-600 border-slate-200'
                    : 'bg-blue-100 text-blue-800 border-blue-200'
                }`}>
                  {currentClassLabel}
                </span>
              </div>

              <div className="flex items-center justify-between text-xs">
                <span className="text-slate-600">Calibrated Confidence</span>
                <span className="font-bold text-slate-900 font-mono">
                  {currentConfidence !== null ? `${currentConfidence}%` : '--'}
                </span>
              </div>

              <div className="flex items-center justify-between text-xs text-slate-500">
                <span>Model Contract</span>
                <span className="font-mono text-[11px] text-slate-700">Frozen 23-Feature Classifier v1.0</span>
              </div>

              {/* Dempster-Shafer Metrics */}
              {activeFusion ? (
                <div className="pt-2 border-t border-slate-200 grid grid-cols-3 gap-2 text-center">
                  <div className="bg-white p-2 rounded-lg border border-slate-200 shadow-2xs">
                    <span className="text-[10px] text-slate-500 font-semibold block">Belief Mass</span>
                    <span className="text-xs font-mono font-bold text-emerald-700">{activeFusion.belief_mass}</span>
                  </div>
                  <div className="bg-white p-2 rounded-lg border border-slate-200 shadow-2xs">
                    <span className="text-[10px] text-slate-500 font-semibold block">Uncertainty</span>
                    <span className="text-xs font-mono font-bold text-amber-700">{activeFusion.uncertainty_mass}</span>
                  </div>
                  <div className="bg-white p-2 rounded-lg border border-slate-200 shadow-2xs">
                    <span className="text-[10px] text-slate-500 font-semibold block">Conflict K</span>
                    <span className={`text-xs font-mono font-bold ${activeFusion.conflict_k > 0.5 ? 'text-red-600' : 'text-slate-800'}`}>
                      {activeFusion.conflict_k}
                    </span>
                  </div>
                </div>
              ) : (
                <div className="pt-2 border-t border-slate-200 text-center text-xs text-slate-400 font-mono py-1">
                  Dempster-Shafer fusion standby (Awaiting multi-source evidence)
                </div>
              )}
            </div>
          </div>

          {/* D. Consequence & Prediction Health Posture */}
          <div className="p-4 space-y-2.5 bg-slate-50/30">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-600 flex items-center gap-1.5">
              <Wind className="w-4 h-4 text-teal-600" /> Consequence & Predictive Telemetry
            </span>

            <div className="p-3 bg-white border border-slate-200 rounded-xl space-y-1.5 text-xs">
              <div className="flex items-center justify-between">
                <span className="text-slate-600 font-semibold">Prediction Posture</span>
                <span className={`font-bold px-2 py-0.5 rounded text-[11px] ${
                  failureFlags.inject_missing_telemetry || !activePred || activePred.prediction_state === 'PREDICTION_STANDBY'
                    ? 'bg-amber-100 text-amber-800 border border-amber-200'
                    : 'bg-emerald-100 text-emerald-800 border border-emerald-200'
                }`}>
                  {failureFlags.inject_missing_telemetry || !activePred || activePred.prediction_state === 'PREDICTION_STANDBY'
                    ? 'PREDICTION STANDBY'
                    : 'PREDICTION AVAILABLE'}
                </span>
              </div>
              <p className="text-[11px] text-slate-500">
                {failureFlags.inject_missing_telemetry
                  ? 'Awaiting verified live industrial OT hardware telemetry.'
                  : activeConseq
                  ? `Toxic dispersion evaluated (${activeConseq.summary_zones?.length || 3} threat zones active).`
                  : 'Awaiting thermal incident evolution.'}
              </p>
            </div>
          </div>

          {/* E. Action Command Buttons (Gated by Prerequisite Context) */}
          <div className="p-4 space-y-3 bg-white mt-auto">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold uppercase tracking-wider text-slate-700 flex items-center gap-1.5">
                <Navigation className="w-4 h-4 text-blue-600" /> Operational Response Actions
              </span>
              {!isContextAvailable && (
                <span className="text-[10px] font-bold text-amber-700 flex items-center gap-1">
                  <Lock className="w-3 h-3" /> Gated (Step 4+ required)
                </span>
              )}
            </div>

            <div className="grid grid-cols-1 gap-2.5">
              {/* Compute Safe Evacuation Button */}
              <button
                onClick={handleComputeEvacuation}
                disabled={!isContextAvailable || isComputingEvac}
                className={`w-full py-2.5 px-3.5 rounded-lg text-xs font-bold flex items-center justify-center gap-2 transition shadow-xs ${
                  isContextAvailable 
                    ? 'bg-blue-600 hover:bg-blue-700 text-white cursor-pointer' 
                    : 'bg-slate-100 text-slate-400 border border-slate-200 cursor-not-allowed opacity-60'
                }`}
                title={!isContextAvailable ? 'Available after incident consequence analysis (Step 4 & 5)' : 'Compute dynamic safe evacuation route'}
              >
                {isComputingEvac ? (
                  <RefreshCw className="w-4 h-4 animate-spin text-white" />
                ) : (
                  <Navigation className="w-4 h-4 text-white" />
                )}
                <span>{isComputingEvac ? 'Computing Evacuation Corridor...' : 'Compute Dynamic Safe Evacuation'}</span>
              </button>

              {/* Export Official ERDMP Pre-Plan PDF Button */}
              <button
                onClick={handleExportPDF}
                disabled={!isContextAvailable || isExportingPDF}
                className={`w-full py-2.5 px-3.5 rounded-lg text-xs font-bold flex items-center justify-center gap-2 transition shadow-xs ${
                  isContextAvailable 
                    ? 'bg-white hover:bg-slate-50 text-slate-900 border border-slate-300 cursor-pointer' 
                    : 'bg-slate-100 text-slate-400 border border-slate-200 cursor-not-allowed opacity-60'
                }`}
                title={!isContextAvailable ? 'Available after incident consequence analysis (Step 4 & 5)' : 'Export official ERDMP Pre-Plan PDF'}
              >
                {isExportingPDF ? (
                  <RefreshCw className="w-4 h-4 animate-spin text-amber-600" />
                ) : (
                  <FileText className="w-4 h-4 text-amber-600" />
                )}
                <span>{isExportingPDF ? 'Generating Pre-Plan PDF...' : 'Export Official ERDMP Pre-Plan PDF'}</span>
              </button>
            </div>

            {!isContextAvailable && (
              <p className="text-[11px] text-slate-400 text-center italic">
                Available after incident consequence analysis (Advance replay to Step 4 or 5).
              </p>
            )}
          </div>

        </div>

        {/* Right Side: Map Canvas & GIS Spatial Context */}
        <div className="flex-1 h-full relative bg-slate-100">
          <CommandMapWorkspace
            center={[21.6850, 72.5750]}
            zoom={14}
            facilities={[{
              id: 'FAC-IN-DAHEJ-001',
              name: 'Dahej Petrochemical Complex (Demo Reference)',
              location: 'Dahej PCPIR, Gujarat',
              coordinates: [21.6850, 72.5750],
              current_status: replayState.current_step >= 3 ? 'ELEVATED_ALERT' : 'NOMINAL_OPERATIONS'
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
