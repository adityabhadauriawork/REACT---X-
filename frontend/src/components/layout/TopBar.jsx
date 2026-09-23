import React, { useState, useEffect, useRef } from 'react';
import { 
  ShieldAlert, Search, Bell, User, LogOut, 
  ChevronDown, Satellite, Radio, CheckCircle2, 
  AlertTriangle, RefreshCw, Layers, ShieldCheck,
  Building2, MapPin, Sparkles, Sliders, Activity, Check
} from 'lucide-react';

const ROLE_LABELS = {
  HSE_COMMANDER: { title: 'Plant Operator / HSE', tier: 'Tier 1 — Facility', badge: 'bg-blue-100 text-blue-800 border-blue-200' },
  PLANT_MANAGER: { title: 'Plant Operations Manager', tier: 'Tier 1 — Facility', badge: 'bg-blue-100 text-blue-800 border-blue-200' },
  DISTRICT_AUTHORITY: { title: 'Regional Authority (GIDC)', tier: 'Tier 2 — Regional', badge: 'bg-teal-100 text-teal-800 border-teal-200' },
  EXECUTIVE_AUTHORITY: { title: 'National Command (NDMA)', tier: 'Tier 3 — National', badge: 'bg-indigo-100 text-indigo-800 border-indigo-200' },
  FIELD_RESPONDER: { title: 'Emergency / Public Safety (NDRF)', tier: 'Tier 4 — Tactical', badge: 'bg-amber-100 text-amber-800 border-amber-200' },
  DEMO_ADMIN: { title: 'System Administrator', tier: 'Full Access', badge: 'bg-purple-100 text-purple-800 border-purple-200' }
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
  const [searchQuery, setSearchQuery] = useState('');
  const [showSearchResults, setShowSearchResults] = useState(false);
  const [showRoleMenu, setShowRoleMenu] = useState(false);
  const [showHealthMenu, setShowHealthMenu] = useState(false);
  const [showUserMenu, setShowUserMenu] = useState(false);
  const [currentTime, setCurrentTime] = useState('');

  const searchRef = useRef(null);

  useEffect(() => {
    const timer = setInterval(() => {
      const d = new Date();
      setCurrentTime(d.toLocaleTimeString('en-US', { hour12: false }) + ' IST');
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  // Filter facilities and landmarks matching search query
  const searchResults = facilities.filter(f => 
    f.name?.toLowerCase().includes(searchQuery.toLowerCase()) ||
    f.id?.toLowerCase().includes(searchQuery.toLowerCase()) ||
    f.location?.toLowerCase().includes(searchQuery.toLowerCase()) ||
    f.primary_hazard?.toLowerCase().includes(searchQuery.toLowerCase())
  ).slice(0, 6);

  const activeFacility = facilities.find(f => f.id === selectedFacilityId) || facilities[0];
  const roleInfo = ROLE_LABELS[currentRole] || ROLE_LABELS.HSE_COMMANDER;

  return (
    <header className="bg-white border-b border-slate-200 px-4 py-2.5 flex items-center justify-between gap-4 sticky top-0 z-30 shadow-2xs">
      {/* Left: Brand Identity & Location Context */}
      <div className="flex items-center space-x-3 shrink-0">
        <div className="w-8 h-8 rounded-lg bg-blue-600 flex items-center justify-center text-white font-bold shadow-xs">
          <ShieldAlert className="w-4.5 h-4.5" />
        </div>
        
        <div>
          <div className="flex items-center space-x-2">
            <span className="font-extrabold text-sm tracking-tight text-slate-900">REACT-X</span>
            <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${roleInfo.badge}`}>
              {roleInfo.tier}
            </span>
          </div>
          
          {/* Facility Selector */}
          <div className="relative group">
            <select
              value={selectedFacilityId || (activeFacility?.id || '')}
              onChange={(e) => onSelectFacility && onSelectFacility(e.target.value)}
              className="text-xs font-semibold text-slate-700 bg-transparent hover:text-blue-600 cursor-pointer pr-4 focus:outline-none appearance-none"
            >
              {facilities.map(f => (
                <option key={f.id} value={f.id}>
                  {f.name} ({f.location || 'Gujarat'})
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
            className="w-full pl-9 pr-4 py-1.5 bg-slate-100 border border-slate-200 rounded-lg text-xs focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all text-slate-900"
          />
        </div>

        {/* Search Results Dropdown */}
        {showSearchResults && searchQuery.trim() !== '' && (
          <div className="absolute top-full mt-1.5 left-0 right-0 bg-white border border-slate-200 rounded-xl shadow-xl p-2 z-50 max-h-72 overflow-y-auto">
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
                  className="w-full text-left p-2 rounded-lg hover:bg-slate-50 flex items-center justify-between text-xs cursor-pointer"
                >
                  <div>
                    <div className="font-bold text-slate-900">{f.name}</div>
                    <div className="text-[11px] text-slate-500">{f.location} • {f.id}</div>
                  </div>
                  <span className="text-[10px] px-2 py-0.5 rounded bg-blue-50 text-blue-700 font-semibold border border-blue-200">
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

      {/* Right: Role Switcher, Freshness Status & User Profile */}
      <div className="flex items-center space-x-2.5 shrink-0 text-xs">
        
        {/* Mode Switcher to Demo Command Room */}
        {onSwitchToDemo && (
          <button
            onClick={onSwitchToDemo}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-amber-50 hover:bg-amber-100 text-amber-800 border border-amber-300 font-bold cursor-pointer transition-colors shadow-2xs"
            title="Open Controlled Replay Simulation Mode"
          >
            <Sliders className="w-3.5 h-3.5 text-amber-600" />
            <span className="hidden sm:inline">Demo Command Room</span>
          </button>
        )}

        {/* Live Satellite / OT Freshness Popover Trigger */}
        <div className="relative">
          <button
            onClick={() => setShowHealthMenu(!showHealthMenu)}
            className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-emerald-50 hover:bg-emerald-100 text-emerald-800 border border-emerald-200 font-semibold cursor-pointer transition-colors"
          >
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
            <span className="hidden sm:inline text-xs">SATELLITE: LIVE</span>
            <ChevronDown className="w-3.5 h-3.5" />
          </button>

          {showHealthMenu && (
            <div className="absolute right-0 top-full mt-1.5 w-72 bg-white border border-slate-200 rounded-xl shadow-xl p-3 z-50 space-y-2 text-xs">
              <div className="font-bold text-slate-900 pb-1 border-b border-slate-100 flex items-center justify-between">
                <span>National Feeds & Telemetry</span>
                <span className="text-emerald-600 font-semibold">Active</span>
              </div>
              
              <div className="space-y-1.5 text-[11px]">
                <div className="flex justify-between items-center text-slate-600">
                  <span className="flex items-center gap-1.5"><Satellite className="w-3.5 h-3.5 text-blue-600" /> NASA FIRMS VIIRS</span>
                  <span className="font-mono text-emerald-700 font-bold">LIVE</span>
                </div>
                <div className="flex justify-between items-center text-slate-600">
                  <span className="flex items-center gap-1.5"><Satellite className="w-3.5 h-3.5 text-indigo-600" /> ISRO MOSDAC INSAT</span>
                  <span className="font-mono text-emerald-700 font-bold">LIVE</span>
                </div>
                <div className="flex justify-between items-center text-slate-600">
                  <span className="flex items-center gap-1.5"><Satellite className="w-3.5 h-3.5 text-teal-600" /> Copernicus Sentinel-2</span>
                  <span className="font-mono text-slate-700 font-bold">LATEST PASS</span>
                </div>
                <div className="flex justify-between items-center text-slate-600">
                  <span className="flex items-center gap-1.5"><Satellite className="w-3.5 h-3.5 text-amber-600" /> USGS Landsat 8/9</span>
                  <span className="font-mono text-slate-700 font-bold">LATEST PASS</span>
                </div>
                <div className="flex justify-between items-center text-slate-600 pt-1 border-t border-slate-100">
                  <span className="flex items-center gap-1.5"><Radio className="w-3.5 h-3.5 text-amber-600" /> Plant OT Hardware</span>
                  <span className="font-mono text-amber-700 font-bold">STANDBY</span>
                </div>
                <div className="flex justify-between items-center text-slate-600">
                  <span className="flex items-center gap-1.5"><Activity className="w-3.5 h-3.5 text-blue-600" /> Predictive OT Inference</span>
                  <span className="font-mono text-amber-700 font-bold">AWAITING HARDWARE</span>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Role Switcher Dropdown */}
        <div className="relative">
          <button
            onClick={() => setShowRoleMenu(!showRoleMenu)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-800 font-semibold cursor-pointer transition-colors"
          >
            <User className="w-3.5 h-3.5 text-slate-600" />
            <span className="hidden lg:inline">{roleInfo.title}</span>
            <ChevronDown className="w-3.5 h-3.5 text-slate-500" />
          </button>

          {showRoleMenu && (
            <div className="absolute right-0 top-full mt-1.5 w-60 bg-white border border-slate-200 rounded-xl shadow-xl p-2 z-50 space-y-1">
              <div className="text-[10px] font-bold uppercase text-slate-400 px-2 py-1 border-b border-slate-100">
                Switch Operational Role Tier
              </div>
              {Object.entries(ROLE_LABELS).map(([key, item]) => (
                <button
                  key={key}
                  onClick={() => {
                    onRoleChange && onRoleChange(key);
                    setShowRoleMenu(false);
                  }}
                  className={`w-full text-left px-2.5 py-1.5 rounded-lg text-xs flex items-center justify-between cursor-pointer ${
                    currentRole === key ? 'bg-blue-50 text-blue-700 font-bold' : 'hover:bg-slate-50 text-slate-700'
                  }`}
                >
                  <div>
                    <div className="font-bold">{item.title}</div>
                    <div className="text-[10px] text-slate-400">{item.tier}</div>
                  </div>
                  {currentRole === key && <Check className="w-4 h-4 text-blue-600" />}
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Executive Brief Modal Trigger */}
        <button
          onClick={onOpenExecutiveBrief}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-700 text-white font-bold cursor-pointer transition-colors shadow-xs"
        >
          <Sparkles className="w-3.5 h-3.5" />
          <span className="hidden md:inline">Situation Brief</span>
        </button>

        {/* User Account / Logout */}
        <div className="relative">
          <button
            onClick={() => setShowUserMenu(!showUserMenu)}
            className="w-8 h-8 rounded-full bg-slate-200 hover:bg-slate-300 flex items-center justify-center text-slate-700 font-bold cursor-pointer transition"
          >
            {user?.name ? user.name.charAt(0) : 'U'}
          </button>

          {showUserMenu && (
            <div className="absolute right-0 top-full mt-1.5 w-48 bg-white border border-slate-200 rounded-xl shadow-xl p-2 z-50 space-y-1">
              <div className="px-2 py-1.5 border-b border-slate-100">
                <div className="font-bold text-slate-900 truncate">{user?.name || 'Operator'}</div>
                <div className="text-[10px] text-slate-500">{roleInfo.title}</div>
              </div>
              <button
                onClick={onLogout}
                className="w-full text-left px-2 py-1.5 rounded-lg text-red-600 hover:bg-red-50 flex items-center gap-2 cursor-pointer font-semibold"
              >
                <LogOut className="w-3.5 h-3.5" /> Logout
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
