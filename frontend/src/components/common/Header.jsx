import React, { useState, useEffect } from 'react';
import { 
  ShieldAlert, Radio, Wind, Thermometer, Clock, 
  FileText, Play, RefreshCw, AlertTriangle, CheckCircle2, 
  CloudSun, Info, ChevronDown, ChevronUp, UserCheck, Shield, Sparkles,
  Satellite, Database, AlertCircle 
} from 'lucide-react';

export default function Header({ 
  plantInfo, 
  globalSystemState,
  activeSimulation, 
  impactResult, 
  activeWeather, 
  liveTelemetry,
  isLiveData = false,
  currentRole = 'HSE_COMMANDER',
  onRoleChange,
  onOpenExecutiveBrief,
  onRefreshWeather,
  isRefreshingWeather,
  onLoadPrimaryDemo, 
  onExportPDF, 
  isExporting,
  loading 
}) {
  const [timeStr, setTimeStr] = useState('');
  const [showWeatherDetails, setShowWeatherDetails] = useState(false);

  useEffect(() => {
    const updateTime = () => {
      const now = new Date();
      setTimeStr(now.toLocaleTimeString('en-US', { hour12: false }) + ' IST');
    };
    updateTime();
    const interval = setInterval(updateTime, 1000);
    return () => clearInterval(interval);
  }, []);

  const stateObj = globalSystemState || {
    state: activeSimulation ? 'INCIDENT_ACTIVE' : 'NORMAL',
    label: activeSimulation ? 'INCIDENT ACTIVE' : 'NORMAL',
    badgeClass: activeSimulation ? 'bg-red-500/20 text-red-300 border-red-500/60' : 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30',
    color: activeSimulation ? '#ef4444' : '#10b981'
  };

  const isLiveWeather = activeWeather?.mode === 'LIVE';
  const weatherSource = activeWeather?.source || (isLiveWeather ? 'Open-Meteo' : 'Scenario Override');

  return (
    <header className="border-b border-slate-800/90 bg-[#090d16]/95 backdrop-blur-md px-4 py-2 sticky top-0 z-50">
      <div className="max-w-[1920px] mx-auto flex flex-wrap items-center justify-between gap-3">
        
        {/* Left: Product Identity & Facility Context */}
        <div className="flex items-center space-x-3">
          <div className="relative">
            <div className={`p-2 rounded-lg border transition-all ${
              stateObj.state === 'INCIDENT_ACTIVE' || stateObj.state === 'CRITICAL'
                ? 'bg-red-950/60 border-red-500/60' 
                : (stateObj.state === 'ABNORMAL' ? 'bg-amber-950/60 border-amber-500/60' : 'bg-cyan-950/40 border-cyan-500/40')
            }`}>
              <ShieldAlert className={`w-4 h-4 ${
                stateObj.state === 'INCIDENT_ACTIVE' || stateObj.state === 'CRITICAL' 
                  ? 'text-red-400 animate-pulse' 
                  : (stateObj.state === 'ABNORMAL' ? 'text-amber-400' : 'text-cyan-400')
              }`} />
            </div>
            <span className="absolute -bottom-0.5 -right-0.5 flex h-2 w-2">
              <span className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 ${
                stateObj.state === 'INCIDENT_ACTIVE' || stateObj.state === 'CRITICAL' ? 'bg-red-400' : 'bg-emerald-400'
              }`} />
              <span className={`relative inline-flex rounded-full h-2 w-2 ${
                stateObj.state === 'INCIDENT_ACTIVE' || stateObj.state === 'CRITICAL' ? 'bg-red-500' : 'bg-emerald-500'
              }`} />
            </span>
          </div>

          <div>
            <div className="flex items-center space-x-2">
              <span className="font-mono text-[10px] px-2 py-0.5 rounded bg-cyan-500/10 text-cyan-400 font-extrabold border border-cyan-500/30">
                REACT-X
              </span>
              <h1 className="text-xs md:text-sm font-extrabold tracking-tight text-white uppercase flex items-center gap-1.5 font-mono">
                Industrial Hazard Intelligence
              </h1>
            </div>
            <p className="text-[10px] text-slate-400 font-mono">
              {plantInfo?.name || 'PetroChem Complex Alpha'} • <span className="text-slate-500">{plantInfo?.location || 'Dahej PCPIR, Gujarat'}</span>
            </p>
          </div>
        </div>

        {/* Center: System Status & Data Provenance */}
        <div className="flex items-center space-x-2.5">
          
          {/* Authoritative Global System State Badge */}
          <div className="flex items-center space-x-2 bg-slate-900/90 px-3 py-1 rounded-lg border border-slate-800 font-mono text-xs">
            <span className="text-[10px] text-slate-400 font-bold">STATE:</span>
            <span className={`px-2 py-0.5 rounded text-[10px] font-black uppercase tracking-wider border ${stateObj.badgeClass}`}>
              {stateObj.label}
            </span>
          </div>

          {/* Explicit Data Provenance Badge (Live vs Demo) */}
          <div className="flex items-center space-x-1.5 bg-slate-900/90 px-2.5 py-1 rounded-lg border border-slate-800 font-mono text-xs">
            <Database className="w-3.5 h-3.5 text-slate-400" />
            <span className={`px-1.5 py-0.2 rounded text-[9px] font-black uppercase tracking-wider border ${
              isLiveData 
                ? 'bg-cyan-500/20 text-cyan-300 border-cyan-500/50 animate-pulse' 
                : 'bg-amber-500/20 text-amber-300 border-amber-500/50'
            }`}>
              {isLiveData ? 'LIVE NASA FIRMS' : 'DEMO / SIMULATION'}
            </span>
          </div>

          {/* Meteorological Feed Pill */}
          <div className="relative">
            <button
              type="button"
              onClick={() => setShowWeatherDetails(!showWeatherDetails)}
              className="flex items-center space-x-2 bg-slate-900/90 hover:bg-slate-800 px-3 py-1 rounded-lg border border-slate-800 transition-all font-mono text-xs"
              title="Meteorological Conditions"
            >
              <div className="flex items-center space-x-1 text-slate-300">
                <Wind className="w-3.5 h-3.5 text-cyan-400" />
                <span className="font-bold">{activeWeather?.wind_speed_kmh} km/h</span>
                <span className="text-[10px] text-slate-400 font-semibold">{activeWeather?.wind_direction_cardinal}</span>
              </div>
              
              <span className="text-slate-600">|</span>
              
              <div className="flex items-center space-x-1 text-slate-300">
                <Thermometer className="w-3.5 h-3.5 text-amber-400" />
                <span className="font-bold">{activeWeather?.temperature_c}°C</span>
              </div>

              {showWeatherDetails ? <ChevronUp className="w-3 h-3 text-slate-400" /> : <ChevronDown className="w-3 h-3 text-slate-400" />}
            </button>

            {/* Weather Dropdown */}
            {showWeatherDetails && (
              <div className="absolute right-0 mt-1 w-64 bg-slate-900 border border-slate-800 rounded-xl p-3 shadow-2xl font-mono text-xs z-50 space-y-2">
                <div className="flex justify-between items-center border-b border-slate-800 pb-1.5 text-[10px]">
                  <span className="text-slate-400 font-bold uppercase">Meteorological Telemetry</span>
                  <span className={`px-1.5 py-0.2 rounded font-bold border ${isLiveWeather ? 'bg-cyan-500/20 text-cyan-300 border-cyan-500/40' : 'bg-amber-500/20 text-amber-300 border-amber-500/40'}`}>
                    {isLiveWeather ? 'OPEN-METEO LIVE' : 'SCENARIO OVERRIDE'}
                  </span>
                </div>
                <div className="space-y-1 text-[11px] text-slate-300">
                  <div className="flex justify-between">
                    <span className="text-slate-400">Wind Direction:</span>
                    <b>{activeWeather?.wind_direction_deg}° ({activeWeather?.wind_direction_cardinal})</b>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">Wind Velocity:</span>
                    <b>{activeWeather?.wind_speed_kmh} km/h ({(activeWeather?.wind_speed_kmh / 3.6).toFixed(2)} m/s)</b>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">Stability Class:</span>
                    <b>Pasquill-{activeWeather?.atmospheric_stability || 'D'}</b>
                  </div>
                </div>
                {onRefreshWeather && (
                  <button
                    type="button"
                    onClick={onRefreshWeather}
                    disabled={isRefreshingWeather}
                    className="w-full mt-1 bg-slate-800 hover:bg-slate-700 text-cyan-300 py-1 rounded text-[10px] font-bold border border-slate-700 flex items-center justify-center space-x-1"
                  >
                    <RefreshCw className={`w-3 h-3 ${isRefreshingWeather ? 'animate-spin' : ''}`} />
                    <span>Sync Live Weather Feed</span>
                  </button>
                )}
              </div>
            )}
          </div>

        </div>

        {/* Right: Operational Controls & Role View Selector */}
        <div className="flex items-center space-x-2">
          
          {/* Executive Situation Brief Trigger */}
          {onOpenExecutiveBrief && (
            <button
              type="button"
              onClick={onOpenExecutiveBrief}
              className="flex items-center space-x-1.5 px-2.5 py-1.5 bg-slate-900 hover:bg-slate-800 text-indigo-300 border border-indigo-500/30 rounded-lg text-xs font-bold font-mono transition-all"
              title="Open Executive Situation Brief Modal"
            >
              <Sparkles className="w-3.5 h-3.5 text-indigo-400" />
              <span className="hidden sm:inline">Executive Brief</span>
            </button>
          )}

          {/* Fire Pre-Plan PDF Export */}
          {onExportPDF && (
            <button
              type="button"
              onClick={onExportPDF}
              disabled={isExporting}
              className="flex items-center space-x-1.5 px-2.5 py-1.5 bg-slate-900 hover:bg-slate-800 text-slate-200 border border-slate-700 rounded-lg text-xs font-bold font-mono transition-all"
              title="Download Compliance Fire Pre-Plan Document"
            >
              <FileText className="w-3.5 h-3.5 text-slate-400" />
              <span className="hidden sm:inline">{isExporting ? 'Exporting...' : 'Pre-Plan PDF'}</span>
            </button>
          )}

          {/* Role View Switcher Dropdown */}
          <div className="flex items-center space-x-1.5 bg-slate-900 px-2 py-1 rounded-lg border border-slate-800">
            <UserCheck className="w-3.5 h-3.5 text-cyan-400 shrink-0" />
            <select
              value={currentRole}
              onChange={(e) => onRoleChange && onRoleChange(e.target.value)}
              className="bg-transparent text-white font-mono text-xs font-bold focus:outline-none cursor-pointer pr-1"
            >
              <option value="HSE_COMMANDER" className="bg-slate-900 text-white">HSE Incident Commander</option>
              <option value="FIELD_RESPONDER" className="bg-slate-900 text-white">Field Responder</option>
              <option value="PLANT_MANAGER" className="bg-slate-900 text-white">Plant General Manager</option>
              <option value="DISTRICT_AUTHORITY" className="bg-slate-900 text-white">District Emergency Authority</option>
              <option value="EXECUTIVE_AUTHORITY" className="bg-slate-900 text-white">Executive Authority (NDMA/PESO)</option>
              <option value="DEMO_ADMIN" className="bg-slate-900 text-white">Demo & Inspection Admin</option>
            </select>
          </div>

        </div>

      </div>
    </header>
  );
}
