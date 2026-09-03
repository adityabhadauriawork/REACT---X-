import React, { useState } from 'react';
import { 
  Home, Map, Flame, Building2, Cpu, Radio, ShieldCheck,
  Siren, Navigation, Users, FileText, Sliders, Play,
  BarChart3, FileCheck, Database, ShieldAlert, ChevronDown,
  ChevronRight, ChevronLeft, Layers, Sparkles
} from 'lucide-react';

export default function Sidebar({
  activeTab,
  onNavigateTab,
  activeThermalCount = 0,
  abnormalThermalCount = 0,
  isLiveData = false,
  collapsed,
  onToggleCollapse
}) {
  const [openSections, setOpenSections] = useState({
    HOME: true,
    MONITOR: true,
    INTELLIGENCE: false,
    RESPONSE: true,
    SIMULATION: true,
    SYSTEM: false
  });

  const toggleSection = (sectionKey) => {
    setOpenSections(prev => ({
      ...prev,
      [sectionKey]: !prev[sectionKey]
    }));
  };

  const navGroups = [
    {
      id: 'HOME',
      title: 'HOME',
      icon: Home,
      items: [
        { id: 'home', label: 'Executive Overview', icon: Home }
      ]
    },
    {
      id: 'MONITOR',
      title: 'MONITOR',
      icon: Map,
      badge: isLiveData ? 'LIVE' : 'SIMULATED',
      items: [
        { id: 'dashboard', label: 'Live Command Map', icon: Map, badge: activeThermalCount > 0 ? `${activeThermalCount}` : null },
        { id: 'thermal_sources', label: 'Thermal Sources', icon: Flame, badge: 'H3 L9' },
        { id: 'context_facilities', label: 'Monitored Facilities', icon: Building2, badge: 'National' }
      ]
    },
    {
      id: 'INTELLIGENCE',
      title: 'INTELLIGENCE',
      icon: Cpu,
      items: [
        { id: 'thermal_classification', label: 'AI Classification', icon: Cpu, badge: '7 Classes' },
        { id: 'risk_baselines', label: 'Hazard Trajectory', icon: Radio, badge: 'CUSUM' },
        { id: 'safety_center', label: 'Evidence & Fusion', icon: ShieldCheck, badge: 'Dempster-Shafer' }
      ]
    },
    {
      id: 'RESPONSE',
      title: 'RESPONSE',
      icon: Siren,
      badge: 'ACTIONABLE',
      items: [
        { id: 'impact', label: 'Incident Assessment', icon: Users },
        { id: 'evacuation', label: 'Evacuation Routing', icon: Navigation },
        { id: 'resources', label: 'Resource Dispatch', icon: Siren },
        { id: 'preplan', label: 'Emergency Pre-Plan', icon: FileText }
      ]
    },
    {
      id: 'SIMULATION',
      title: 'SIMULATION',
      icon: Sliders,
      badge: 'DAHEJ REF',
      items: [
        { id: 'simulation', label: 'Simulation Lab', icon: Sliders, badge: 'Scenarios A-J' }
      ]
    },
    {
      id: 'SYSTEM',
      title: 'SYSTEM',
      icon: Database,
      items: [
        { id: 'analytics', label: 'Historical Analytics', icon: BarChart3 },
        { id: 'audit', label: 'Audit Trail', icon: FileCheck },
        { id: 'system_health', label: 'System Readiness', icon: Database }
      ]
    }
  ];

  return (
    <aside 
      className={`bg-[#060a12]/95 border-r border-slate-800/90 flex flex-col transition-all duration-300 z-40 select-none ${
        collapsed ? 'w-16' : 'w-64 xl:w-72'
      }`}
    >
      {/* Brand Header */}
      <div className="p-3.5 border-b border-slate-800/80 flex items-center justify-between bg-gradient-to-r from-slate-950/80 to-[#090f1d]">
        {!collapsed && (
          <div className="flex items-center space-x-2.5 overflow-hidden">
            <div className="p-1.5 rounded-lg bg-cyan-950/80 border border-cyan-500/40 text-cyan-400 shrink-0 shadow-sm">
              <ShieldAlert className="w-5 h-5" />
            </div>
            <div className="leading-tight">
              <div className="flex items-center space-x-1.5">
                <span className="font-mono text-xs font-black tracking-wider text-cyan-400">REACT-X</span>
              </div>
              <p className="text-[10px] font-mono text-slate-400 font-semibold truncate">
                Industrial Hazard Platform
              </p>
            </div>
          </div>
        )}

        {collapsed && (
          <div className="mx-auto p-1.5 rounded-lg bg-cyan-950/80 border border-cyan-500/40 text-cyan-400 shadow-sm">
            <ShieldAlert className="w-5 h-5" />
          </div>
        )}

        <button
          type="button"
          onClick={onToggleCollapse}
          className="p-1 text-slate-400 hover:text-cyan-300 hover:bg-slate-800 rounded transition-colors hidden sm:block"
          title={collapsed ? "Expand Navigation" : "Collapse Navigation"}
        >
          <ChevronLeft className={`w-4 h-4 transition-transform ${collapsed ? 'rotate-180' : ''}`} />
        </button>
      </div>

      {/* Navigation Groups */}
      <div className="flex-1 overflow-y-auto py-2 space-y-1.5 custom-scrollbar font-mono text-xs">
        {navGroups.map((group) => {
          const isOpen = openSections[group.id];
          const hasActiveChild = group.items.some(item => item.id === activeTab);
          const GroupIcon = group.icon;

          return (
            <div key={group.id} className="px-2">
              {!collapsed ? (
                <button
                  type="button"
                  onClick={() => toggleSection(group.id)}
                  className={`w-full flex items-center justify-between px-2.5 py-1.5 rounded-lg font-bold text-[10px] uppercase tracking-wider transition-all ${
                    hasActiveChild 
                      ? 'text-cyan-300 bg-cyan-950/30 border border-cyan-500/20' 
                      : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900/60'
                  }`}
                >
                  <div className="flex items-center space-x-2">
                    <GroupIcon className={`w-3.5 h-3.5 ${hasActiveChild ? 'text-cyan-400' : 'text-slate-500'}`} />
                    <span>{group.title}</span>
                  </div>

                  <div className="flex items-center space-x-1.5">
                    {group.badge && (
                      <span className={`text-[8px] px-1.5 py-0.2 rounded font-bold border ${
                        group.badge.includes('ALERT') || group.badge.includes('ACTIONABLE')
                          ? 'bg-red-500/20 text-red-300 border-red-500/40'
                          : (group.badge.includes('LIVE') ? 'bg-cyan-500/20 text-cyan-300 border-cyan-500/40' : 'bg-slate-800 text-slate-400 border-slate-700')
                      }`}>
                        {group.badge}
                      </span>
                    )}
                    {isOpen ? <ChevronDown className="w-3 h-3 text-slate-500" /> : <ChevronRight className="w-3 h-3 text-slate-500" />}
                  </div>
                </button>
              ) : (
                <button
                  type="button"
                  onClick={() => toggleSection(group.id)}
                  className={`w-full p-2.5 rounded-lg flex justify-center transition-all ${
                    hasActiveChild ? 'bg-cyan-950/50 text-cyan-400 border border-cyan-500/30' : 'text-slate-400 hover:bg-slate-900'
                  }`}
                  title={group.title}
                >
                  <GroupIcon className="w-4 h-4" />
                </button>
              )}

              {/* Sub-Items */}
              {(!collapsed && isOpen) && (
                <div className="mt-1 ml-2 pl-2 border-l border-slate-800 space-y-0.5">
                  {group.items.map((item) => {
                    const isActive = activeTab === item.id;
                    const ItemIcon = item.icon;

                    return (
                      <button
                        key={item.id}
                        type="button"
                        onClick={() => onNavigateTab && onNavigateTab(item.id)}
                        className={`w-full flex items-center justify-between px-2.5 py-1.5 rounded-lg text-[11px] font-semibold transition-all ${
                          isActive
                            ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 shadow-sm font-bold'
                            : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900/60'
                        }`}
                      >
                        <div className="flex items-center space-x-2 truncate">
                          <ItemIcon className={`w-3.5 h-3.5 shrink-0 ${isActive ? 'text-cyan-400' : 'text-slate-500'}`} />
                          <span className="truncate">{item.label}</span>
                        </div>

                        {item.badge && (
                          <span className={`text-[8px] px-1.5 py-0.2 rounded font-bold shrink-0 border ${
                            item.badge.includes('Alert') || item.badge.includes('CRITICAL')
                              ? 'bg-red-500/20 text-red-300 border-red-500/40'
                              : 'bg-slate-800 text-slate-400 border-slate-700'
                          }`}>
                            {item.badge}
                          </span>
                        )}
                      </button>
                    );
                  })}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Footer Info */}
      <div className="p-3 border-t border-slate-800/80 bg-slate-950/60 font-mono text-[10px] text-slate-500">
        {!collapsed ? (
          <div className="space-y-1">
            <div className="flex justify-between items-center text-slate-400">
              <span>PLATFORM</span>
              <span className="text-cyan-400 font-bold">REACT-X v3.0</span>
            </div>
            <div className="flex justify-between items-center text-slate-400">
              <span>DEPLOYMENT</span>
              <span className="text-slate-300">ENTERPRISE</span>
            </div>
          </div>
        ) : (
          <div className="text-center text-[9px] text-cyan-400 font-bold">v3.0</div>
        )}
      </div>
    </aside>
  );
}
