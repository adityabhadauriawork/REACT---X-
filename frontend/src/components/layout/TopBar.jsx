import React, { useState, useEffect, useRef } from 'react';
import { 
  ShieldAlert, Search, Bell, User, LogOut, 
  ChevronDown, Satellite, Radio, CheckCircle2, 
  AlertTriangle, RefreshCw, Layers, ShieldCheck,
  Building2, MapPin, Sparkles, Sliders, Activity, Check,
  Sun, Moon
} from 'lucide-react';
import { useTheme } from '../../context/ThemeContext';

const ROLE_LABELS = {
  HSE_COMMANDER: { title: 'Plant Operator / HSE', tier: 'Tier 1 — Facility', badge: 'bg-blue-100 dark:bg-blue-900/60 text-blue-800 dark:text-blue-300 border-blue-200 dark:border-blue-800' },
  PLANT_MANAGER: { title: 'Plant Operations Manager', tier: 'Tier 1 — Facility', badge: 'bg-blue-100 dark:bg-blue-900/60 text-blue-800 dark:text-blue-300 border-blue-200 dark:border-blue-800' },
  DISTRICT_AUTHORITY: { title: 'Regional Authority (GIDC)', tier: 'Tier 2 — Regional', badge: 'bg-teal-100 dark:bg-teal-900/60 text-teal-800 dark:text-teal-300 border-teal-200 dark:border-teal-800' },
  EXECUTIVE_AUTHORITY: { title: 'National Command (NDMA)', tier: 'Tier 3 — National', badge: 'bg-indigo-100 dark:bg-indigo-900/60 text-indigo-800 dark:text-indigo-300 border-indigo-200 dark:border-indigo-800' },
  FIELD_RESPONDER: { title: 'Emergency / Public Safety (NDRF)', tier: 'Tier 4 — Tactical', badge: 'bg-amber-100 dark:bg-amber-900/60 text-amber-800 dark:text-amber-300 border-amber-200 dark:border-amber-800' },
  DEMO_ADMIN: { title: 'System Administrator', tier: 'Full Access', badge: 'bg-purple-100 dark:bg-purple-900/60 text-purple-800 dark:text-purple-300 border-purple-200 dark:border-purple-800' }
};

