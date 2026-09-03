import React, { useState, useEffect } from 'react';
import { api } from '../../services/api';
import { 
  Activity, ShieldAlert, Cpu, CheckCircle2, AlertTriangle, Flame, 
  ArrowRight, RefreshCw, Zap, Sliders, Layers, Radio, Play, 
  ChevronRight, ChevronLeft, ChevronDown, ChevronUp, Eye, Thermometer, Droplets, Wind,
  CheckSquare, FileCheck, ExternalLink, Sparkles, Compass, ShieldCheck
} from 'lucide-react';

export default function PreIncidentSafetyCenter({ onNavigateToSimulator, onNavigateToEvacuation }) {
  const [activeSubView, setActiveSubView] = useState('early_warnings'); // early_warnings, preventive_whatif, risk_graph, storyline_19, live_telemetry
  
  // 1. Streaming & Pipeline Telemetry State
  const [metrics, setMetrics] = useState({
    events_per_second: 30878.3,
    active_streams_count: 100,
    p95_ingest_latency_ms: 4.52,
    p99_ingest_latency_ms: 4.52,
    quality_good_pct: 99.4,
    quality_bad_pct: 0.4,
    quality_stale_pct: 0.2
  });
  const [recentEvents, setRecentEvents] = useState([]);
  const [streamCount, setStreamCount] = useState(100);
  const [isInjecting, setIsInjecting] = useState(false);
  const [injectionSuccess, setInjectionSuccess] = useState(null);

  // 2. Early Warning State Roster & Expanded Details Map
  const [assetRoster, setAssetRoster] = useState([]);
  const [selectedAsset, setSelectedAsset] = useState('T-04');
  const [loadingAssets, setLoadingAssets] = useState(false);
  const [expandedAssets, setExpandedAssets] = useState({ 'T-04': true });

  // 3. Preventive What-If State
  const [preventiveActions, setPreventiveActions] = useState([]);
  const [selectedActionIds, setSelectedActionIds] = useState(['ACT-T04-ISO', 'ACT-T04-CURTAIN']);
  const [whatIfOutcome, setWhatIfOutcome] = useState(null);
  const [simulatingWhatIf, setSimulatingWhatIf] = useState(false);

  // Control Authorization Modal State
  const [showAuthModal, setShowAuthModal] = useState(false);
  const [selectedControlAction, setSelectedControlAction] = useState(null);
  const [checklist, setChecklist] = useState({
    downwind_verified: true,
    flare_header_clear: true,
    ert_stationed: true
  });
  const [authResult, setAuthResult] = useState(null);

  // 4. Risk Graph & Environmental State
  const [cascadeData, setCascadeData] = useState(null);
  const [environmentalData, setEnvironmentalData] = useState([]);

  // 5. 19-Stage Storyline State
  const [stageRoster, setStageRoster] = useState([]);
  const [currentStageNum, setCurrentStageNum] = useState(5);
  const [currentStageData, setCurrentStageData] = useState(null);

  // Initial Data Fetching
  useEffect(() => {
    fetchLiveMetrics();
    fetchAssetEarlyWarnings();
    fetchPreventiveInterventions('T-04');
    fetchCascadeAndEnv('T-04');
    fetch19StageRoster();
    fetchStageData(5);

    const interval = setInterval(() => {
      fetchLiveMetrics();
      fetchStreamTick();
    }, 5000);
    return () => clearInterval(interval);
  }, []);

  const fetchLiveMetrics = async () => {
    try {
      const data = await api.getStreamingMetrics();
      setMetrics(data);
    } catch (err) {
      console.warn('Metrics polling error:', err);
    }
  };

  const fetchStreamTick = async () => {
    try {
      const data = await api.getStreamTick(12);
      setRecentEvents(data);
    } catch (err) {
      console.warn('Tick polling error:', err);
    }
  };

  const fetchAssetEarlyWarnings = async () => {
    try {
      setLoadingAssets(true);
      const data = await api.getAllAssetsEarlyWarning();
      setAssetRoster(data);
    } catch (err) {
      console.warn('Early warning fetch error:', err);
    } finally {
      setLoadingAssets(false);
    }
  };

  const fetchPreventiveInterventions = async (assetId) => {
    try {
      const data = await api.getPreventiveInterventions(assetId);
      setPreventiveActions(data);
      if (data.length >= 2) {
        setSelectedActionIds([data[0].action_id, data[1].action_id]);
      }
    } catch (err) {
      console.warn('Interventions error:', err);
    }
  };

  const fetchCascadeAndEnv = async (assetId) => {
    try {
      const [casc, env] = await Promise.all([
        api.getCascadePathways(assetId),
        api.getEnvironmentalReceptors(assetId, 195.0)
      ]);
      setCascadeData(casc);
      setEnvironmentalData(env);
    } catch (err) {
      console.warn('Risk graph error:', err);
    }
  };

  const fetch19StageRoster = async () => {
    try {
      const data = await api.get19StageRoster();
      setStageRoster(data);
    } catch (err) {
      console.warn('Stage roster error:', err);
    }
  };

  const fetchStageData = async (stageNum) => {
    try {
      const data = await api.execute19Stage(stageNum);
      setCurrentStageData(data);
    } catch (err) {
      console.warn('Stage data error:', err);
    }
  };

  const handleSetStreamCount = async (count) => {
    try {
      setStreamCount(count);
      await api.setStreamConfig(count);
      fetchLiveMetrics();
    } catch (err) {
      console.error('Failed to configure streams:', err);
    }
  };

  const handleInjectAnomaly = async () => {
    try {
      setIsInjecting(true);
      await api.injectStreamAnomaly('T-04', 'PRESS_01', 6.8, 'CRITICAL');
      setInjectionSuccess('Pressure & vibration excursion (6.8 bar) injected into T-04 Ammonia Header.');
      setTimeout(() => setInjectionSuccess(null), 6000);
      fetchAssetEarlyWarnings();
      fetchLiveMetrics();
    } catch (err) {
      console.error('Failed to inject anomaly:', err);
    } finally {
      setIsInjecting(false);
    }
  };

  const handleClearAnomalies = async () => {
    try {
      await api.clearStreamAnomalies();
      setInjectionSuccess('All anomalies cleared. Baseline reset.');
      setTimeout(() => setInjectionSuccess(null), 3000);
      fetchAssetEarlyWarnings();
      fetchLiveMetrics();
    } catch (err) {
      console.error('Failed to clear anomalies:', err);
    }
  };

  const handleRunPreventiveWhatIf = async () => {
    try {
      setSimulatingWhatIf(true);
      const res = await api.simulatePreventiveWhatIf({
        asset_id: selectedAsset,
        chemical_id: selectedAsset === 'T-03' ? 'CHEM-LPG' : 'CHEM-NH3',
        base_risk_score: selectedAsset === 'T-04' ? 82.0 : 68.0,
        selected_action_ids: selectedActionIds
      });
      setWhatIfOutcome(res);
    } catch (err) {
      console.error('Preventive What-If failed:', err);
    } finally {
      setSimulatingWhatIf(false);
    }
  };

  const handleToggleActionSelection = (actionId) => {
    setSelectedActionIds(prev => 
      prev.includes(actionId) ? prev.filter(id => id !== actionId) : [...prev, actionId]
    );
  };

  const handleAuthorizeControl = async () => {
    if (!selectedControlAction) return;
    try {
      const res = await api.authorizeControlAction({
        action_id: selectedControlAction.action_id,
        approver_name: 'Lead HSE Controller (Er. S. Nair)',
        approver_role: 'HSE_COMMANDER',
        checklist_confirmations: Object.keys(checklist).filter(k => checklist[k])
      });
      setAuthResult(res);
    } catch (err) {
      console.error('Failed to authorize control action:', err);
    }
  };

  const toggleExpandAsset = (assetId) => {
    setExpandedAssets(prev => ({ ...prev, [assetId]: !prev[assetId] }));
  };

  // Compute Summary Statistics
  const warningCount = assetRoster.filter(a => a.state === 'WATCH' || a.state === 'PREVENTIVE' || a.state === 'CRITICAL').length;
  const criticalCount = assetRoster.filter(a => a.state === 'CRITICAL').length;
  const highestRiskAsset = assetRoster.length ? assetRoster[0] : null;

  return (
    <div className="space-y-3 font-mono text-slate-100 text-xs">
      
      {/* 1. TOP SUMMARY BAR: "Is the plant becoming unsafe?" */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
        
        {/* System Ingestion Health */}
        <div className="bg-slate-900/80 px-3 py-2 rounded-lg border border-slate-800 flex items-center justify-between">
          <div>
            <div className="text-[9px] text-slate-400 uppercase tracking-wider">System Ingestion</div>
            <div className="text-xs font-bold text-emerald-400">OPERATIONAL</div>
            <div className="text-[9px] text-slate-500 font-normal">{metrics.events_per_second.toLocaleString()} eps • {metrics.p95_ingest_latency_ms}ms</div>
          </div>
          <div className="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-pulse" />
        </div>

        {/* Early Warnings Count */}
        <div className={`px-3 py-2 rounded-lg border flex items-center justify-between ${
          warningCount > 0 ? 'bg-amber-950/30 border-amber-500/40 text-amber-300' : 'bg-slate-900/80 border-slate-800 text-slate-300'
        }`}>
          <div>
            <div className="text-[9px] text-slate-400 uppercase tracking-wider">Early Warnings</div>
            <div className="text-sm font-black">{warningCount} Warning{warningCount !== 1 ? 's' : ''}</div>
            <div className="text-[9px] text-slate-500 font-normal">Across {assetRoster.length} Monitored Units</div>
          </div>
          <Activity className={`w-4 h-4 ${warningCount > 0 ? 'text-amber-400' : 'text-slate-500'}`} />
        </div>

        {/* Critical Assets */}
        <div className={`px-3 py-2 rounded-lg border flex items-center justify-between ${
          criticalCount > 0 ? 'bg-red-950/30 border-red-500/50 text-red-300' : 'bg-slate-900/80 border-slate-800 text-slate-300'
        }`}>
          <div>
            <div className="text-[9px] text-slate-400 uppercase tracking-wider">Critical Units</div>
            <div className="text-sm font-black">{criticalCount > 0 ? `${criticalCount} Unit (${highestRiskAsset?.asset_id || 'T-04'})` : '0 Units (Safe)'}</div>
            <div className="text-[9px] text-slate-500 font-normal">Immediate Action Required</div>
          </div>
          <ShieldAlert className={`w-4 h-4 ${criticalCount > 0 ? 'text-red-400 animate-pulse' : 'text-slate-500'}`} />
        </div>

        {/* Overall Plant Risk */}
        <div className="bg-slate-900/80 px-3 py-2 rounded-lg border border-slate-800 flex items-center justify-between">
          <div>
            <div className="text-[9px] text-slate-400 uppercase tracking-wider">Overall Plant Risk</div>
            <div className={`text-sm font-black ${highestRiskAsset?.early_warning_score > 70 ? 'text-red-400' : (highestRiskAsset?.early_warning_score > 40 ? 'text-amber-400' : 'text-emerald-400')}`}>
              {highestRiskAsset?.early_warning_score || 65.6} <span className="text-[10px] text-slate-500">/ 100</span>
            </div>
            <div className="text-[9px] text-slate-500 font-normal">{highestRiskAsset?.state || 'NORMAL'}</div>
          </div>
          <Zap className="w-4 h-4 text-cyan-400" />
        </div>

      </div>

      {/* 2. RECOMMENDED PREVENTIVE ACTION BANNER */}
      {highestRiskAsset && highestRiskAsset.state !== 'NORMAL' && (
        <div className="bg-gradient-to-r from-slate-900 via-slate-900/90 to-slate-950 border border-cyan-500/40 rounded-xl p-3.5 shadow-lg flex flex-wrap items-center justify-between gap-3">
          <div className="space-y-1 max-w-2xl">
            <div className="flex items-center space-x-2">
              <span className="px-2 py-0.2 rounded text-[9px] font-bold bg-red-500/20 text-red-300 border border-red-500/40">
                RECOMMENDED PREVENTIVE ACTION
              </span>
              <span className="text-[11px] font-bold text-white">Target Asset: {highestRiskAsset.asset_id} ({highestRiskAsset.asset_name})</span>
            </div>
            <p className="text-[11px] text-slate-300 leading-relaxed font-sans">
              <b>What is happening:</b> {highestRiskAsset.asset_id} shows progressive multi-signal excursion (Top Driver: <b>{highestRiskAsset.top_driver}</b>).<br/>
              <b>Recommended Action:</b> Actuate ROSOV isolation valves and initiate water fog deluge curtain before containment loss.
            </p>
          </div>

          <div className="flex items-center space-x-2">
            <button
              type="button"
              onClick={() => {
                setSelectedAsset(highestRiskAsset.asset_id);
                fetchPreventiveInterventions(highestRiskAsset.asset_id);
                setActiveSubView('preventive_whatif');
              }}
              className="px-4 py-2 bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white rounded-lg font-bold text-xs shadow-md shadow-cyan-500/20 transition-all flex items-center space-x-1.5"
            >
              <Sparkles className="w-3.5 h-3.5" />
              <span>SIMULATE PREVENTIVE WHAT-IF →</span>
            </button>
          </div>
        </div>
      )}

      {/* 3. STREAM CONTROLS & ANOMALY INJECTION STRIP */}
      <div className="bg-slate-950/70 border border-slate-800 rounded-lg p-2 flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center space-x-2">
          <span className="text-[10px] text-slate-400 font-bold uppercase">Stream Multiplexer:</span>
          <div className="flex items-center bg-slate-900 rounded p-0.5 border border-slate-800">
            {[100, 500, 1000].map(cnt => (
              <button
                key={cnt}
                type="button"
                onClick={() => handleSetStreamCount(cnt)}
                className={`px-2 py-0.5 rounded text-[10px] font-bold transition-all ${
                  streamCount === cnt
                    ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                {cnt} Streams
              </button>
            ))}
          </div>
        </div>

        <div className="flex items-center space-x-2">
          <button
            type="button"
            onClick={handleInjectAnomaly}
            disabled={isInjecting}
            className="flex items-center space-x-1 px-2.5 py-1 bg-red-950/50 hover:bg-red-900/70 border border-red-500/40 text-red-200 rounded text-[10px] font-bold transition-all"
          >
            <Zap className="w-3 h-3 text-red-400" />
            <span>Inject T-04 Excursion</span>
          </button>

          <button
            type="button"
            onClick={handleClearAnomalies}
            className="flex items-center space-x-1 px-2 py-1 bg-slate-900 hover:bg-slate-800 border border-slate-700 text-slate-300 rounded text-[10px] font-bold transition-all"
          >
            <RefreshCw className="w-3 h-3 text-slate-400" />
            <span>Reset Baseline</span>
          </button>
        </div>
      </div>

      {/* 4. SUB-NAVIGATION TABS */}
      <div className="flex border-b border-slate-800 bg-slate-950/80 rounded-xl p-1 gap-1 overflow-x-auto shadow-sm">
        {[
          { id: 'early_warnings', label: '1. Early Warnings & Asset Health', icon: Activity, badge: warningCount },
          { id: 'preventive_whatif', label: '2. Preventive What-If Recalculator', icon: Sliders, badge: 'PREDICT → VERIFY' },
          { id: 'risk_graph', label: '3. Risk Graph & Domino Cascades', icon: Layers },
          { id: 'storyline_19', label: '4. 19-Stage Storyline Journey', icon: Sparkles, badge: `Stage ${currentStageNum}/19` },
          { id: 'live_telemetry', label: '5. Live Telemetry Stream', icon: Radio }
        ].map(tab => {
          const Icon = tab.icon;
          const isActive = activeSubView === tab.id;
          return (
            <button
              key={tab.id}
              type="button"
              onClick={() => setActiveSubView(tab.id)}
              className={`flex items-center space-x-2 px-3 py-1.5 rounded-lg text-xs font-bold transition-all whitespace-nowrap ${
                isActive
                  ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/50 shadow-sm shadow-cyan-500/10'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900/60'
              }`}
            >
              <Icon className={`w-3.5 h-3.5 ${isActive ? 'text-cyan-400' : 'text-slate-500'}`} />
              <span>{tab.label}</span>
              {tab.badge && (
                <span className={`text-[9px] px-1.5 py-0.2 rounded font-bold border ${
                  tab.badge === 'PREDICT → VERIFY'
                    ? 'bg-indigo-500/20 text-indigo-300 border-indigo-500/30'
                    : 'bg-red-500/20 text-red-300 border-red-500/40'
                }`}>
                  {tab.badge}
                </span>
              )}
            </button>
          );
        })}
      </div>

      {/* ======================================================================= */}
      {/* SUB-VIEW 1: EARLY WARNING ROSTER WITH PROGRESSIVE DISCLOSURE           */}
      {/* ======================================================================= */}
      {activeSubView === 'early_warnings' && (
        <div className="space-y-2.5">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-2.5">
            {assetRoster.map(asset => {
              const isCrit = asset.state === 'CRITICAL';
              const isPrev = asset.state === 'PREVENTIVE';
              const isWatch = asset.state === 'WATCH';
              const isExpanded = !!expandedAssets[asset.asset_id];

              const badgeColor = isCrit
                ? 'bg-red-500/20 text-red-300 border-red-500/50'
                : (isPrev ? 'bg-amber-500/20 text-amber-300 border-amber-500/50' : (isWatch ? 'bg-yellow-500/20 text-yellow-300 border-yellow-500/40' : 'bg-emerald-500/10 text-emerald-300 border-emerald-500/30'));

              return (
                <div
                  key={asset.asset_id}
                  className={`bg-slate-950/80 border rounded-xl p-3 space-y-2.5 shadow-sm transition-all ${
                    isCrit ? 'border-red-500/60 bg-red-950/10' : (isPrev ? 'border-amber-500/50' : 'border-slate-800')
                  }`}
                >
                  {/* Card Header: Level 1 Info */}
                  <div className="flex items-start justify-between">
                    <div>
                      <div className="flex items-center space-x-1.5">
                        <span className="text-cyan-400 font-bold">{asset.asset_id}</span>
                        <span className={`px-1.5 py-0.2 rounded text-[9px] font-bold border ${badgeColor}`}>
                          {asset.state}
                        </span>
                      </div>
                      <h4 className="font-bold text-slate-100 text-xs mt-0.5">{asset.asset_name}</h4>
                      <span className="text-[10px] text-slate-400">{asset.chemical_name}</span>
                    </div>

                    <div className="text-right">
                      <div className={`text-lg font-black ${isCrit ? 'text-red-400' : (isPrev ? 'text-amber-400' : 'text-slate-200')}`}>
                        {asset.early_warning_score}
                      </div>
                      <div className="text-[9px] text-slate-500">Risk Score</div>
                    </div>
                  </div>

                  {/* Top Driver Summary */}
                  <div className="bg-slate-900/80 rounded-lg p-2 border border-slate-800/80 flex items-center justify-between text-[10px]">
                    <span className="text-slate-400">Top Driver:</span>
                    <span className="text-cyan-300 font-bold truncate max-w-[170px]">{asset.top_driver}</span>
                  </div>

                  {/* Progressive Disclosure: Sensor Evidence Grid */}
                  {isExpanded && (
                    <div className="bg-slate-900/60 rounded-lg p-2.5 border border-slate-800 space-y-2 text-[10px] animate-fade-in">
                      <div className="text-[9px] text-slate-400 font-bold uppercase tracking-wider border-b border-slate-800 pb-1">
                        Sensor Evidence & ML Signals
                      </div>
                      
                      <div className="space-y-1.5">
                        {asset.drivers_breakdown?.map((d, idx) => (
                          <div key={idx} className="space-y-0.5">
                            <div className="flex justify-between text-slate-300">
                              <span className="truncate">{d.driver}</span>
                              <span className="font-bold text-cyan-300">+{d.score} pts</span>
                            </div>
                            <div className="w-full h-1 bg-slate-800 rounded-full overflow-hidden">
                              <div
                                className={`h-full rounded-full ${d.score > 15 ? 'bg-red-400' : (d.score > 8 ? 'bg-amber-400' : 'bg-cyan-400')}`}
                                style={{ width: `${Math.min(100, (d.score / 25) * 100)}%` }}
                              />
                            </div>
                          </div>
                        ))}
                      </div>

                      <div className="pt-1 text-[9px] text-slate-400 flex justify-between border-t border-slate-800/60">
                        <span>ML Isolation Forest: <b>{asset.confidence_pct}% Confidence</b></span>
                      </div>
                    </div>
                  )}

                  {/* Actions & Expansion Toggle */}
                  <div className="flex items-center justify-between pt-1 border-t border-slate-800/60 gap-2">
                    <button
                      type="button"
                      onClick={() => toggleExpandAsset(asset.asset_id)}
                      className="text-[10px] text-slate-400 hover:text-cyan-300 flex items-center space-x-1"
                    >
                      <span>{isExpanded ? 'Hide Details' : 'View Sensor Evidence'}</span>
                      {isExpanded ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
                    </button>

                    <button
                      type="button"
                      onClick={() => {
                        setSelectedAsset(asset.asset_id);
                        fetchPreventiveInterventions(asset.asset_id);
                        fetchCascadeAndEnv(asset.asset_id);
                        setActiveSubView('preventive_whatif');
                      }}
                      className="px-2.5 py-1 bg-cyan-950/60 hover:bg-cyan-900/80 border border-cyan-500/40 text-cyan-300 rounded text-[10px] font-bold transition-all"
                    >
                      PREVENTIVE WHAT-IF →
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* ======================================================================= */}
      {/* SUB-VIEW 2: PREVENTIVE WHAT-IF RECALCULATOR                            */}
      {/* ======================================================================= */}
      {activeSubView === 'preventive_whatif' && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-3 items-start">
          
          {/* Left: Ranked Engineering Preventive Interventions */}
          <div className="lg:col-span-6 bg-slate-950/80 border border-slate-800 rounded-xl p-3.5 space-y-3 shadow-sm">
            <div className="flex items-center justify-between border-b border-slate-800 pb-2">
              <div>
                <h3 className="font-bold text-slate-100 text-xs flex items-center space-x-1.5">
                  <Sliders className="w-3.5 h-3.5 text-cyan-400" />
                  <span>PREVENTIVE INTERVENTIONS FOR {selectedAsset}</span>
                </h3>
                <span className="text-[10px] text-slate-400">Select proposed mitigations to simulate risk reduction</span>
              </div>
              <button
                type="button"
                onClick={handleRunPreventiveWhatIf}
                disabled={simulatingWhatIf || selectedActionIds.length === 0}
                className="px-3 py-1.5 bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 disabled:opacity-50 text-white rounded-lg font-bold text-xs shadow-md shadow-cyan-500/20 transition-all flex items-center space-x-1.5"
              >
                <Sparkles className="w-3.5 h-3.5" />
                <span>{simulatingWhatIf ? 'RECALCULATING...' : 'SIMULATE WHAT-IF'}</span>
              </button>
            </div>

            <div className="space-y-2">
              {preventiveActions.map(act => {
                const isSelected = selectedActionIds.includes(act.action_id);
                return (
                  <div
                    key={act.action_id}
                    onClick={() => handleToggleActionSelection(act.action_id)}
                    className={`border rounded-lg p-2.5 cursor-pointer transition-all space-y-1.5 ${
                      isSelected
                        ? 'border-cyan-500/60 bg-cyan-950/20'
                        : 'border-slate-800 bg-slate-900/40 hover:border-slate-700'
                    }`}
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex items-start space-x-2">
                        <div className={`mt-0.5 w-3.5 h-3.5 rounded border flex items-center justify-center ${
                          isSelected ? 'bg-cyan-500 border-cyan-400 text-slate-950' : 'border-slate-600'
                        }`}>
                          {isSelected && <CheckCircle2 className="w-3 h-3" />}
                        </div>
                        <div>
                          <span className="text-[9px] text-cyan-400 font-bold uppercase">{act.action_type}</span>
                          <h5 className="font-bold text-slate-200 text-xs">{act.title}</h5>
                        </div>
                      </div>
                      <div className="text-right">
                        <span className="px-1.5 py-0.2 rounded text-[9px] font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-500/40">
                          -{act.expected_risk_reduction_pts} pts ΔR
                        </span>
                      </div>
                    </div>

                    <p className="text-[10px] text-slate-300 pl-5 leading-relaxed font-sans">{act.description}</p>

                    <div className="pl-5 flex items-center justify-between text-[9px] text-slate-400 pt-1 border-t border-slate-800/50">
                      <span>Est Time: {act.estimated_execution_time_min} min</span>
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          setSelectedControlAction(act);
                          setShowAuthModal(true);
                        }}
                        className="px-2 py-0.5 bg-slate-800 hover:bg-slate-700 text-cyan-300 rounded font-bold text-[9px] border border-cyan-500/30"
                      >
                        AUTHORIZE COMMAND
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Right: Before vs After Mitigated Risk Comparison */}
          <div className="lg:col-span-6 space-y-2.5">
            {whatIfOutcome ? (
              <div className="bg-slate-950/80 border border-slate-800 rounded-xl p-3.5 space-y-3 shadow-sm">
                <div className="border-b border-slate-800 pb-1.5">
                  <span className="text-[9px] text-emerald-400 font-bold uppercase tracking-wider">VERIFIED PREVENTIVE OUTCOME</span>
                  <h4 className="font-bold text-slate-100 text-xs">PREDICT → INTERVENE → VERIFY RESULT</h4>
                </div>

                {/* Side-by-Side Risk Dials */}
                <div className="grid grid-cols-2 gap-2.5">
                  <div className="bg-red-950/20 border border-red-500/40 rounded-lg p-3 text-center space-y-1">
                    <span className="text-[9px] text-red-300 font-bold uppercase">BASE UNMITIGATED</span>
                    <div className="text-2xl font-black text-red-400">{whatIfOutcome.base_state.risk_score}</div>
                    <span className="px-1.5 py-0.2 rounded text-[9px] font-bold bg-red-500/20 text-red-200">
                      {whatIfOutcome.base_state.risk_category}
                    </span>
                    <div className="text-[9px] text-slate-400 pt-0.5">Threat Reach: {whatIfOutcome.base_state.max_plume_reach_m}m</div>
                  </div>

                  <div className="bg-emerald-950/20 border border-emerald-500/40 rounded-lg p-3 text-center space-y-1">
                    <span className="text-[9px] text-emerald-300 font-bold uppercase">AFTER MITIGATION</span>
                    <div className="text-2xl font-black text-emerald-400">{whatIfOutcome.mitigated_state.risk_score}</div>
                    <span className="px-1.5 py-0.2 rounded text-[9px] font-bold bg-emerald-500/20 text-emerald-200">
                      {whatIfOutcome.mitigated_state.risk_category}
                    </span>
                    <div className="text-[9px] text-slate-400 pt-0.5">Threat Reach: {whatIfOutcome.mitigated_state.max_plume_reach_m}m</div>
                  </div>
                </div>

                {/* Quantified Deltas Matrix */}
                <div className="grid grid-cols-3 gap-2">
                  <div className="bg-slate-900/60 p-2 rounded border border-slate-800 text-center">
                    <div className="text-xs font-bold text-cyan-300">-{whatIfOutcome.deltas.risk_reduction_pct}%</div>
                    <span className="text-[8px] text-slate-400 uppercase">Risk Drop</span>
                  </div>
                  <div className="bg-slate-900/60 p-2 rounded border border-slate-800 text-center">
                    <div className="text-xs font-bold text-emerald-300">+{whatIfOutcome.deltas.workers_saved}</div>
                    <span className="text-[8px] text-slate-400 uppercase">Workers Saved</span>
                  </div>
                  <div className="bg-slate-900/60 p-2 rounded border border-slate-800 text-center">
                    <div className="text-xs font-bold text-indigo-300">+{whatIfOutcome.deltas.cascade_assets_protected}</div>
                    <span className="text-[8px] text-slate-400 uppercase">Domino Units Saved</span>
                  </div>
                </div>

                <div className="bg-slate-900/80 rounded-lg p-2.5 border border-slate-800 space-y-1">
                  <span className="text-[9px] text-slate-400 font-bold uppercase tracking-wider">Engineering Assessment:</span>
                  <p className="text-[11px] text-slate-200 leading-relaxed font-sans">{whatIfOutcome.safety_summary}</p>
                </div>
              </div>
            ) : (
              <div className="bg-slate-950/60 border border-slate-800 rounded-xl p-6 text-center space-y-2">
                <Sliders className="w-6 h-6 text-slate-600 mx-auto" />
                <h4 className="font-bold text-slate-300 text-xs">Ready to Simulate Interventions</h4>
                <p className="text-[11px] text-slate-400 max-w-xs mx-auto font-sans">
                  Select preventive engineering actions from the left and click <b>SIMULATE WHAT-IF</b> to compute risk reduction.
                </p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* ======================================================================= */}
      {/* SUB-VIEW 3: RISK GRAPH & DOMINO CASCADES                                */}
      {/* ======================================================================= */}
      {activeSubView === 'risk_graph' && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-3 items-start">
          <div className="lg:col-span-6 bg-slate-950/80 border border-slate-800 rounded-xl p-3.5 space-y-2.5 shadow-sm">
            <div className="border-b border-slate-800 pb-1.5">
              <span className="text-[9px] text-cyan-400 font-bold uppercase tracking-wider">PROCESS CASCADE GRAPH</span>
              <h3 className="font-bold text-slate-100 text-xs">DOMINO PROPAGATION FOR {selectedAsset}</h3>
            </div>

            <div className="space-y-1.5">
              {cascadeData?.threatened_nodes?.map((node, i) => (
                <div key={i} className="bg-slate-900/60 border border-slate-800 rounded-lg p-2 flex items-center justify-between text-[11px]">
                  <div>
                    <div className="flex items-center space-x-2">
                      <span className="font-bold text-slate-200">{node.name}</span>
                      <span className="text-[9px] px-1 py-0.2 bg-slate-800 text-slate-400 rounded">{node.relation}</span>
                    </div>
                    <span className="text-[9px] text-slate-400">Distance: {node.distance_m}m • Criticality: {node.criticality}</span>
                  </div>
                  <div className="text-right">
                    <span className="font-bold text-amber-400 text-xs">{node.cascade_probability_pct}%</span>
                    <div className="text-[8px] text-slate-500">Cascade Risk</div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="lg:col-span-6 bg-slate-950/80 border border-slate-800 rounded-xl p-3.5 space-y-2.5 shadow-sm">
            <div className="border-b border-slate-800 pb-1.5">
              <span className="text-[9px] text-emerald-400 font-bold uppercase tracking-wider">CONSEQUENCE RECEPTORS</span>
              <h3 className="font-bold text-slate-100 text-xs">WATER BODIES & NEARBY SETTLEMENTS</h3>
            </div>

            <div className="space-y-1.5">
              {environmentalData.map((rec, i) => (
                <div key={i} className="bg-slate-900/60 border border-slate-800 rounded-lg p-2 space-y-0.5 text-[11px]">
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-slate-200">{rec.name}</span>
                    <span className={`text-[8px] px-1.5 py-0.2 rounded font-bold ${
                      rec.is_downwind ? 'bg-red-500/20 text-red-300 border border-red-500/40' : 'bg-slate-800 text-slate-400'
                    }`}>
                      {rec.is_downwind ? 'DOWNWIND' : 'CROSSWIND'}
                    </span>
                  </div>
                  <div className="flex items-center justify-between text-[9px] text-slate-400">
                    <span>Distance: {rec.distance_m}m</span>
                    <span>Sensitivity: {rec.sensitivity}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* ======================================================================= */}
      {/* SUB-VIEW 4: 19-STAGE STORYLINE JOURNEY                                  */}
      {/* ======================================================================= */}
      {activeSubView === 'storyline_19' && (
        <div className="bg-slate-950/80 border border-slate-800 rounded-xl p-3.5 space-y-3 shadow-sm">
          <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-800 pb-2">
            <div>
              <div className="flex items-center space-x-2">
                <span className="text-[9px] text-cyan-400 font-bold uppercase tracking-wider">DEMONSTRATION JOURNEY</span>
                <span className="px-1.5 py-0.2 bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 rounded text-[9px] font-bold">
                  PHASE: {currentStageData?.phase || 'PREDICT'}
                </span>
              </div>
              <h3 className="font-bold text-slate-100 text-sm mt-0.5">
                Stage {currentStageNum} of 19: {currentStageData?.stage_name}
              </h3>
            </div>

            <div className="flex items-center space-x-2">
              <button
                type="button"
                onClick={() => {
                  if (currentStageNum > 1) {
                    const prev = currentStageNum - 1;
                    setCurrentStageNum(prev);
                    fetchStageData(prev);
                  }
                }}
                disabled={currentStageNum <= 1}
                className="px-2.5 py-1 bg-slate-900 hover:bg-slate-800 disabled:opacity-40 text-slate-300 rounded text-xs font-bold border border-slate-700 flex items-center space-x-1"
              >
                <ChevronLeft className="w-3.5 h-3.5" />
                <span>Prev</span>
              </button>
              <button
                type="button"
                onClick={() => {
                  if (currentStageNum < 19) {
                    const next = currentStageNum + 1;
                    setCurrentStageNum(next);
                    fetchStageData(next);
                  }
                }}
                disabled={currentStageNum >= 19}
                className="px-3 py-1 bg-cyan-600 hover:bg-cyan-500 disabled:opacity-40 text-white rounded text-xs font-bold shadow flex items-center space-x-1"
              >
                <span>Next Stage</span>
                <ChevronRight className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>

          {/* Stepper Dots */}
          <div className="flex items-center gap-1 overflow-x-auto py-1">
            {stageRoster.map(stg => (
              <button
                key={stg.stage}
                type="button"
                onClick={() => {
                  setCurrentStageNum(stg.stage);
                  fetchStageData(stg.stage);
                }}
                className={`px-2 py-0.5 rounded text-[9px] font-bold whitespace-nowrap transition-all ${
                  currentStageNum === stg.stage
                    ? 'bg-cyan-500 text-slate-950 font-black'
                    : 'bg-slate-900 text-slate-400 hover:bg-slate-800'
                }`}
              >
                {stg.stage}. {stg.name.slice(0, 12)}...
              </button>
            ))}
          </div>

          {currentStageData && (
            <div className="bg-slate-900/80 border border-slate-800 rounded-lg p-3 space-y-2">
              <p className="text-xs text-slate-200 leading-relaxed font-sans">{currentStageData.description}</p>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-2 pt-2 border-t border-slate-800">
                <div className="bg-slate-950 p-2 rounded border border-slate-800">
                  <span className="text-[8px] text-slate-400 uppercase">State Category</span>
                  <div className="text-xs font-bold text-cyan-300">{currentStageData.incident_packet.risk_category}</div>
                </div>
                <div className="bg-slate-950 p-2 rounded border border-slate-800">
                  <span className="text-[8px] text-slate-400 uppercase">Risk Score</span>
                  <div className="text-xs font-bold text-emerald-400">{currentStageData.incident_packet.risk_score} / 100</div>
                </div>
                <div className="bg-slate-950 p-2 rounded border border-slate-800">
                  <span className="text-[8px] text-slate-400 uppercase">Confidence</span>
                  <div className="text-xs font-bold text-slate-200">{Math.round(currentStageData.incident_packet.confidence * 100)}%</div>
                </div>
                <div className="bg-slate-950 p-2 rounded border border-slate-800">
                  <span className="text-[8px] text-slate-400 uppercase">Hazard Type</span>
                  <div className="text-xs font-bold text-amber-300">{currentStageData.incident_packet.hazard_type}</div>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* ======================================================================= */}
      {/* SUB-VIEW 5: LIVE TELEMETRY STREAM                                      */}
      {/* ======================================================================= */}
      {activeSubView === 'live_telemetry' && (
        <div className="bg-slate-950/80 border border-slate-800 rounded-xl p-3.5 space-y-2.5 shadow-sm">
          <div className="flex items-center justify-between border-b border-slate-800 pb-1.5">
            <div>
              <span className="text-[9px] text-cyan-400 font-bold uppercase tracking-wider">CANONICAL TELEMETRY STREAM</span>
              <h3 className="font-bold text-slate-100 text-xs">NORMALIZED PROTOCOL INGESTION TICKER</h3>
            </div>
            <span className="text-[9px] text-emerald-400 font-bold animate-pulse">● POLLING LIVE</span>
          </div>

          <div className="space-y-1 max-h-[380px] overflow-y-auto">
            {recentEvents.map((ev, i) => (
              <div
                key={i}
                className="bg-slate-900/60 border border-slate-800/80 rounded p-1.5 flex items-center justify-between text-[10px]"
              >
                <div className="flex items-center space-x-2">
                  <span className="text-cyan-400 font-bold">{ev.asset_id}</span>
                  <span className="text-slate-300">{ev.signal_id}</span>
                  <span className="text-slate-500">[{ev.source}]</span>
                </div>
                <div className="flex items-center space-x-3">
                  <span className="font-bold text-slate-100">{ev.value} {ev.unit}</span>
                  <span className={`px-1 py-0.2 rounded font-bold text-[8px] ${
                    ev.quality === 'GOOD' ? 'bg-emerald-500/20 text-emerald-300' : 'bg-red-500/20 text-red-300'
                  }`}>
                    {ev.quality}
                  </span>
                  <span className={`px-1 py-0.2 rounded font-bold text-[8px] ${
                    ev.classification === 'HOT' ? 'bg-red-500/20 text-red-300' : 'bg-slate-800 text-slate-400'
                  }`}>
                    {ev.classification}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* HUMAN REVIEW & CONTROL ACTION AUTHORIZATION MODAL */}
      {showAuthModal && selectedControlAction && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-950 border border-slate-700 rounded-xl max-w-lg w-full p-5 space-y-3.5 shadow-2xl animate-fade-in">
            <div className="flex items-center justify-between border-b border-slate-800 pb-2">
              <div>
                <span className="text-[9px] text-cyan-400 font-bold uppercase tracking-wider">SAFETY-CONTROL BOUNDARY</span>
                <h3 className="font-bold text-slate-100 text-xs">AUTHORIZE DCS CONTROL COMMAND</h3>
              </div>
              <button
                type="button"
                onClick={() => {
                  setShowAuthModal(false);
                  setAuthResult(null);
                }}
                className="text-slate-400 hover:text-white font-bold"
              >
                ✕
              </button>
            </div>

            <div className="bg-slate-900/90 rounded-lg p-2.5 border border-slate-800 space-y-0.5">
              <span className="text-[9px] text-cyan-300 font-bold">{selectedControlAction.action_type}</span>
              <h4 className="font-bold text-slate-200 text-xs">{selectedControlAction.title}</h4>
              <p className="text-[10px] text-slate-400 font-sans">{selectedControlAction.description}</p>
            </div>

            <div className="space-y-1.5">
              <span className="text-[9px] text-slate-400 font-bold uppercase tracking-wider">Engineering Checklist:</span>
              {[
                { key: 'downwind_verified', label: 'Downwind sniffer concentrations verified within boundary limits' },
                { key: 'flare_header_clear', label: 'Flare header depressurization routing confirmed clear' },
                { key: 'ert_stationed', label: 'Field Hazmat squad stationed at designated upwind post' }
              ].map(item => (
                <label key={item.key} className="flex items-center space-x-2 text-[11px] text-slate-300 cursor-pointer font-sans">
                  <input
                    type="checkbox"
                    checked={checklist[item.key]}
                    onChange={(e) => setChecklist(prev => ({ ...prev, [item.key]: e.target.checked }))}
                    className="rounded border-slate-700 text-cyan-500 focus:ring-0"
                  />
                  <span>{item.label}</span>
                </label>
              ))}
            </div>

            {authResult && (
              <div className="bg-emerald-950/80 border border-emerald-500 p-2.5 rounded text-xs text-emerald-200 space-y-0.5">
                <div className="font-bold">✓ CONTROL ACTION AUTHORIZED</div>
                <div className="text-[10px]">Token: {authResult.authorization_token}</div>
                <div className="text-[10px]">Forwarded to Plant DCS Console by {authResult.approver_name}</div>
              </div>
            )}

            <div className="flex items-center justify-end space-x-2 pt-2 border-t border-slate-800">
              <button
                type="button"
                onClick={() => setShowAuthModal(false)}
                className="px-3 py-1 bg-slate-900 hover:bg-slate-800 text-slate-300 rounded text-xs font-bold"
              >
                CANCEL
              </button>
              <button
                type="button"
                onClick={handleAuthorizeControl}
                disabled={authResult !== null}
                className="px-3.5 py-1 bg-cyan-600 hover:bg-cyan-500 disabled:opacity-50 text-white rounded text-xs font-bold shadow"
              >
                SIGN & AUTHORIZE DCS COMMAND
              </button>
            </div>
          </div>
        </div>
      )}

    </div>
  );
}
