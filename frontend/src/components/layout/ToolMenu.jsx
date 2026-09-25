import React, { useState, useRef, useEffect } from 'react';
import { 
  Sliders, Activity, Flame, Building2, 
  BarChart3, Satellite, LineChart, TrendingUp,
  ShieldAlert, AlertTriangle, ShieldCheck, 
  Navigation, Droplets, FileText, ChevronRight,
  Layers, Sparkles, X, Radio, Network, Send
} from 'lucide-react';

export default function ToolMenu({ onSelectTool }) {
  const [isOpen, setIsOpen] = useState(false);
  const menuRef = useRef(null);

  // Close when clicking outside
  useEffect(() => {
    function handleClickOutside(e) {
      if (menuRef.current && !menuRef.current.contains(e.target)) {
        setIsOpen(false);
      }
    }
    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [isOpen]);

  const handleToolClick = (toolKey) => {
    onSelectTool && onSelectTool(toolKey);
    setIsOpen(false);
  };

  return (
    <div ref={menuRef} className="relative z-[400]">
      {/* Floating Tools Trigger Button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 px-3.5 py-2 rounded-xl bg-white/95 dark:bg-slate-900/95 backdrop-blur hover:bg-white dark:hover:bg-slate-900 text-slate-800 dark:text-slate-100 font-bold text-xs border border-slate-300 dark:border-slate-700 shadow-md cursor-pointer transition-all hover:border-blue-400"
      >
        <Sliders className="w-4 h-4 text-blue-600 dark:text-blue-400" />
        <span>TOOLS & WORKFLOWS</span>
        <span className="text-[10px] px-1.5 py-0.2 rounded bg-blue-50 dark:bg-blue-950/60 text-blue-700 dark:text-blue-300 font-extrabold border border-blue-200 dark:border-blue-800">
          5 Categories
        </span>
      </button>

      {/* Floating Command Panel Dropdown */}
      {isOpen && (
        <div className="absolute left-0 top-full mt-2 w-[460px] bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl shadow-2xl p-4 z-50 text-xs space-y-4 animate-in fade-in slide-in-from-top-2 duration-150 text-slate-800 dark:text-slate-100">
          
          <div className="flex items-center justify-between pb-2 border-b border-slate-100 dark:border-slate-800">
            <div>
              <h3 className="font-bold text-slate-900 dark:text-slate-100 text-sm">Industrial Intelligence Tools</h3>
              <p className="text-[11px] text-slate-500 dark:text-slate-400">Select an on-demand analysis or response workflow</p>
            </div>
            <button 
              onClick={() => setIsOpen(false)}
              className="p-1 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 cursor-pointer"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          {/* Tool Categories Grid */}
          <div className="grid grid-cols-2 gap-3">
            
            {/* Category 1: Thermal & Detection */}
            <div className="space-y-1.5">
              <div className="text-[10px] font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider flex items-center gap-1">
                <Satellite className="w-3 h-3 text-blue-600 dark:text-blue-400" /> 1. Earth Observation
              </div>
              
              <button 
                onClick={() => handleToolClick('live_thermal')}
                className="w-full text-left p-2 rounded-lg bg-slate-50 dark:bg-slate-800/60 hover:bg-blue-50 dark:hover:bg-blue-950/40 hover:text-blue-900 dark:hover:text-blue-300 border border-slate-200 dark:border-slate-700 transition flex items-center justify-between cursor-pointer"
              >
                <span>Live Thermal Hotspots</span>
                <ChevronRight className="w-3.5 h-3.5 text-slate-400" />
              </button>
              
              <button 
                onClick={() => handleToolClick('persistent_sources')}
                className="w-full text-left p-2 rounded-lg bg-slate-50 dark:bg-slate-800/60 hover:bg-blue-50 dark:hover:bg-blue-950/40 hover:text-blue-900 dark:hover:text-blue-300 border border-slate-200 dark:border-slate-700 transition flex items-center justify-between cursor-pointer"
              >
                <span>Persistent Flare Sources</span>
                <ChevronRight className="w-3.5 h-3.5 text-slate-400" />
              </button>
            </div>

            {/* Category 2: Classification & Evidence */}
            <div className="space-y-1.5">
              <div className="text-[10px] font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider flex items-center gap-1">
                <ShieldCheck className="w-3 h-3 text-emerald-600 dark:text-emerald-400" /> 2. 7-Class AI & Fusion
              </div>

              <button 
                onClick={() => handleToolClick('source_classification')}
                className="w-full text-left p-2 rounded-lg bg-slate-50 dark:bg-slate-800/60 hover:bg-emerald-50 dark:hover:bg-emerald-950/40 hover:text-emerald-900 dark:hover:text-emerald-300 border border-slate-200 dark:border-slate-700 transition flex items-center justify-between cursor-pointer"
              >
                <span>7-Class AI Classification</span>
                <ChevronRight className="w-3.5 h-3.5 text-slate-400" />
              </button>

              <button 
                onClick={() => handleToolClick('satellite_comparison')}
                className="w-full text-left p-2 rounded-lg bg-slate-50 dark:bg-slate-800/60 hover:bg-emerald-50 dark:hover:bg-emerald-950/40 hover:text-emerald-900 dark:hover:text-emerald-300 border border-slate-200 dark:border-slate-700 transition flex items-center justify-between cursor-pointer"
              >
                <span>Dempster-Shafer Consensus</span>
                <ChevronRight className="w-3.5 h-3.5 text-slate-400" />
              </button>
            </div>

            {/* Category 3: Consequence & Domino Cascade */}
            <div className="space-y-1.5">
              <div className="text-[10px] font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider flex items-center gap-1">
                <Network className="w-3 h-3 text-purple-600 dark:text-purple-400" /> 3. Domino Cascade
              </div>

              <button 
                onClick={() => handleToolClick('domino_risk')}
                className="w-full text-left p-2 rounded-lg bg-slate-50 dark:bg-slate-800/60 hover:bg-purple-50 dark:hover:bg-purple-950/40 hover:text-purple-900 dark:hover:text-purple-300 border border-slate-200 dark:border-slate-700 transition flex items-center justify-between cursor-pointer"
              >
                <span>Domino / Cascade Graph</span>
                <ChevronRight className="w-3.5 h-3.5 text-slate-400" />
              </button>

              <button 
                onClick={() => handleToolClick('impact_zones')}
                className="w-full text-left p-2 rounded-lg bg-slate-50 dark:bg-slate-800/60 hover:bg-purple-50 dark:hover:bg-purple-950/40 hover:text-purple-900 dark:hover:text-purple-300 border border-slate-200 dark:border-slate-700 transition flex items-center justify-between cursor-pointer"
              >
                <span>Gaussian Dispersion Plume</span>
                <ChevronRight className="w-3.5 h-3.5 text-slate-400" />
              </button>
            </div>

            {/* Category 4: Emergency Response & SOS */}
            <div className="space-y-1.5">
              <div className="text-[10px] font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider flex items-center gap-1">
                <Send className="w-3 h-3 text-red-600 dark:text-red-400" /> 4. Emergency Response / SOS
              </div>

              <button 
                onClick={() => handleToolClick('emergency_sos')}
                className="w-full text-left p-2 rounded-lg bg-slate-50 dark:bg-slate-800/60 hover:bg-red-50 dark:hover:bg-red-950/40 hover:text-red-900 dark:hover:text-red-300 border border-slate-200 dark:border-slate-700 transition flex items-center justify-between cursor-pointer"
              >
                <span>Prepare SOS Alert Packet</span>
                <ChevronRight className="w-3.5 h-3.5 text-slate-400" />
              </button>

              <button 
                onClick={() => handleToolClick('evacuation_support')}
                className="w-full text-left p-2 rounded-lg bg-slate-50 dark:bg-slate-800/60 hover:bg-red-50 dark:hover:bg-red-950/40 hover:text-red-900 dark:hover:text-red-300 border border-slate-200 dark:border-slate-700 transition flex items-center justify-between cursor-pointer"
              >
                <span>Dynamic Dijkstra Evac Route</span>
                <ChevronRight className="w-3.5 h-3.5 text-slate-400" />
              </button>
            </div>

          </div>

          <div className="pt-2 border-t border-slate-100 dark:border-slate-800 flex justify-between items-center text-[11px] text-slate-500 dark:text-slate-400 font-mono">
            <span>Canonical Intelligence Pipeline</span>
            <span className="text-emerald-700 dark:text-emerald-400 font-bold">READY</span>
          </div>

        </div>
      )}
    </div>
  );
}
