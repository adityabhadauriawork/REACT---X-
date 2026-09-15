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
    <div className="bg-white border-b border-slate-200 px-4 py-2 flex items-center justify-between gap-3 overflow-x-auto shadow-2xs">
      <div className="flex items-center space-x-3 sm:space-x-4 min-w-max">
        
        {/* Metric 1: Active Incidents */}
        <div 
          onClick={() => onMetricClick && onMetricClick('incidents')}
          className="flex items-center gap-2.5 px-3 py-1.5 rounded-lg bg-slate-50 hover:bg-slate-100 border border-slate-200 cursor-pointer transition-colors"
        >
          <div className={`p-1.5 rounded-md ${activeIncidentsCount > 0 ? 'bg-rose-100 text-rose-700' : 'bg-slate-200 text-slate-700'}`}>
            <AlertTriangle className="w-3.5 h-3.5" />
          </div>
          <div>
            <div className="text-[10px] font-bold uppercase text-slate-500 tracking-wider">Active Incidents</div>
            <div className="text-sm font-black text-slate-900 flex items-center gap-1.5">
              <span>{activeIncidentsCount}</span>
              {activeIncidentsCount > 0 && (
                <span className="text-[10px] font-bold px-1.5 py-0.2 rounded-full bg-rose-50 text-rose-700 border border-rose-200">
                  Critical
                </span>
              )}
            </div>
          </div>
        </div>

        {/* Metric 2: High Risk Facilities */}
        <div 
          onClick={() => onMetricClick && onMetricClick('facilities_risk')}
          className="flex items-center gap-2.5 px-3 py-1.5 rounded-lg bg-slate-50 hover:bg-slate-100 border border-slate-200 cursor-pointer transition-colors"
        >
          <div className={`p-1.5 rounded-md ${highRiskFacilitiesCount > 0 ? 'bg-amber-100 text-amber-700' : 'bg-slate-200 text-slate-700'}`}>
            <Building2 className="w-3.5 h-3.5" />
          </div>
          <div>
            <div className="text-[10px] font-bold uppercase text-slate-500 tracking-wider">High-Risk Facilities</div>
            <div className="text-sm font-black text-slate-900 flex items-center gap-1.5">
              <span>{highRiskFacilitiesCount}</span>
              <span className="text-[10px] font-medium text-slate-500">/ {totalFacilitiesCount}</span>
            </div>
          </div>
        </div>

        {/* Metric 3: Persistent Sources */}
        <div 
          onClick={() => onMetricClick && onMetricClick('persistent_sources')}
          className="flex items-center gap-2.5 px-3 py-1.5 rounded-lg bg-slate-50 hover:bg-slate-100 border border-slate-200 cursor-pointer transition-colors"
        >
          <div className="p-1.5 rounded-md bg-purple-100 text-purple-700">
            <Flame className="w-3.5 h-3.5" />
          </div>
          <div>
            <div className="text-[10px] font-bold uppercase text-slate-500 tracking-wider">Persistent Sources</div>
            <div className="text-sm font-black text-slate-900 flex items-center gap-1.5">
              <span>{persistentSourcesCount}</span>
              <span className="text-[10px] font-medium text-slate-500">Flares / Process</span>
            </div>
          </div>
        </div>

        {/* Metric 4: Facilities Monitored */}
        <div 
          onClick={() => onMetricClick && onMetricClick('facilities_all')}
          className="flex items-center gap-2.5 px-3 py-1.5 rounded-lg bg-slate-50 hover:bg-slate-100 border border-slate-200 cursor-pointer transition-colors"
        >
          <div className="p-1.5 rounded-md bg-blue-100 text-blue-700">
            <Activity className="w-3.5 h-3.5" />
          </div>
          <div>
            <div className="text-[10px] font-bold uppercase text-slate-500 tracking-wider">Facilities Monitored</div>
            <div className="text-sm font-black text-slate-900 flex items-center gap-1.5">
              <span>{totalFacilitiesCount}</span>
              <span className="text-[10px] font-bold px-1.5 py-0.2 rounded-full bg-blue-50 text-blue-700 border border-blue-200">
                GIDC Grid
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Metric 5: Data Freshness Status */}
      <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-emerald-50 border border-emerald-200 text-emerald-800 shrink-0">
        <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
        <div className="text-xs">
          <span className="font-bold">DATA FRESHNESS: </span>
          <span className="font-mono text-emerald-900 font-semibold">LIVE (4m Sat / Real-time OT)</span>
        </div>
      </div>
    </div>
  );
}
