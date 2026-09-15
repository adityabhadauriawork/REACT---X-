import React, { useState, useEffect, useRef } from 'react';
import { 
  ShieldAlert, Search, Bell, User, LogOut, 
  ChevronDown, Satellite, Radio, CheckCircle2, 
  AlertTriangle, RefreshCw, Layers, ShieldCheck,
  Building2, MapPin, Sparkles, Sliders
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
            {user?.isDemo && (
              <span className="text-[10px] font-bold px-1.5 py-0.2 rounded bg-amber-50 text-amber-700 border border-amber-200">
                Demo
              </span>
            )}
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
            value={searchQuery}
            onChange={(e) => {
              setSearchQuery(e.target.value);
              setShowSearchResults(true);
            }}
            onFocus={() => setShowSearchResults(true)}
            placeholder="Search facility, coordinates, incident ID (e.g. Dahej, Jamnagar, INC-01)..."
            className="w-full pl-9 pr-4 py-1.5 bg-slate-50 border border-slate-200 rounded-lg text-xs text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:bg-white transition-all"
          />
        </div>

        {/* Search Results Dropdown */}
        {showSearchResults && searchQuery.trim().length > 0 && (
          <div className="absolute left-0 right-0 top-full mt-1.5 bg-white border border-slate-200 rounded-xl shadow-lg p-2 z-50 space-y-1">
            <div className="text-[10px] font-bold uppercase text-slate-400 px-2 py-1">
              Matching Facilities & Locations ({searchResults.length})
            </div>
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
        
        {/* Live Satellite / OT Freshness Popover Trigger */}
        <div className="relative">
          <button
            onClick={() => setShowHealthMenu(!showHealthMenu)}
            className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-emerald-50 hover:bg-emerald-100 text-emerald-800 border border-emerald-200 font-semibold cursor-pointer transition-colors"
          >
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
            <span className="hidden sm:inline text-xs">FEEDS: LIVE</span>
            <ChevronDown className="w-3.5 h-3.5" />
          </button>

          {showHealthMenu && (
            <div className="absolute right-0 top-full mt-1.5 w-64 bg-white border border-slate-200 rounded-xl shadow-xl p-3 z-50 space-y-2 text-xs">
              <div className="font-bold text-slate-900 pb-1 border-b border-slate-100 flex items-center justify-between">
                <span>Data Freshness & Integrity</span>
                <span className="text-emerald-600 font-semibold">All Healthy</span>
              </div>
              
              <div className="space-y-1.5 text-[11px]">
                <div className="flex justify-between items-center text-slate-600">
                  <span className="flex items-center gap-1.5"><Satellite className="w-3.5 h-3.5 text-blue-600" /> NASA FIRMS VIIRS</span>
                  <span className="font-mono text-emerald-700 font-bold">LIVE — 4 min</span>
                </div>
                <div className="flex justify-between items-center text-slate-600">
                  <span className="flex items-center gap-1.5"><Satellite className="w-3.5 h-3.5 text-indigo-600" /> MOSDAC INSAT-3DR</span>
                  <span className="font-mono text-emerald-700 font-bold">LIVE — 9 min</span>
                </div>
                <div className="flex justify-between items-center text-slate-600">
                  <span className="flex items-center gap-1.5"><Satellite className="w-3.5 h-3.5 text-teal-600" /> Copernicus Sentinel-2</span>
                  <span className="font-mono text-slate-700 font-bold">LATEST — 1.2d</span>
                </div>
                <div className="flex justify-between items-center text-slate-600">
                  <span className="flex items-center gap-1.5"><Satellite className="w-3.5 h-3.5 text-amber-600" /> USGS Landsat 8/9</span>
                  <span className="font-mono text-slate-700 font-bold">LATEST — 4d</span>
                </div>
                <div className="flex justify-between items-center text-slate-600">
                  <span className="flex items-center gap-1.5"><Radio className="w-3.5 h-3.5 text-rose-600" /> Industrial OT Telemetry</span>
                  <span className="font-mono text-emerald-700 font-bold">24/24 Sensors</span>
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
                    <div>{item.title}</div>
                    <div className="text-[10px] text-slate-400 font-normal">{item.tier}</div>
                  </div>
                  {currentRole === key && <CheckCircle2 className="w-4 h-4 text-blue-600" />}
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Executive Situation Brief Button */}
        <button
          onClick={onOpenExecutiveBrief}
          className="hidden sm:flex items-center gap-1 px-3 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-700 text-white font-semibold cursor-pointer shadow-xs transition-colors"
        >
          <Sparkles className="w-3.5 h-3.5" />
          <span>Executive Brief</span>
        </button>

        {/* User Menu / Logout */}
        <div className="relative">
          <button
            onClick={() => setShowUserMenu(!showUserMenu)}
            className="p-1.5 rounded-lg hover:bg-slate-100 text-slate-600 cursor-pointer transition-colors"
            title="User Settings"
          >
            <LogOut className="w-4 h-4" onClick={onLogout} />
          </button>
        </div>
      </div>
    </header>
  );
}
