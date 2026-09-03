import React, { useState, useEffect } from 'react';
import { Activity, AlertTriangle, ShieldCheck, Flame, Eye, Compass, Moon, Sun, Info, RefreshCw, BarChart2 } from 'lucide-react';
import { api } from '../../services/api';

export default function FacilityThermalHealthCard({ facilityId, onSelectSource }) {
  const [healthData, setHealthData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [showEvidence, setShowEvidence] = useState(false);

  const fetchThermalHealth = async () => {
    if (!facilityId) return;
    setLoading(true);
    setError(null);
    try {
      const data = await api.getFacilityThermalHealth(facilityId);
      setHealthData(data);
    } catch (err) {
      console.error('Error fetching facility thermal health:', err);
      setError(err.message || 'Failed to load thermal health profile');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchThermalHealth();
  }, [facilityId]);

  if (loading) {
    return (
      <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-5 flex items-center justify-center space-x-3 text-slate-400">
        <RefreshCw className="w-5 h-5 animate-spin text-cyan-400" />
        <span className="text-sm font-medium">Computing Facility Thermal Fingerprint & Abnormality...</span>
      </div>
    );
  }

  if (error || !healthData) {
    return (
      <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-4 text-xs text-slate-400">
        <div className="flex items-center space-x-2 text-amber-400 font-semibold mb-1">
          <Info className="w-4 h-4" />
          <span>Thermal Health Profile Unavailable</span>
        </div>
        <p>No historical thermal fingerprint established for facility {facilityId}.</p>
      </div>
    );
  }

  const getStatusBadge = (status) => {
    switch (status) {
      case 'ABNORMAL_THERMAL_BEHAVIOUR':
        return {
          bg: 'bg-rose-500/10 text-rose-400 border-rose-500/30',
          dot: 'bg-rose-500 animate-ping',
          label: 'ABNORMAL THERMAL BEHAVIOUR',
          icon: AlertTriangle
        };
      case 'WATCH':
        return {
          bg: 'bg-amber-500/10 text-amber-400 border-amber-500/30',
          dot: 'bg-amber-400',
          label: 'WATCH (ELEVATED)',
          icon: Eye
        };
      case 'EXPECTED_PERSISTENT':
        return {
          bg: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30',
          dot: 'bg-emerald-400',
          label: 'EXPECTED PERSISTENT BASELINE',
          icon: ShieldCheck
        };
      case 'INSUFFICIENT_HISTORY':
        return {
          bg: 'bg-slate-500/10 text-slate-400 border-slate-500/30',
          dot: 'bg-slate-400',
          label: 'INSUFFICIENT HISTORY',
          icon: Info
        };
      default:
        return {
          bg: 'bg-cyan-500/10 text-cyan-400 border-cyan-500/30',
          dot: 'bg-cyan-400',
          label: 'NORMAL BASELINE',
          icon: Activity
        };
    }
  };

  const badge = getStatusBadge(healthData.thermal_health_status);
  const BadgeIcon = badge.icon;

  return (
    <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-5 shadow-xl space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-slate-800 pb-3">
        <div className="flex items-center space-x-3">
          <div className="p-2 bg-cyan-950/60 border border-cyan-500/30 rounded-lg text-cyan-400">
            <Activity className="w-5 h-5" />
          </div>
          <div>
            <h4 className="text-sm font-semibold text-slate-100 uppercase tracking-wide">
              Facility Thermal Health & Fingerprint
            </h4>
            <p className="text-xs text-slate-400">
              {healthData.facility_name} ({healthData.state})
            </p>
          </div>
        </div>

        {/* Status Badge */}
        <div className={`flex items-center space-x-2 px-3 py-1.5 rounded-full border text-xs font-bold tracking-wider ${badge.bg}`}>
          <span className={`w-2 h-2 rounded-full ${badge.dot}`}></span>
          <BadgeIcon className="w-3.5 h-3.5" />
          <span>{badge.label}</span>
        </div>
      </div>

      {/* Main KPI Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {/* Current vs Historical FRP */}
        <div className="bg-slate-950/60 border border-slate-800 rounded-lg p-3">
          <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block">Current FRP</span>
          <div className="flex items-baseline space-x-1.5 mt-1">
            <span className="text-xl font-bold text-slate-100">{healthData.current_frp_mw.toFixed(1)}</span>
            <span className="text-xs text-slate-400">MW</span>
          </div>
          <div className="mt-1 text-[10px] text-slate-400">
            Median: <span className="text-slate-300 font-semibold">{healthData.historical_median_frp_mw.toFixed(1)} MW</span>
          </div>
        </div>

        {/* FRP Deviation Ratio */}
        <div className="bg-slate-950/60 border border-slate-800 rounded-lg p-3">
          <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block">FRP Deviation</span>
          <div className="flex items-baseline space-x-1.5 mt-1">
            <span className={`text-xl font-bold ${healthData.frp_deviation_ratio >= 2.0 ? 'text-rose-400' : healthData.frp_deviation_ratio >= 1.4 ? 'text-amber-400' : 'text-emerald-400'}`}>
              {healthData.frp_deviation_ratio.toFixed(2)}x
            </span>
            <span className="text-[10px] text-slate-400">of Median</span>
          </div>
          <div className="mt-1 text-[10px] text-slate-400">
            IQR: <span className="text-slate-300 font-semibold">±{healthData.historical_iqr_frp_mw.toFixed(1)} MW</span>
          </div>
        </div>

        {/* Abnormality Score */}
        <div className="bg-slate-950/60 border border-slate-800 rounded-lg p-3">
          <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block">Abnormality Score</span>
          <div className="flex items-baseline space-x-1.5 mt-1">
            <span className={`text-xl font-bold ${healthData.overall_abnormality_score >= 65 ? 'text-rose-400' : healthData.overall_abnormality_score >= 35 ? 'text-amber-400' : 'text-cyan-400'}`}>
              {healthData.overall_abnormality_score.toFixed(1)}
            </span>
            <span className="text-xs text-slate-400">/ 100</span>
          </div>
          <div className="mt-1 text-[10px] text-slate-400">
            Trend: <span className="text-slate-300 font-medium">{healthData.recent_trend}</span>
          </div>
        </div>

        {/* Evidence Confidence */}
        <div className="bg-slate-950/60 border border-slate-800 rounded-lg p-3">
          <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block">Assessment Confidence</span>
          <div className="flex items-baseline space-x-1.5 mt-1">
            <span className="text-xl font-bold text-emerald-400">{(healthData.confidence * 100).toFixed(0)}%</span>
            <span className="text-[10px] text-slate-400">Statistical</span>
          </div>
          <div className="mt-1 text-[10px] text-slate-400 truncate">
            Tier: <span className="text-slate-300 font-semibold">{healthData.data_sufficiency.replace('_', ' ')}</span>
          </div>
        </div>
      </div>

      {/* Behavioral Diagnostics Bar */}
      <div className="bg-slate-950/40 border border-slate-800/80 rounded-lg p-3 grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs">
        <div className="flex items-center space-x-2">
          <Compass className="w-4 h-4 text-cyan-400 flex-shrink-0" />
          <div>
            <span className="text-slate-400 text-[10px] block">Spatial Stability</span>
            <span className="font-semibold text-slate-200">{(healthData.spatial_stability_score * 100).toFixed(0)}% (Fixed)</span>
          </div>
        </div>

        <div className="flex items-center space-x-2">
          {healthData.night_fraction > 0.5 ? (
            <Moon className="w-4 h-4 text-indigo-400 flex-shrink-0" />
          ) : (
            <Sun className="w-4 h-4 text-amber-400 flex-shrink-0" />
          )}
          <div>
            <span className="text-slate-400 text-[10px] block">Diurnal Balance</span>
            <span className="font-semibold text-slate-200">{(healthData.night_fraction * 100).toFixed(0)}% Night / {((1 - healthData.night_fraction) * 100).toFixed(0)}% Day</span>
          </div>
        </div>

        <div className="flex items-center space-x-2">
          <BarChart2 className="w-4 h-4 text-purple-400 flex-shrink-0" />
          <div>
            <span className="text-slate-400 text-[10px] block">Active Recurrence</span>
            <span className="font-semibold text-slate-200">{(healthData.recurrence_rate * 100).toFixed(0)}% ({healthData.active_days_total} Days)</span>
          </div>
        </div>

        <div className="flex items-center space-x-2">
          <Flame className="w-4 h-4 text-rose-400 flex-shrink-0" />
          <div>
            <span className="text-slate-400 text-[10px] block">Baseline Range</span>
            <span className="font-semibold text-slate-200">{healthData.historical_range_mw[0].toFixed(1)} - {healthData.historical_range_mw[1].toFixed(1)} MW</span>
          </div>
        </div>
      </div>

      {/* Toggle View Evidence */}
      <div className="border-t border-slate-800 pt-3">
        <div className="flex items-center justify-between">
          <span className="text-xs text-slate-400 font-medium">Statistical Evidence & Reasons</span>
          <button
            onClick={() => setShowEvidence(!showEvidence)}
            className="text-xs font-semibold text-cyan-400 hover:text-cyan-300 flex items-center space-x-1.5 transition-colors"
          >
            <span>{showEvidence ? 'Hide Evidence' : 'View Full Evidence'}</span>
            <Info className="w-3.5 h-3.5" />
          </button>
        </div>

        {showEvidence && (
          <div className="mt-3 bg-slate-950/80 border border-slate-800 rounded-lg p-3 space-y-2 text-xs">
            <h5 className="font-semibold text-slate-200 text-[11px] uppercase tracking-wider text-cyan-300">
              Why was this status assessed?
            </h5>
            <ul className="space-y-1.5 text-slate-300">
              {healthData.evidence_reasons.map((r, idx) => (
                <li key={idx} className="flex items-start space-x-2">
                  <span className="text-cyan-400 font-bold">•</span>
                  <span>{r}</span>
                </li>
              ))}
            </ul>

            {healthData.timeline_sparkline && healthData.timeline_sparkline.length > 0 && (
              <div className="mt-3 pt-3 border-t border-slate-800">
                <span className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider block mb-2">
                  Recent Passes Telemetry ({healthData.timeline_sparkline.length} observations)
                </span>
                <div className="flex items-end space-x-1 h-12 bg-slate-900/60 p-1.5 rounded border border-slate-800/60">
                  {healthData.timeline_sparkline.slice(-25).map((p, idx) => {
                    const heightPct = Math.min(100, Math.max(15, (p.frp_mw / (healthData.historical_p90_frp_mw * 2)) * 100));
                    const isHigh = p.frp_mw >= healthData.historical_p90_frp_mw * 1.5;
                    return (
                      <div
                        key={idx}
                        className="flex-1 rounded-t transition-all group relative cursor-pointer"
                        style={{ height: `${heightPct}%` }}
                      >
                        <div className={`w-full h-full rounded-t ${isHigh ? 'bg-rose-500' : 'bg-cyan-500/70'} hover:bg-cyan-300`} />
                        <div className="hidden group-hover:block absolute bottom-full mb-1 left-1/2 -translate-x-1/2 bg-slate-950 text-slate-100 text-[10px] px-2 py-1 rounded shadow-lg border border-slate-700 whitespace-nowrap z-30">
                          {p.frp_mw.toFixed(1)} MW ({p.satellite}, {p.day_night})
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
