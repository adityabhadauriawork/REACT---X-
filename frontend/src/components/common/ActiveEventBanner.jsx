import React from 'react';
import { 
  ShieldCheck, AlertTriangle, Flame, Siren, 
  Satellite, Activity, Radio, ArrowRight, Eye 
} from 'lucide-react';
import { determineGlobalSystemState } from '../../utils/canonicalState';

export default function ActiveEventBanner({
  globalSystemState,
  simulationResult,
  impactResult,
  thermalEvents = [],
  facilities = [],
  onNavigateTab,
  onOpenFacilityProfile
}) {
  const stateObj = globalSystemState || determineGlobalSystemState({
    simulationResult,
    impactResult,
    thermalEvents,
    facilities
  });

  const { state, label, badgeClass, description, isEmergency, event } = stateObj;

  let Icon = ShieldCheck;
  if (state === 'INCIDENT_ACTIVE') Icon = Siren;
  else if (state === 'CRITICAL') Icon = Flame;
  else if (state === 'ABNORMAL') Icon = AlertTriangle;
  else if (state === 'WATCH') Icon = Satellite;

  return (
    <div className="bg-[#090d16]/90 border border-slate-800 rounded-xl px-3.5 py-2 flex flex-wrap items-center justify-between gap-2 shadow-sm font-mono text-xs select-none">
      
      {/* Left: Status Badge & Description */}
      <div className="flex items-center space-x-2.5 min-w-0">
        <div className={`p-1.5 rounded-lg border flex items-center justify-center shrink-0 ${
          state === 'CRITICAL' || state === 'INCIDENT_ACTIVE' 
            ? 'bg-red-950/80 border-red-500/50 text-red-400 animate-pulse' 
            : (state === 'ABNORMAL' ? 'bg-amber-950/80 border-amber-500/50 text-amber-400' : 'bg-slate-900 border-slate-700 text-slate-300')
        }`}>
          <Icon className="w-3.5 h-3.5" />
        </div>

        <div className="flex items-center space-x-2 min-w-0">
          <span className={`px-2 py-0.5 rounded text-[10px] font-black uppercase tracking-wider border shrink-0 ${badgeClass}`}>
            {label}
          </span>
          <p className="text-[11px] text-slate-300 truncate">
            {description}
          </p>
        </div>
      </div>

      {/* Right: Fast Contextual Action */}
      <div className="flex items-center space-x-2 shrink-0">
        {state === 'INCIDENT_ACTIVE' && (
          <button
            type="button"
            onClick={() => onNavigateTab && onNavigateTab('evacuation')}
            className="px-2.5 py-1 rounded bg-red-950/80 hover:bg-red-900 text-red-300 border border-red-500/40 text-[10px] font-bold flex items-center gap-1 transition-all"
          >
            <span>Evacuation Route</span>
            <ArrowRight className="w-3 h-3" />
          </button>
        )}

        {state === 'CRITICAL' && event?.attributed_facility_id && (
          <button
            type="button"
            onClick={() => {
              const fac = facilities.find(f => f.id === event.attributed_facility_id);
              if (fac && onOpenFacilityProfile) onOpenFacilityProfile(fac);
            }}
            className="px-2.5 py-1 rounded bg-red-600 hover:bg-red-500 text-white text-[10px] font-bold flex items-center gap-1 shadow transition-all"
          >
            <Eye className="w-3 h-3" />
            <span>Triage Facility Dossier</span>
          </button>
        )}

        {state === 'ABNORMAL' && (
          <button
            type="button"
            onClick={() => onNavigateTab && onNavigateTab('thermal_persistence')}
            className="px-2.5 py-1 rounded bg-amber-950 hover:bg-amber-900 text-amber-300 border border-amber-500/40 text-[10px] font-bold flex items-center gap-1 transition-all"
          >
            <span>Inspect Baseline Z-Score</span>
            <ArrowRight className="w-3 h-3" />
          </button>
        )}

        {(state === 'NORMAL' || state === 'WATCH') && (
          <span className="text-[10px] text-slate-500 hidden sm:inline">
            NASA FIRMS VIIRS 375m & MODIS Synchronized
          </span>
        )}
      </div>

    </div>
  );
}
