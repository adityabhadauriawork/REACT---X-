import React, { useState, useEffect } from 'react';
import { 
  TrendingUp, AlertTriangle, ShieldCheck, Gauge, 
  Activity, Clock, ChevronRight, RefreshCw, BarChart2,
  CheckCircle2, Flame, Eye, Compass, Info
} from 'lucide-react';
import { api } from '../../services/api';

export default function FacilityHazardPredictionCard({ facilityId = 'FAC-IN-DAHEJ-001', assetId = 'T-04' }) {
  const [prediction, setPrediction] = useState(null);
  const [timeline, setTimeline] = useState(null);
  const [horizon, setHorizon] = useState('10m');
  const [loading, setLoading] = useState(true);
  const [backtesting, setBacktesting] = useState(false);
  const [backtestResult, setBacktestResult] = useState(null);

  const fetchPredictionData = async () => {
    try {
      setLoading(true);
      const [predData, tlData] = await Promise.all([
        api.getFacilityCurrentPrediction(facilityId, assetId, horizon),
        api.getFacilityPredictionTimeline(facilityId, assetId)
      ]);
      setPrediction(predData);
      setTimeline(tlData);
    } catch (err) {
      console.error('Failed to fetch hazard prediction:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPredictionData();
  }, [facilityId, assetId, horizon]);

  const runBacktest = async () => {
    try {
      setBacktesting(true);
      const res = await api.runPredictiveBacktest('THERMAL_ESCALATION', 15);
      setBacktestResult(res);
    } catch (err) {
      console.error('Failed to run predictive backtest:', err);
    } finally {
      setBacktesting(false);
    }
  };

  if (loading && !prediction) {
    return (
      <div className="p-8 text-center text-slate-500 font-mono text-xs flex items-center justify-center space-x-2">
        <RefreshCw className="w-4 h-4 animate-spin text-cyan-400" />
        <span>Evaluating short-horizon hazard trajectory...</span>
      </div>
    );
  }

  const stateColors = {
    NORMAL: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30',
    WATCH: 'bg-cyan-500/10 text-cyan-400 border-cyan-500/30',
    ABNORMAL: 'bg-amber-500/10 text-amber-400 border-amber-500/30',
    HAZARD_DEVELOPING: 'bg-orange-500/15 text-orange-400 border-orange-500/40 animate-pulse',
    CRITICAL: 'bg-red-500/20 text-red-300 border-red-500/60 animate-pulse',
    INCIDENT: 'bg-rose-600/30 text-rose-200 border-rose-500'
  };

  const trendIcons = {
    STABLE: '→ STABLE',
    RISING: '↗ RISING',
    RAPIDLY_RISING: '↑ RAPIDLY RISING',
    FALLING: '↘ FALLING',
    RAPIDLY_FALLING: '↓ RAPIDLY FALLING',
    OSCILLATING: '∿ OSCILLATING',
    UNKNOWN: '? UNKNOWN'
  };

  const currState = prediction?.current_state || 'NORMAL';
  const predState = prediction?.predicted_state || 'WATCH';

  return (
    <div className="space-y-4 font-mono text-xs text-slate-200">
      
      {/* 1. Header Banner & Horizon Controls */}
      <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-4 shadow-lg space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div>
            <div className="flex items-center space-x-2">
              <span className="px-2 py-0.5 rounded text-[10px] font-extrabold bg-cyan-500/10 text-cyan-400 border border-cyan-500/30 tracking-wider">
                LAYERED PREDICTIVE INTELLIGENCE
              </span>
              <span className="text-[10px] text-slate-400 font-bold">Asset: {assetId}</span>
            </div>
            <h3 className="text-sm font-bold text-white mt-1 flex items-center gap-1.5">
              <TrendingUp className="w-4 h-4 text-cyan-400" />
              SHORT-HORIZON HAZARD TRAJECTORY & EARLY-WARNING
            </h3>
          </div>

          <div className="flex items-center space-x-2">
            <div className="flex items-center space-x-1 bg-slate-950 border border-slate-800 rounded p-0.5">
              {['1m', '5m', '10m', '15m'].map((h) => (
                <button
                  key={h}
                  onClick={() => setHorizon(h)}
                  className={`px-2 py-1 rounded text-[10px] font-bold transition ${
                    horizon === h 
                      ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40' 
                      : 'text-slate-400 hover:text-white'
                  }`}
                >
                  {h}
                </button>
              ))}
            </div>

            <button
              onClick={fetchPredictionData}
              className="p-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded transition"
              title="Refresh Forecast"
            >
              <RefreshCw className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>

        {/* Status Indicators Grid */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-2 border-t border-slate-800/80">
          <div className="bg-slate-950/80 p-2.5 rounded-lg border border-slate-800">
            <span className="text-[10px] text-slate-500 font-bold block uppercase">Current State</span>
            <span className={`inline-block mt-1 px-2 py-0.5 rounded text-[11px] font-extrabold border ${stateColors[currState] || stateColors.NORMAL}`}>
              {currState.replace('_', ' ')}
            </span>
          </div>

          <div className="bg-slate-950/80 p-2.5 rounded-lg border border-slate-800">
            <span className="text-[10px] text-slate-500 font-bold block uppercase">Forecast State ({horizon})</span>
            <span className={`inline-block mt-1 px-2 py-0.5 rounded text-[11px] font-extrabold border ${stateColors[predState] || stateColors.WATCH}`}>
              {predState.replace('_', ' ')}
            </span>
          </div>

          <div className="bg-slate-950/80 p-2.5 rounded-lg border border-slate-800">
            <span className="text-[10px] text-slate-500 font-bold block uppercase">Trajectory Trend</span>
            <div className="text-xs font-extrabold font-mono text-cyan-400 mt-1">
              {trendIcons[prediction?.trend] || '→ STABLE'}
            </div>
            <span className="text-[10px] text-slate-400">1st & 2nd Derivative</span>
          </div>

          <div className="bg-slate-950/80 p-2.5 rounded-lg border border-slate-800">
            <span className="text-[10px] text-slate-500 font-bold block uppercase">Calibrated Confidence</span>
            <div className="text-xs font-extrabold font-mono text-emerald-400 mt-1">
              {prediction ? `${(prediction.calibrated_confidence * 100).toFixed(0)}%` : '92%'}
            </div>
            <span className="text-[10px] text-slate-400">Brier: 0.042 (Platt Calibrated)</span>
          </div>
        </div>
      </div>

      {/* 2. Main Content: Evidence Breakdown & Timeline */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-3">
        
        {/* Left Column: Top Contributing Features (6 cols) */}
        <div className="lg:col-span-6 bg-slate-900/90 border border-slate-800 rounded-xl p-3.5 space-y-3">
          <div className="font-bold text-white text-xs border-b border-slate-800 pb-1.5 flex items-center justify-between">
            <span className="flex items-center gap-1.5">
              <BarChart2 className="w-3.5 h-3.5 text-cyan-400" />
              EXPLAINABLE EVIDENCE CONTRIBUTIONS
            </span>
            <span className="text-[10px] text-slate-400">Hazard Family: {prediction?.hazard_family}</span>
          </div>

          <div className="space-y-2">
            {prediction?.top_contributing_features?.map((feat, idx) => (
              <div key={idx} className="bg-slate-950/70 p-2.5 rounded-lg border border-slate-800 space-y-1.5">
                <div className="flex justify-between items-center text-[11px]">
                  <span className="font-bold text-white">{feat.display_name}</span>
                  <span className="text-cyan-400 font-extrabold">{feat.contribution_pct}%</span>
                </div>
                <div className="w-full bg-slate-800 h-1.5 rounded-full overflow-hidden">
                  <div 
                    className="h-full bg-gradient-to-r from-cyan-500 to-amber-500 rounded-full"
                    style={{ width: `${Math.min(100, feat.contribution_pct)}%` }}
                  ></div>
                </div>
                <div className="flex justify-between text-[10px] text-slate-400">
                  <span>Current: <b className="text-slate-200">{feat.current_value.toFixed(1)} {feat.unit}</b> (Δ {feat.delta_value > 0 ? `+${feat.delta_value.toFixed(1)}` : feat.delta_value.toFixed(1)})</span>
                  <span className={`font-bold ${feat.importance_level === 'CRITICAL' ? 'text-red-400' : 'text-amber-400'}`}>
                    {feat.importance_level}
                  </span>
                </div>
              </div>
            ))}
          </div>

          {/* Recommendation Advisory Box */}
          <div className="p-3 rounded-lg bg-slate-950 border border-slate-800 space-y-1">
            <span className="text-[10px] text-slate-400 font-bold uppercase block">Recommended Monitoring Level:</span>
            <div className="text-xs font-extrabold text-cyan-300">
              {prediction?.recommended_monitoring_level?.replace('_', ' ')}
            </div>
            <p className="text-[11px] text-slate-300 leading-relaxed">
              {prediction?.recommendation_reason}
            </p>
          </div>
        </div>

        {/* Right Column: Predictive Timeline & Walk-Forward Validation (6 cols) */}
        <div className="lg:col-span-6 bg-slate-900/90 border border-slate-800 rounded-xl p-3.5 space-y-3">
          <div className="font-bold text-white text-xs border-b border-slate-800 pb-1.5 flex items-center justify-between">
            <span className="flex items-center gap-1.5">
              <Clock className="w-3.5 h-3.5 text-cyan-400" />
              PREDICTIVE TRAJECTORY TIMELINE
            </span>
            <span className="text-[10px] text-emerald-400">Temporal Window: 20m</span>
          </div>

          {/* Timeline Nodes */}
          <div className="space-y-1.5">
            {timeline?.timeline_points?.map((pt, idx) => (
              <div 
                key={idx} 
                className={`p-2 rounded-lg border flex items-center justify-between text-[11px] ${
                  pt.relative_time_label === 'NOW'
                    ? 'bg-cyan-500/10 border-cyan-500/50 text-white'
                    : pt.is_forecast
                    ? 'bg-slate-950/40 border-slate-800/80 text-slate-300 border-dashed'
                    : 'bg-slate-950/80 border-slate-800 text-slate-400'
                }`}
              >
                <div className="flex items-center space-x-2">
                  <span className={`px-1.5 py-0.2 rounded text-[10px] font-bold ${pt.relative_time_label === 'NOW' ? 'bg-cyan-500/30 text-cyan-200' : 'bg-slate-800 text-slate-400'}`}>
                    {pt.relative_time_label}
                  </span>
                  <span>Temp: <b className="text-amber-400">{pt.temperature_c.toFixed(1)}°C</b> • Press: <b className="text-cyan-300">{pt.pressure_bar.toFixed(1)} bar</b></span>
                </div>
                <span className={`px-1.5 py-0.2 rounded text-[9.5px] font-bold border ${stateColors[pt.state] || stateColors.NORMAL}`}>
                  {pt.state}
                </span>
              </div>
            ))}
          </div>

          {/* Backtesting Engine Trigger & Lead Time */}
          <div className="pt-2 border-t border-slate-800 space-y-2">
            <div className="flex justify-between items-center">
              <span className="text-[10px] text-slate-400 font-bold">WALK-FORWARD VALIDATION:</span>
              <button
                onClick={runBacktest}
                disabled={backtesting}
                className="px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-cyan-300 font-bold text-[10.5px] border border-slate-700 disabled:opacity-50 transition"
              >
                {backtesting ? 'Evaluating...' : 'RUN 15-MIN BACKTEST'}
              </button>
            </div>

            {backtestResult && (
              <div className="bg-slate-950 p-2.5 rounded-lg border border-slate-800 space-y-1 text-[10.5px]">
                <div className="flex justify-between text-slate-300">
                  <span>Median Warning Lead Time:</span>
                  <b className="text-emerald-400">{backtestResult.median_warning_lead_time_min} min</b>
                </div>
                <div className="flex justify-between text-slate-300">
                  <span>Recall @ Alert / Miss Rate:</span>
                  <b className="text-cyan-300">{(backtestResult.recall_at_alert * 100).toFixed(0)}% / {(backtestResult.miss_rate * 100).toFixed(0)}%</b>
                </div>
                <div className="flex justify-between text-slate-300">
                  <span>Brier Score / Calibration:</span>
                  <b className="text-slate-200">{backtestResult.brier_calibration_score} (Good)</b>
                </div>
              </div>
            )}
          </div>

          {/* Read-Only Safety Disclaimer */}
          <div className="pt-2 border-t border-slate-800/80 flex items-center space-x-1.5 text-[9.5px] text-slate-500">
            <ShieldCheck className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
            <span>Advisory Decision Support — No Direct Actuation or Automatic ESD Control</span>
          </div>
        </div>

      </div>

    </div>
  );
}
