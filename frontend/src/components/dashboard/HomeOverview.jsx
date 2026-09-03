import React from 'react';
import { 
  Map, Flame, Building2, Siren, Sliders, ShieldCheck, 
  AlertTriangle, CheckCircle2, ArrowRight, Activity, 
  Satellite, Radio, Sparkles, Database, Eye, ShieldAlert
} from 'lucide-react';

export default function HomeOverview({
  onNavigate,
  activeThermalCount = 2,
  abnormalCount = 1,
  facilitiesCount = 10,
  dataMode = "SIMULATION",
  onSelectFacility
}) {
  const quickActions = [
    {
      id: 'dashboard',
      title: 'LIVE MONITORING',
      subtitle: 'Real-time interactive command map, active thermal hotspots, and facility perimeters.',
      icon: Map,
      badge: `${activeThermalCount} Hotspots`,
      badgeColor: 'bg-cyan-500/20 text-cyan-300 border-cyan-500/40',
      gradient: 'from-cyan-950/40 via-slate-900/60 to-slate-950',
      borderColor: 'border-cyan-500/30 hover:border-cyan-400'
    },
    {
      id: 'thermal_sources',
      title: 'THERMAL SOURCES',
      subtitle: 'Inspect spatiotemporal clustering, 10m land cover context, and AI source classification.',
      icon: Flame,
      badge: 'Multimodal AI',
      badgeColor: 'bg-orange-500/20 text-orange-300 border-orange-500/40',
      gradient: 'from-orange-950/40 via-slate-900/60 to-slate-950',
      borderColor: 'border-orange-500/30 hover:border-orange-400'
    },
    {
      id: 'context_facilities',
      title: 'FACILITY INTELLIGENCE',
      subtitle: 'Analyze high-frequency telemetry, CUSUM trajectory prediction, and radiometric thermal video.',
      icon: Building2,
      badge: `${facilitiesCount} Monitored`,
      badgeColor: 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40',
      gradient: 'from-emerald-950/40 via-slate-900/60 to-slate-950',
      borderColor: 'border-emerald-500/30 hover:border-emerald-400'
    },
    {
      id: 'impact',
      title: 'INCIDENT RESPONSE',
      subtitle: 'Access ALOHA chemical plume dispersion, safe evacuation routing, and resource quotas.',
      icon: Siren,
      badge: 'Actionable',
      badgeColor: 'bg-red-500/20 text-red-300 border-red-500/40',
      gradient: 'from-red-950/40 via-slate-900/60 to-slate-950',
      borderColor: 'border-red-500/30 hover:border-red-400'
    },
    {
      id: 'simulation',
      title: 'SIMULATION LAB',
      subtitle: 'Execute controlled industrial scenarios and guided step-by-step technical demonstrations.',
      icon: Sliders,
      badge: 'Reference Lab',
      badgeColor: 'bg-purple-500/20 text-purple-300 border-purple-500/40',
      gradient: 'from-purple-950/40 via-slate-900/60 to-slate-950',
      borderColor: 'border-purple-500/30 hover:border-purple-400'
    }
  ];

  const priorityEvents = [
    {
      id: 'EVT-DAHEJ-T04',
      facility: 'Dahej Petrochemical Complex Alpha',
      location: 'Unit 04 • Tank T-04',
      status: 'HAZARD DEVELOPING',
      statusColor: 'bg-amber-500/20 text-amber-300 border-amber-500/40',
      details: 'Pressure rising at +1.45 bar/min with localized radiometric hotspot surge (42.0 MW).',
      actionTab: 'context_facilities'
    },
    {
      id: 'EVT-JAMNAGAR-FLARE',
      facility: 'Jamnagar Integrated Refinery Complex',
      location: 'Flare Header Area 2',
      status: 'ROUTINE PROCESS HEAT',
      statusColor: 'bg-cyan-500/20 text-cyan-300 border-cyan-500/40',
      details: 'Elevated thermal centroid (145 MW) verified consistent with historical empirical baseline.',
      actionTab: 'thermal_sources'
    },
    {
      id: 'EVT-ROURKELA-STEEL',
      facility: 'Rourkela Integrated Steel Plant',
      location: 'Blast Furnace Perimeter',
      status: 'NOMINAL BASELINE',
      statusColor: 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40',
      details: 'Satellite pass clear; land cover confirmed industrial built-up area.',
      actionTab: 'dashboard'
    }
  ];

  return (
    <div className="space-y-6 font-mono p-1">
      {/* Top Banner: Answers "What is happening? Where? How serious?" */}
      <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-6 shadow-2xl relative overflow-hidden">
        <div className="absolute top-0 right-0 w-96 h-96 bg-cyan-500/5 rounded-full blur-3xl pointer-events-none" />
        
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6 relative z-10">
          <div className="space-y-2">
            <div className="flex items-center space-x-3">
              <span className="text-xs font-bold px-2.5 py-1 rounded-full bg-cyan-950 border border-cyan-500/40 text-cyan-400">
                SYSTEM OVERVIEW
              </span>
              <span className="text-xs px-2.5 py-1 rounded-full bg-purple-950/60 border border-purple-500/30 text-purple-300">
                MODE: {dataMode}
              </span>
            </div>
            <h1 className="text-2xl lg:text-3xl font-extrabold text-white tracking-tight">
              Industrial Hazard Intelligence
            </h1>
            <p className="text-xs text-slate-400 font-sans max-w-2xl">
              Unified multimodal platform combining NASA FIRMS satellite thermal detection, high-frequency process telemetry, radiometric thermal vision, and predictive consequence modeling across India.
            </p>
          </div>

          {/* Quick Metrics Strip */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-center">
            <div className="bg-slate-950/80 p-3 rounded-xl border border-slate-800">
              <span className="text-[10px] text-slate-500 uppercase font-bold block">Active Alerts</span>
              <span className="text-lg font-bold text-amber-400 font-mono">{abnormalCount}</span>
            </div>
            <div className="bg-slate-950/80 p-3 rounded-xl border border-slate-800">
              <span className="text-[10px] text-slate-500 uppercase font-bold block">Hotspots</span>
              <span className="text-lg font-bold text-cyan-400 font-mono">{activeThermalCount}</span>
            </div>
            <div className="bg-slate-950/80 p-3 rounded-xl border border-slate-800">
              <span className="text-[10px] text-slate-500 uppercase font-bold block">Facilities</span>
              <span className="text-lg font-bold text-emerald-400 font-mono">{facilitiesCount}</span>
            </div>
            <div className="bg-slate-950/80 p-3 rounded-xl border border-slate-800">
              <span className="text-[10px] text-slate-500 uppercase font-bold block">Freshness</span>
              <span className="text-lg font-bold text-slate-200 font-mono">100%</span>
            </div>
          </div>
        </div>
      </div>

      {/* Answers "What should I open next?" -> Large Task-Oriented Entry Cards */}
      <div className="space-y-3">
        <h2 className="text-xs font-bold text-slate-400 uppercase tracking-wider flex items-center space-x-2">
          <span>Primary Operational Workspaces</span>
        </h2>

        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {quickActions.map((action) => {
            const Icon = action.icon;
            return (
              <button
                key={action.id}
                onClick={() => onNavigate && onNavigate(action.id)}
                className={`bg-gradient-to-b ${action.gradient} border ${action.borderColor} rounded-2xl p-5 text-left transition-all duration-300 hover:scale-[1.02] hover:shadow-xl group flex flex-col justify-between min-h-[160px]`}
              >
                <div className="flex items-start justify-between w-full mb-3">
                  <div className="p-3 rounded-xl bg-slate-950/80 border border-slate-800 text-cyan-400 group-hover:text-white transition-colors">
                    <Icon className="w-6 h-6" />
                  </div>
                  <span className={`text-[10px] px-2 py-0.5 rounded-full font-bold border ${action.badgeColor}`}>
                    {action.badge}
                  </span>
                </div>

                <div>
                  <h3 className="text-sm font-bold text-white group-hover:text-cyan-300 transition-colors flex items-center justify-between">
                    <span>{action.title}</span>
                    <ArrowRight className="w-4 h-4 text-slate-500 group-hover:text-cyan-400 transition-transform group-hover:translate-x-1" />
                  </h3>
                  <p className="text-xs text-slate-400 font-sans mt-1 line-clamp-2">
                    {action.subtitle}
                  </p>
                </div>
              </button>
            );
          })}
        </div>
      </div>

      {/* Priority Events Strip */}
      <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-5 shadow-xl space-y-4">
        <div className="flex items-center justify-between border-b border-slate-800 pb-3">
          <div className="flex items-center space-x-2.5">
            <Activity className="w-4 h-4 text-amber-400" />
            <h3 className="text-xs font-bold text-white uppercase tracking-wider">
              Priority Monitored Events
            </h3>
          </div>
          <span className="text-[10px] text-slate-500">Live National Triage Feed</span>
        </div>

        <div className="space-y-2.5">
          {priorityEvents.map((evt) => (
            <div 
              key={evt.id}
              className="bg-slate-950/60 border border-slate-800/80 rounded-xl p-3.5 flex flex-col sm:flex-row sm:items-center justify-between gap-3 hover:border-slate-700 transition-all"
            >
              <div className="space-y-1">
                <div className="flex items-center space-x-2">
                  <span className="text-xs font-bold text-white">{evt.facility}</span>
                  <span className="text-[10px] text-slate-400">({evt.location})</span>
                  <span className={`text-[9px] px-2 py-0.5 rounded-full font-bold border ${evt.statusColor}`}>
                    {evt.status}
                  </span>
                </div>
                <p className="text-xs text-slate-300 font-sans">{evt.details}</p>
              </div>

              <button
                onClick={() => onNavigate && onNavigate(evt.actionTab)}
                className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-cyan-300 border border-slate-700 text-xs font-bold transition-all shrink-0 flex items-center space-x-1 self-start sm:self-auto"
              >
                <span>Inspect</span>
                <ArrowRight className="w-3 h-3" />
              </button>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
