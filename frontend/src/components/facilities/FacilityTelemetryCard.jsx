import React, { useState, useEffect } from 'react';
import { 
  Activity, Radio, Gauge, Flame, Wind, Droplets, 
  TrendingUp, TrendingDown, Minus, RefreshCw, AlertCircle, 
  CheckCircle2, Clock, ShieldCheck, Zap
} from 'lucide-react';
import { api } from '../../services/api';

export default function FacilityTelemetryCard({ facilityId = 'FAC-IN-DAHEJ-001' }) {
  const [telemetry, setTelemetry] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState(null);
  const [scenario, setScenario] = useState('NORMAL');
  const [lastUpdated, setLastUpdated] = useState(null);

  const fetchTelemetry = async (showLoading = false) => {
    if (showLoading) setLoading(true);
    setError(null);
    try {
      const data = await api.getFacilityLatestTelemetry(facilityId);
      setTelemetry(data || []);
      setLastUpdated(new Date());
    } catch (err) {
      console.error('Error fetching facility telemetry:', err);
      setError(err.message || 'Telemetry connection offline');
    } finally {
      if (showLoading) setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchTelemetry(true);
    const interval = setInterval(() => {
      fetchTelemetry(false);
    }, 3000);
    return () => clearInterval(interval);
  }, [facilityId]);

  const handleScenarioChange = async (e) => {
    const newScn = e.target.value;
    setScenario(newScn);
    setRefreshing(true);
    try {
      await api.setSimulatorScenario(newScn);
      await api.triggerSimulatorTick();
      await fetchTelemetry(false);
    } catch (err) {
      console.error('Failed to change scenario:', err);
    } finally {
      setRefreshing(false);
    }
  };

  const getFreshnessBadge = (status) => {
    switch (status) {
      case 'LIVE':
        return { bg: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30', label: 'LIVE', dot: 'bg-emerald-400 animate-pulse' };
      case 'FRESH':
        return { bg: 'bg-cyan-500/10 text-cyan-400 border-cyan-500/30', label: 'FRESH', dot: 'bg-cyan-400' };
      case 'STALE':
        return { bg: 'bg-amber-500/10 text-amber-400 border-amber-500/30', label: 'STALE', dot: 'bg-amber-400' };
      case 'DEGRADED':
        return { bg: 'bg-orange-500/10 text-orange-400 border-orange-500/30', label: 'DEGRADED', dot: 'bg-orange-400' };
      default:
        return { bg: 'bg-rose-500/10 text-rose-400 border-rose-500/30', label: 'UNAVAILABLE', dot: 'bg-rose-400' };
    }
  };

  const getTrendIcon = (trend) => {
    if (trend === 'RISING' || trend === 'RAPID_RISE') {
      return <TrendingUp className="w-3.5 h-3.5 text-rose-400 inline ml-1" />;
    }
    if (trend === 'FALLING' || trend === 'RAPID_FALL') {
      return <TrendingDown className="w-3.5 h-3.5 text-blue-400 inline ml-1" />;
    }
    return <Minus className="w-3.5 h-3.5 text-slate-500 inline ml-1" />;
  };

  const getSensorIcon = (type) => {
    switch (type) {
      case 'TEMPERATURE':
        return <Flame className="w-4 h-4 text-amber-400" />;
      case 'PRESSURE':
        return <Gauge className="w-4 h-4 text-cyan-400" />;
      case 'GAS_CONCENTRATION':
        return <Wind className="w-4 h-4 text-purple-400" />;
      case 'FLOW':
        return <Droplets className="w-4 h-4 text-blue-400" />;
      case 'THERMAL_CAMERA_SUMMARY':
        return <Radio className="w-4 h-4 text-rose-400" />;
      default:
        return <Activity className="w-4 h-4 text-slate-400" />;
    }
  };

  // Filter or group key telemetry modalities
  const displaySensors = telemetry.slice(0, 6);

  return (
    <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-4 shadow-xl backdrop-blur-md">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-slate-800/80 pb-3 mb-3">
        <div className="flex items-center space-x-2">
          <div className="p-1.5 bg-cyan-500/10 border border-cyan-500/30 rounded-lg text-cyan-400">
            <Radio className="w-4 h-4 animate-pulse" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-200">FACILITY TELEMETRY</h3>
              <span className="px-1.5 py-0.5 rounded text-[10px] font-extrabold bg-amber-500/10 text-amber-400 border border-amber-500/30 tracking-wider">
                SIMULATION
              </span>
            </div>
            <p className="text-[11px] text-slate-400">High-Frequency Process & Safety Ingestion Layer</p>
          </div>
        </div>

        {/* Controls */}
        <div className="flex items-center space-x-2">
          <select
            value={scenario}
            onChange={handleScenarioChange}
            className="bg-slate-950 border border-slate-700 text-[11px] text-slate-300 rounded px-2 py-1 focus:outline-none focus:border-cyan-500"
          >
            <option value="NORMAL">Normal Baseline</option>
            <option value="DRIFT">Thermal Drift</option>
            <option value="THERMAL_RISE">Acute Thermal Rise</option>
            <option value="PRESSURE_RISE">Boil-Off Overpressure</option>
            <option value="GAS_LEAK_PATTERN">Flange Gas Leak</option>
            <option value="MULTI_SENSOR_DEVIATION">Multi-Sensor Cascade</option>
            <option value="SENSOR_FAILURE">Sensor Fault</option>
            <option value="COMMUNICATION_LOSS">Gateway Comm Loss</option>
          </select>

          <button
            onClick={() => { setRefreshing(true); fetchTelemetry(false); }}
            disabled={refreshing}
            className="p-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded transition disabled:opacity-50"
            title="Poll Latest Telemetry"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${refreshing ? 'animate-spin text-cyan-400' : ''}`} />
          </button>
        </div>
      </div>

      {/* Loading & Error States */}
      {loading ? (
        <div className="py-6 flex items-center justify-center space-x-2 text-xs text-slate-400">
          <RefreshCw className="w-4 h-4 animate-spin text-cyan-400" />
          <span>Ingesting gateway streams...</span>
        </div>
      ) : error ? (
        <div className="py-4 px-3 bg-rose-500/10 border border-rose-500/20 rounded-lg text-xs text-rose-400 flex items-center space-x-2">
          <AlertCircle className="w-4 h-4 flex-shrink-0" />
          <span>{error}</span>
        </div>
      ) : displaySensors.length === 0 ? (
        <div className="py-4 text-center text-xs text-slate-500">
          No live sensor streams reporting for {facilityId}.
        </div>
      ) : (
        /* Sensor Grid */
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-2.5">
          {displaySensors.map((s) => {
            const fresh = getFreshnessBadge(s.freshness_status || 'LIVE');
            const isAbnormal = s.quality === 'WARNING' || s.quality === 'BAD';

            return (
              <div
                key={s.sensor_id}
                className={`p-2.5 rounded-lg border transition-all ${
                  isAbnormal
                    ? 'bg-rose-950/20 border-rose-500/40 ring-1 ring-rose-500/20'
                    : 'bg-slate-950/60 border-slate-800/80 hover:border-slate-700'
                }`}
              >
                <div className="flex items-center justify-between mb-1.5">
                  <div className="flex items-center space-x-1.5">
                    {getSensorIcon(s.sensor_type)}
                    <span className="text-[11px] font-bold text-slate-300 truncate max-w-[90px]">
                      {s.asset_id} • {s.sensor_type.replace('_', ' ').slice(0, 8)}
                    </span>
                  </div>
                  <span className={`px-1.5 py-0.5 rounded text-[9px] font-bold border flex items-center space-x-1 ${fresh.bg}`}>
                    <span className={`w-1.5 h-1.5 rounded-full ${fresh.dot}`} />
                    <span>{fresh.label}</span>
                  </span>
                </div>

                <div className="flex items-baseline justify-between mt-1">
                  <div className="text-base font-extrabold font-mono text-slate-100">
                    {s.value >= 0 ? `+${s.value.toFixed(1)}` : s.value.toFixed(1)}
                    <span className="text-xs font-normal text-slate-400 ml-1 font-sans">{s.unit}</span>
                  </div>
                  <div className="text-[11px] font-medium text-slate-400 flex items-center">
                    {getTrendIcon(s.trend)}
                  </div>
                </div>

                <div className="flex items-center justify-between text-[10px] text-slate-500 mt-1 pt-1 border-t border-slate-800/50">
                  <span className="truncate">{s.tag_name.split('.').pop()}</span>
                  <span>{s.source_protocol === 'SIMULATED_GATEWAY' ? 'SIM' : s.source_protocol}</span>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Footer Info */}
      <div className="mt-3 pt-2 border-t border-slate-800/60 flex items-center justify-between text-[10px] text-slate-500">
        <div className="flex items-center space-x-1.5 text-slate-400">
          <ShieldCheck className="w-3 h-3 text-emerald-400" />
          <span>Read-Only Boundary Enforced (Zero Actuation)</span>
        </div>
        <div>
          {lastUpdated && (
            <span>Updated: {lastUpdated.toLocaleTimeString()}</span>
          )}
        </div>
      </div>
    </div>
  );
}