export default function TopBar({
  user,
  currentRole,
  onRoleChange,
  facilities = [],
  selectedFacilityId,
  onSelectFacility,
  onSearchSelect,
  onLogout,
  onOpenExecutiveBrief,
  onSwitchToDemo,
  liveTelemetry
}) {
  const { theme, toggleTheme, isDark } = useTheme();
  const [searchQuery, setSearchQuery] = useState('');
  const [showSearchResults, setShowSearchResults] = useState(false);
  const [showRoleMenu, setShowRoleMenu] = useState(false);
  const [currentTime, setCurrentTime] = useState('');

  const searchRef = useRef(null);

  useEffect(() => {
    const timer = setInterval(() => {
      const d = new Date();
      setCurrentTime(d.toLocaleTimeString('en-US', { hour12: false }) + ' IST');
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  // Filter facilities matching search query
  const searchResults = facilities.filter(f => 
    f.name?.toLowerCase().includes(searchQuery.toLowerCase()) ||
    f.id?.toLowerCase().includes(searchQuery.toLowerCase()) ||
    f.location?.toLowerCase().includes(searchQuery.toLowerCase()) ||
    f.primary_hazard?.toLowerCase().includes(searchQuery.toLowerCase())
  ).slice(0, 6);

  const activeFacility = facilities.find(f => f.id === selectedFacilityId) || facilities[0];
  const roleInfo = ROLE_LABELS[currentRole] || ROLE_LABELS.HSE_COMMANDER;

  return (
    <header className="bg-white dark:bg-slate-900 border-b border-slate-200 dark:border-slate-800 px-4 py-2.5 flex items-center justify-between gap-4 sticky top-0 z-30 shadow-2xs transition-colors">
      {/* Left: Brand Identity & Facility Context */}
      <div className="flex items-center space-x-3 shrink-0">
        <div className="w-8 h-8 rounded-lg bg-blue-600 flex items-center justify-center text-white font-bold shadow-xs">
          <ShieldAlert className="w-4.5 h-4.5" />
        </div>
        
        <div>
          <div className="flex items-center space-x-2">
            <span className="font-extrabold text-sm tracking-tight text-slate-900 dark:text-slate-100">REACT-X</span>
            <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-blue-50 dark:bg-blue-950/60 text-blue-700 dark:text-blue-300 border border-blue-200 dark:border-blue-800 uppercase tracking-wider">
              INDIA OPERATIONS
            </span>
            <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${roleInfo.badge}`}>
              {roleInfo.tier}
            </span>
          </div>
          
          {/* Facility Selector */}
          <div className="relative group">
            <select
              value={selectedFacilityId || (activeFacility?.id || '')}
              onChange={(e) => onSelectFacility && onSelectFacility(e.target.value)}
              className="text-xs font-semibold text-slate-700 dark:text-slate-300 bg-transparent hover:text-blue-600 dark:hover:text-blue-400 cursor-pointer pr-4 focus:outline-none appearance-none"
            >
              {facilities.map(f => (
                <option key={f.id} value={f.id} className="bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100">
                  {f.name} ({f.location || 'India'})
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* Center: Global Search Bar */}
      <div ref={searchRef} className="relative flex-1 max-w-md hidden md:block">
        <div className="relative">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
          <input
            type="text"
            placeholder="Search industrial facility, thermal cluster, asset, or chemical..."
            value={searchQuery}
            onChange={(e) => {
              setSearchQuery(e.target.value);
              setShowSearchResults(true);
            }}
            onFocus={() => setShowSearchResults(true)}
            className="w-full pl-9 pr-4 py-1.5 bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg text-xs focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all text-slate-900 dark:text-slate-100 placeholder-slate-400"
          />
        </div>

        {/* Search Results Dropdown */}
        {showSearchResults && searchQuery.trim() !== '' && (
          <div className="absolute top-full mt-1.5 left-0 right-0 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl shadow-xl p-2 z-50 max-h-72 overflow-y-auto">
            <div className="text-[10px] font-bold uppercase text-slate-400 px-2 py-1">Facilities & Corridors</div>
            {searchResults.length > 0 ? (
              searchResults.map((f) => (
                <button
                  key={f.id}
                  onClick={() => {
                    onSearchSelect && onSearchSelect(f);
                    setShowSearchResults(false);
                    setSearchQuery('');
                  }}
                  className="w-full text-left p-2 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-800 flex items-center justify-between text-xs cursor-pointer"
                >
                  <div>
                    <div className="font-bold text-slate-900 dark:text-slate-100">{f.name}</div>
                    <div className="text-[11px] text-slate-500 dark:text-slate-400">{f.location} • {f.id}</div>
                  </div>
                  <span className="text-[10px] px-2 py-0.5 rounded bg-blue-50 dark:bg-blue-950/60 text-blue-700 dark:text-blue-300 font-semibold border border-blue-200 dark:border-blue-800">
                    Jump to Map
                  </span>
                </button>
              ))
            ) : (
              <div className="text-xs text-slate-500 p-2 text-center">No matching facilities found.</div>
            )}
          </div>
        )}
      </div>

      {/* Right: Theme Toggle, Mode Switcher & User Profile */}
      <div className="flex items-center space-x-2.5 shrink-0 text-xs">
        
        {/* Global Light / Dark Mode Toggle */}
        <button
          onClick={toggleTheme}
          className="p-1.5 rounded-lg bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-200 border border-slate-200 dark:border-slate-700 cursor-pointer transition shadow-2xs"
          title={`Switch to ${isDark ? 'Light' : 'Dark'} Mode`}
        >
          {isDark ? <Sun className="w-4 h-4 text-amber-400" /> : <Moon className="w-4 h-4 text-slate-600" />}
        </button>

        {/* Mode Switcher to Demo Command Room */}
        {onSwitchToDemo && (
          <button
            onClick={onSwitchToDemo}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-amber-50 dark:bg-amber-950/50 hover:bg-amber-100 dark:hover:bg-amber-900/60 text-amber-800 dark:text-amber-300 border border-amber-300 dark:border-amber-700 font-bold cursor-pointer transition-colors shadow-2xs"
            title="Open Demo Replay Mode"
          >
            <Sliders className="w-3.5 h-3.5 text-amber-600 dark:text-amber-400" />
            <span>Demo Replay • Reference</span>
          </button>
        )}

        {/* Executive Situation Brief Button */}
        {onOpenExecutiveBrief && (
          <button
            onClick={onOpenExecutiveBrief}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-800 dark:text-slate-200 font-bold border border-slate-200 dark:border-slate-700 cursor-pointer transition shadow-2xs"
          >
            <Sparkles className="w-3.5 h-3.5 text-blue-600 dark:text-blue-400" />
            <span className="hidden sm:inline">Executive Brief</span>
          </button>
        )}

        {/* Role Menu */}
        <div className="relative">
          <button
            onClick={() => setShowRoleMenu(!showRoleMenu)}
            className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-200 cursor-pointer font-semibold"
          >
            <User className="w-3.5 h-3.5 text-slate-500" />
            <span className="max-w-[120px] truncate">{roleInfo.title}</span>
            <ChevronDown className="w-3 h-3 text-slate-400" />
          </button>

          {showRoleMenu && (
            <div className="absolute right-0 top-full mt-1.5 w-60 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl shadow-xl p-1.5 z-50">
              <div className="text-[10px] font-bold text-slate-400 uppercase px-2 py-1">Select Persona</div>
              {Object.entries(ROLE_LABELS).map(([roleKey, info]) => (
                <button
                  key={roleKey}
                  onClick={() => {
                    onRoleChange && onRoleChange(roleKey);
                    setShowRoleMenu(false);
                  }}
                  className={`w-full text-left px-2.5 py-1.5 rounded-lg text-xs flex items-center justify-between cursor-pointer ${
                    currentRole === roleKey
                      ? 'bg-blue-50 dark:bg-blue-950/60 text-blue-700 dark:text-blue-300 font-bold'
                      : 'hover:bg-slate-50 dark:hover:bg-slate-800 text-slate-700 dark:text-slate-300'
                  }`}
                >
                  <div>
                    <div>{info.title}</div>
                    <div className="text-[10px] text-slate-400">{info.tier}</div>
                  </div>
                  {currentRole === roleKey && <Check className="w-3.5 h-3.5 text-blue-600 dark:text-blue-400" />}
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Logout */}
        {onLogout && (
          <button
            onClick={onLogout}
            className="p-1.5 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 cursor-pointer"
            title="Log Out"
          >
            <LogOut className="w-4 h-4" />
          </button>
        )}

      </div>
    </header>
  );
}
