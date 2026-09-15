import React, { useState, useRef, useEffect } from 'react';
import { 
  Sliders, Activity, Flame, Building2, 
  BarChart3, Satellite, LineChart, TrendingUp,
  ShieldAlert, AlertTriangle, ShieldCheck, 
  Navigation, Droplets, FileText, ChevronRight,
  Layers, Sparkles, X, Radio
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
        className="flex items-center gap-2 px-3.5 py-2 rounded-xl bg-white hover:bg-slate-50 text-slate-800 font-bold text-xs border border-slate-300 shadow-md cursor-pointer transition-all hover:border-blue-400"
      >
        <Sliders className="w-4 h-4 text-blue-600" />
        <span>TOOLS & COMMANDS</span>
        <span className="text-[10px] px-1.5 py-0.2 rounded bg-blue-50 text-blue-700 font-extrabold border border-blue-200">
          5 Categories
        </span>
      </button>

      {/* Floating Command Panel Dropdown */}
      {isOpen && (
        <div className="absolute left-0 top-full mt-2 w-[460px] bg-white border border-slate-200 rounded-2xl shadow-2xl p-4 z-50 text-xs space-y-4 animate-in fade-in slide-in-from-top-2 duration-150">
          
          <div className="flex items-center justify-between pb-2 border-b border-slate-100">
            <div>
              <h3 className="font-bold text-slate-900 text-sm">Industrial Intelligence Tools</h3>
              <p className="text-[11px] text-slate-500">Select an on-demand analysis or response workflow</p>
            </div>
            <button 
              onClick={() => setIsOpen(false)}
              className="p-1 rounded-lg hover:bg-slate-100 text-slate-400 hover:text-slate-700 cursor-pointer"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 max-h-[70vh] overflow-y-auto pr-1">
            
            {/* GROUP 1: MONITOR */}
            <div className="p-2.5 rounded-xl bg-slate-50 border border-slate-200 space-y-1.5">
              <div className="text-[10px] font-bold uppercase text-slate-500 flex items-center gap-1.5">
                <Activity className="w-3.5 h-3.5 text-blue-600" />
                <span>1. Monitor</span>
              </div>
              <div className="space-y-1">
                <button
                  onClick={() => handleToolClick('live_thermal')}
                  className="w-full text-left p-1.5 rounded-lg hover:bg-white text-slate-800 hover:text-blue-700 font-semibold text-[11px] flex items-center justify-between cursor-pointer transition-colors"
                >
                  <span>Live Thermal Events</span>
                  <ChevronRight className="w-3 h-3 text-slate-400" />
                </button>
                <button
                  onClick={() => handleToolClick('persistent_sources')}
                  className="w-full text-left p-1.5 rounded-lg hover:bg-white text-slate-800 hover:text-blue-700 font-semibold text-[11px] flex items-center justify-between cursor-pointer transition-colors"
                >
                  <span>Persistent Sources & Flares</span>
                  <ChevronRight className="w-3 h-3 text-slate-400" />
                </button>
                <button
                  onClick={() => handleToolClick('facility_status')}
                  className="w-full text-left p-1.5 rounded-lg hover:bg-white text-slate-800 hover:text-blue-700 font-semibold text-[11px] flex items-center justify-between cursor-pointer transition-colors"
                >
                  <span>Facility OT Sensor Status</span>
                  <ChevronRight className="w-3 h-3 text-slate-400" />
                </button>
              </div>
            </div>

            {/* GROUP 2: ANALYZE */}
            <div className="p-2.5 rounded-xl bg-slate-50 border border-slate-200 space-y-1.5">
              <div className="text-[10px] font-bold uppercase text-slate-500 flex items-center gap-1.5">
                <BarChart3 className="w-3.5 h-3.5 text-teal-600" />
                <span>2. Analyze</span>
              </div>
              <div className="space-y-1">
                <button
                  onClick={() => handleToolClick('source_classification')}
                  className="w-full text-left p-1.5 rounded-lg hover:bg-white text-slate-800 hover:text-teal-700 font-semibold text-[11px] flex items-center justify-between cursor-pointer transition-colors"
                >
                  <span>AI Thermal Classification</span>
                  <ChevronRight className="w-3 h-3 text-slate-400" />
                </button>
                <button
                  onClick={() => handleToolClick('historical_analysis')}
                  className="w-full text-left p-1.5 rounded-lg hover:bg-white text-slate-800 hover:text-teal-700 font-semibold text-[11px] flex items-center justify-between cursor-pointer transition-colors"
                >
                  <span>Historical Trend & Baselines</span>
                  <ChevronRight className="w-3 h-3 text-slate-400" />
                </button>
                <button
                  onClick={() => handleToolClick('satellite_comparison')}
                  className="w-full text-left p-1.5 rounded-lg hover:bg-white text-slate-800 hover:text-teal-700 font-semibold text-[11px] flex items-center justify-between cursor-pointer transition-colors"
                >
                  <span>Multi-Satellite Corroboration</span>
                  <ChevronRight className="w-3 h-3 text-slate-400" />
                </button>
              </div>
            </div>

            {/* GROUP 3: PREDICT */}
            <div className="p-2.5 rounded-xl bg-slate-50 border border-slate-200 space-y-1.5">
              <div className="text-[10px] font-bold uppercase text-slate-500 flex items-center gap-1.5">
                <TrendingUp className="w-3.5 h-3.5 text-indigo-600" />
                <span>3. Predict</span>
              </div>
              <div className="space-y-1">
                <button
                  onClick={() => handleToolClick('hazard_prediction')}
                  className="w-full text-left p-1.5 rounded-lg hover:bg-white text-slate-800 hover:text-indigo-700 font-semibold text-[11px] flex items-center justify-between cursor-pointer transition-colors"
                >
                  <span>Gaussian Plume Dispersion</span>
                  <ChevronRight className="w-3 h-3 text-slate-400" />
                </button>
                <button
                  onClick={() => handleToolClick('preventive_whatif')}
                  className="w-full text-left p-1.5 rounded-lg hover:bg-white text-slate-800 hover:text-indigo-700 font-semibold text-[11px] flex items-center justify-between cursor-pointer transition-colors"
                >
                  <span>Preventive What-If Lab</span>
                  <ChevronRight className="w-3 h-3 text-slate-400" />
                </button>
                <button
                  onClick={() => handleToolClick('trend_analysis')}
                  className="w-full text-left p-1.5 rounded-lg hover:bg-white text-slate-800 hover:text-indigo-700 font-semibold text-[11px] flex items-center justify-between cursor-pointer transition-colors"
                >
                  <span>Early Warning Sensor Matrix</span>
                  <ChevronRight className="w-3 h-3 text-slate-400" />
                </button>
              </div>
            </div>

            {/* GROUP 4: ASSESS */}
            <div className="p-2.5 rounded-xl bg-slate-50 border border-slate-200 space-y-1.5">
              <div className="text-[10px] font-bold uppercase text-slate-500 flex items-center gap-1.5">
                <ShieldAlert className="w-3.5 h-3.5 text-amber-600" />
                <span>4. Assess</span>
              </div>
              <div className="space-y-1">
                <button
                  onClick={() => handleToolClick('domino_risk')}
                  className="w-full text-left p-1.5 rounded-lg hover:bg-white text-slate-800 hover:text-amber-700 font-semibold text-[11px] flex items-center justify-between cursor-pointer transition-colors"
                >
                  <span>Domino Risk & Escalation Graph</span>
                  <ChevronRight className="w-3 h-3 text-slate-400" />
                </button>
                <button
                  onClick={() => handleToolClick('impact_zones')}
                  className="w-full text-left p-1.5 rounded-lg hover:bg-white text-slate-800 hover:text-amber-700 font-semibold text-[11px] flex items-center justify-between cursor-pointer transition-colors"
                >
                  <span>ERPG Impact & Receptor Matrix</span>
                  <ChevronRight className="w-3 h-3 text-slate-400" />
                </button>
              </div>
            </div>

            {/* GROUP 5: RESPOND */}
            <div className="p-2.5 rounded-xl bg-slate-50 border border-slate-200 space-y-1.5 sm:col-span-2">
              <div className="text-[10px] font-bold uppercase text-slate-500 flex items-center gap-1.5">
                <Navigation className="w-3.5 h-3.5 text-rose-600" />
                <span>5. Respond & Plan</span>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
                <button
                  onClick={() => handleToolClick('evacuation_support')}
                  className="text-left p-2 rounded-lg bg-white hover:bg-rose-50 text-slate-800 hover:text-rose-700 font-semibold text-[11px] border border-slate-200 hover:border-rose-200 flex items-center justify-between cursor-pointer transition-all"
                >
                  <span>Safe Evacuation</span>
                  <ChevronRight className="w-3 h-3 text-slate-400" />
                </button>
                <button
                  onClick={() => handleToolClick('resource_allocation')}
                  className="text-left p-2 rounded-lg bg-white hover:bg-rose-50 text-slate-800 hover:text-rose-700 font-semibold text-[11px] border border-slate-200 hover:border-rose-200 flex items-center justify-between cursor-pointer transition-all"
                >
                  <span>Resource Tactics</span>
                  <ChevronRight className="w-3 h-3 text-slate-400" />
                </button>
                <button
                  onClick={() => handleToolClick('preplan_pdf')}
                  className="text-left p-2 rounded-lg bg-white hover:bg-rose-50 text-slate-800 hover:text-rose-700 font-semibold text-[11px] border border-slate-200 hover:border-rose-200 flex items-center justify-between cursor-pointer transition-all"
                >
                  <span>ERDMP Pre-Plan PDF</span>
                  <ChevronRight className="w-3 h-3 text-slate-400" />
                </button>
              </div>
            </div>

          </div>
        </div>
      )}
    </div>
  );
}
