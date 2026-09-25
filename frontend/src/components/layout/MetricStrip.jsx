import React from 'react';
import { 
  AlertTriangle, Building2, Flame, Satellite, 
  Clock, ShieldAlert, Activity, CheckCircle2 
} from 'lucide-react';

export default function MetricStrip({
  facilities = [],
  thermalEvents = [],
  thermalSources = [],
  persistentClusters = [],
  simulationResult,
  onMetricClick
}) {
  // Compute metrics from actual data
  const activeIncidentsCount = thermalEvents.filter(e => 
    e.classification === 'INDUSTRIAL_FIRE' || (e.abnormality_score && e.abnormality_score >= 70)
  ).length + (simulationResult ? 1 : 0);

  const highRiskFacilitiesCount = facilities.filter(f => 
    f.current_status === 'CRITICAL_RISK' || f.current_status === 'ELEVATED_RISK' || (f.current_abnormality_score && f.current_abnormality_score >= 50)
  ).length;

  const persistentSourcesCount = persistentClusters.length || thermalSources.filter(s => 
    s.source_status === 'PERSISTENT_SOURCE' || s.source_status === 'ROUTINE_SOURCE'
  ).length;

  const totalFacilitiesCount = facilities.length || 24;

  return (
    <div className="bg-white dark:bg-slate-900 border-b border-slate-200 dark:border-slate-800 px-4 py-2 flex items-center justify-between gap-3 overflow-x-auto shadow-2xs transition-colors">
      <div className="flex items-center space-x-3 sm:space-x-4 min-w-max">
        
        {/* Metric 1: Active Incidents */}
        <div 
          onClick={() => onMetricClick && onMetricClick('incidents')}
          className="flex items-center gap-2.5 px-3 py-1.5 rounded-lg bg-slate-50 dark:bg-slate-800/60 hover:bg-slate-100 dark:hover:bg-slate-800 border border-slate-200 dark:border-slate-700 cursor-pointer transition-colors"
        >
          <div className={`p-1.5 rounded-md ${activeIncidentsCount > 0 ? 'bg-rose-100 dark:bg-rose-950/60 text-rose-700 dark:text-rose-400' : 'bg-slate-200 dark:bg-slate-700 text-slate-700 dark:text-slate-300'}`}>
            <AlertTriangle className="w-3.5 h-3.5" />
          </div>
          <div>
            <div className="text-[10px] font-bold uppercase text-slate-500 dark:text-slate-400 tracking-wider">Active Incidents</div>
            <div className="text-sm font-black text-slate-900 dark:text-slate-100 flex items-center gap-1.5">
              <span>{activeIncidentsCount}</span>
              {activeIncidentsCount > 0 && (
                <span className="text-[10px] font-bold px-1.5 py-0.2 rounded-full bg-rose-50 dark:bg-rose-950/40 text-rose-700 dark:text-rose-400 border border-rose-200 dark:border-rose-800">
                  Critical
                </span>
              )}
            </div>
          </div>
        </div>

        {/* Metric 2: High Risk Facilities */}
        <div 
          onClick={() => onMetricClick && onMetricClick('facilities_risk')}
          className="flex items-center gap-2.5 px-3 py-1.5 rounded-lg bg-slate-50 dark:bg-slate-800/60 hover:bg-slate-100 dark:hover:bg-slate-800 border border-slate-200 dark:border-slate-700 cursor-pointer transition-colors"
        >
          <div className={`p-1.5 rounded-md ${highRiskFacilitiesCount > 0 ? 'bg-amber-100 dark:bg-amber-950/60 text-amber-700 dark:text-amber-400' : 'bg-slate-200 dark:bg-slate-700 text-slate-700 dark:text-slate-300'}`}>
            <Building2 className="w-3.5 h-3.5" />
          </div>
          <div>
            <div className="text-[10px] font-bold uppercase text-slate-500 dark:text-slate-400 tracking-wider">High-Risk Facilities</div>
            <div className="text-sm font-black text-slate-900 dark:text-slate-100 flex items-center gap-1.5">
              <span>{highRiskFacilitiesCount}</span>
              <span className="text-[10px] font-medium text-slate-500 dark:text-slate-400">/ {totalFacilitiesCount}</span>
            </div>
          </div>
        </div>

        {/* Metric 3: Persistent Sources */}
        <div 
          onClick={() => onMetricClick && onMetricClick('persistent_sources')}
          className="flex items-center gap-2.5 px-3 py-1.5 rounded-lg bg-slate-50 dark:bg-slate-800/60 hover:bg-slate-100 dark:hover:bg-slate-800 border border-slate-200 dark:border-slate-700 cursor-pointer transition-colors"
        >
          <div className="p-1.5 rounded-md bg-purple-100 dark:bg-purple-950/60 text-purple-700 dark:text-purple-400">
            <Flame className="w-3.5 h-3.5" />
          </div>
          <div>
            <div className="text-[10px] font-bold uppercase text-slate-500 dark:text-slate-400 tracking-wider">Persistent Sources</div>
            <div className="text-sm font-black text-slate-900 dark:text-slate-100 flex items-center gap-1.5">
              <span>{persistentSourcesCount}</span>
              <span className="text-[10px] font-medium text-slate-500 dark:text-slate-400">Flares / Process</span>
            </div>
          </div>
        </div>

        {/* Metric 4: Facilities Monitored */}
        <div 
          onClick={() => onMetricClick && onMetricClick('facilities_all')}
          className="flex items-center gap-2.5 px-3 py-1.5 rounded-lg bg-slate-50 dark:bg-slate-800/60 hover:bg-slate-100 dark:hover:bg-slate-800 border border-slate-200 dark:border-slate-700 cursor-pointer transition-colors"
        >
          <div className="p-1.5 rounded-md bg-blue-100 dark:bg-blue-950/60 text-blue-700 dark:text-blue-400">
            <Activity className="w-3.5 h-3.5" />
          </div>
          <div>
            <div className="text-[10px] font-bold uppercase text-slate-500 dark:text-slate-400 tracking-wider">National Registry</div>
            <div className="text-sm font-black text-slate-900 dark:text-slate-100 flex items-center gap-1.5">
              <span>{totalFacilitiesCount}</span>
              <span className="text-[10px] font-bold px-1.5 py-0.2 rounded-full bg-blue-50 dark:bg-blue-950/40 text-blue-700 dark:text-blue-400 border border-blue-200 dark:border-blue-800">
                Active Grid
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Metric 5: Data Freshness Status */}
      <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-200 dark:border-emerald-800/60 text-emerald-800 dark:text-emerald-300 shrink-0">
        <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
        <div className="text-xs">
          <span className="font-bold">FEEDS: </span>
          <span className="font-mono text-emerald-900 dark:text-emerald-200 font-semibold">FIRMS • MOSDAC • SENTINEL</span>
        </div>
      </div>
    </div>
  );
}
