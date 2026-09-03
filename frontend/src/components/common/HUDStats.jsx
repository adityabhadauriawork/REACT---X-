import React from 'react';
import { 
  Users, Flame, AlertOctagon, Navigation, 
  ShieldCheck, Siren, Activity, ShieldAlert,
  Satellite, Building2, Radio, AlertTriangle, Database
} from 'lucide-react';

export default function HUDStats({ 
  impactResult, 
  simulationResult, 
  resourcePlan,
  thermalEvents = [],
  facilities = [],
  persistentClusters = [],
  isLiveData = false
}) {
  // 1. SATELLITE THERMAL INTELLIGENCE / OVERVIEW MODE (When no emergency incident active)
  if (!simulationResult || !impactResult) {
    const totalEvents = thermalEvents.length;
    const liveEvents = thermalEvents.filter(e => e.is_live_data).length;
    const demoEvents = totalEvents - liveEvents;
    const industrialEvents = thermalEvents.filter(e => e.attributed_facility_id).length;
    const persistentCount = persistentClusters.length;
    const abnormalCount = thermalEvents.filter(e => e.abnormality_score >= 50.0 || e.is_abnormal).length;
    const highRiskCount = thermalEvents.filter(e => e.risk_level === 'CRITICAL' || e.classification === 'INDUSTRIAL_FIRE').length;

    return (
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-2 font-mono text-xs">
        
        {/* 1. Active Thermal Events */}
        <div className="bg-slate-900/80 px-3 py-2 rounded-xl border border-slate-800 flex items-center space-x-2.5 shadow-sm">
          <div className="p-2 rounded-lg bg-cyan-950/80 border border-cyan-500/40 text-cyan-400 shrink-0">
            <Satellite className="w-4 h-4" />
          </div>
          <div className="truncate">
            <div className="text-[9px] text-slate-400 uppercase tracking-wider font-bold flex items-center justify-between">
              <span>Active Thermal Hotspots</span>
              <span className={`text-[8px] px-1 rounded font-bold ${
                isLiveData || liveEvents > 0 ? 'bg-cyan-500/20 text-cyan-300' : 'bg-amber-500/20 text-amber-300'
              }`}>
                {liveEvents > 0 ? `${liveEvents} Live` : 'Simulation'}
              </span>
            </div>
            <div className="text-xs sm:text-sm font-black text-white flex items-center gap-1.5">
              <span>{totalEvents} Observations</span>
            </div>
          </div>
        </div>

        {/* 2. Industrial Sources */}
        <div className="bg-slate-900/80 px-3 py-2 rounded-xl border border-slate-800 flex items-center space-x-2.5 shadow-sm">
          <div className="p-2 rounded-lg bg-indigo-950/80 border border-indigo-500/40 text-indigo-400 shrink-0">
            <Building2 className="w-4 h-4" />
          </div>
          <div className="truncate">
            <div className="text-[9px] text-slate-400 uppercase tracking-wider font-bold">Industrial Sources</div>
            <div className="text-xs sm:text-sm font-black text-slate-200">
              {industrialEvents > 0 ? `${industrialEvents} Attributed` : 'Analysis Pending'}
            </div>
          </div>
        </div>

        {/* 3. Persistent Sources */}
        <div className="bg-slate-900/80 px-3 py-2 rounded-xl border border-slate-800 flex items-center space-x-2.5 shadow-sm">
          <div className="p-2 rounded-lg bg-amber-950/80 border border-amber-500/40 text-amber-400 shrink-0">
            <Radio className="w-4 h-4" />
          </div>
          <div className="truncate">
            <div className="text-[9px] text-slate-400 uppercase tracking-wider font-bold">Persistent Sources</div>
            <div className="text-xs sm:text-sm font-black text-slate-200">
              {persistentCount > 0 ? `${persistentCount} Baselines` : 'Analysis Pending'}
            </div>
          </div>
        </div>

        {/* 4. Abnormal Sources */}
        <div className="bg-slate-900/80 px-3 py-2 rounded-xl border border-slate-800 flex items-center space-x-2.5 shadow-sm">
          <div className={`p-2 rounded-lg border shrink-0 ${
            abnormalCount > 0 
              ? 'bg-amber-950/80 border-amber-500/50 text-amber-400 animate-pulse' 
              : 'bg-emerald-950/80 border-emerald-500/40 text-emerald-400'
          }`}>
            <Activity className="w-4 h-4" />
          </div>
          <div className="truncate">
            <div className="text-[9px] text-slate-400 uppercase tracking-wider font-bold">Abnormal Sources</div>
            <div className={`text-xs sm:text-sm font-black ${abnormalCount > 0 ? 'text-amber-300' : 'text-emerald-400'}`}>
              {abnormalCount > 0 ? `${abnormalCount} Elevated (Z ≥ 3.0)` : '0 Nominal'}
            </div>
          </div>
        </div>

        {/* 5. High-Risk Events */}
        <div className="bg-slate-900/80 px-3 py-2 rounded-xl border border-slate-800 flex items-center space-x-2.5 shadow-sm">
          <div className={`p-2 rounded-lg border shrink-0 ${
            highRiskCount > 0 
              ? 'bg-red-950/80 border-red-500/60 text-red-400 animate-bounce' 
              : 'bg-emerald-950/80 border-emerald-500/40 text-emerald-400'
          }`}>
            <ShieldAlert className="w-4 h-4" />
          </div>
          <div className="truncate">
            <div className="text-[9px] text-slate-400 uppercase tracking-wider font-bold">High-Risk Events</div>
            <div className={`text-xs sm:text-sm font-black ${highRiskCount > 0 ? 'text-red-400' : 'text-emerald-400'}`}>
              {highRiskCount > 0 ? `${highRiskCount} Fire Alert` : '0 Active Fires'}
            </div>
          </div>
        </div>

      </div>
    );
  }

  // 2. INCIDENT RESPONSE MODE (When an active chemical plume is modeled)
  const exposed = impactResult?.affected_workers_count ?? 0;
  const redZoneWorkers = impactResult?.red_zone_workers_count ?? 0;
  const threatenedAssets = impactResult?.affected_assets_count ?? 0;
  const primaryRoute = impactResult?.primary_evacuation_route;
  const isEvacSafe = primaryRoute?.is_safe !== false;
  const maxReach = simulationResult?.max_red_reach_m ?? 0;
  const firewater = resourcePlan?.foam_water_requirements?.firewater_demand_lpm ?? 0;

  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-2 font-mono text-xs">
      
      {/* 1. Exposed Personnel */}
      <div className="bg-slate-900/80 px-3 py-2 rounded-xl border border-slate-800 flex items-center space-x-2.5 shadow-sm">
        <div className={`p-2 rounded-lg border shrink-0 ${
          exposed > 0 
            ? 'bg-red-950/80 border-red-500/40 text-red-400 animate-pulse' 
            : 'bg-emerald-950/80 border-emerald-500/40 text-emerald-400'
        }`}>
          <Users className="w-4 h-4" />
        </div>
        <div className="truncate">
          <div className="text-[9px] text-slate-400 uppercase tracking-wider font-bold">Personnel Exposed</div>
          <div className="text-xs sm:text-sm font-black text-white">
            {exposed} <span className="text-[10px] text-slate-400 font-normal">({redZoneWorkers} in Red Zone)</span>
          </div>
        </div>
      </div>

      {/* 2. Max ERPG-3 Downwind Reach */}
      <div className="bg-slate-900/80 px-3 py-2 rounded-xl border border-slate-800 flex items-center space-x-2.5 shadow-sm">
        <div className="p-2 rounded-lg bg-orange-950/80 border border-orange-500/40 text-orange-400 shrink-0">
          <Flame className="w-4 h-4" />
        </div>
        <div className="truncate">
          <div className="text-[9px] text-slate-400 uppercase tracking-wider font-bold">Toxic Plume Reach</div>
          <div className="text-xs sm:text-sm font-black text-orange-300">
            {maxReach > 0 ? `${maxReach.toFixed(0)}m Downwind` : 'Local Release'}
          </div>
        </div>
      </div>

      {/* 3. Threatened Assets */}
      <div className="bg-slate-900/80 px-3 py-2 rounded-xl border border-slate-800 flex items-center space-x-2.5 shadow-sm">
        <div className="p-2 rounded-lg bg-indigo-950/80 border border-indigo-500/40 text-indigo-400 shrink-0">
          <AlertOctagon className="w-4 h-4" />
        </div>
        <div className="truncate">
          <div className="text-[9px] text-slate-400 uppercase tracking-wider font-bold">Threatened Assets</div>
          <div className="text-xs sm:text-sm font-black text-slate-200">
            {threatenedAssets} <span className="text-[10px] text-slate-400 font-normal">Units at Risk</span>
          </div>
        </div>
      </div>

      {/* 4. Evacuation Status */}
      <div className="bg-slate-900/80 px-3 py-2 rounded-xl border border-slate-800 flex items-center space-x-2.5 shadow-sm">
        <div className={`p-2 rounded-lg border shrink-0 ${
          isEvacSafe 
            ? 'bg-emerald-950/80 border-emerald-500/40 text-emerald-400' 
            : 'bg-red-950/80 border-red-500/40 text-red-400'
        }`}>
          <Navigation className="w-4 h-4" />
        </div>
        <div className="truncate">
          <div className="text-[9px] text-slate-400 uppercase tracking-wider font-bold">Evacuation Vector</div>
          <div className={`text-xs sm:text-sm font-black ${isEvacSafe ? 'text-emerald-400' : 'text-red-400'}`}>
            {isEvacSafe ? 'Safe Corridor Clear' : 'Route Compromised'}
          </div>
        </div>
      </div>

      {/* 5. Firewater Demand */}
      <div className="bg-slate-900/80 px-3 py-2 rounded-xl border border-slate-800 flex items-center space-x-2.5 shadow-sm">
        <div className="p-2 rounded-lg bg-blue-950/80 border border-blue-500/40 text-blue-400 shrink-0">
          <Siren className="w-4 h-4" />
        </div>
        <div className="truncate">
          <div className="text-[9px] text-slate-400 uppercase tracking-wider font-bold">Firewater Demand</div>
          <div className="text-xs sm:text-sm font-black text-blue-300">
            {firewater > 0 ? `${firewater.toLocaleString()} LPM` : 'Standby Rate'}
          </div>
        </div>
      </div>

    </div>
  );
}
