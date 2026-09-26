import React, { useState } from 'react';
import { 
   ShieldAlert, Satellite, Flame, Building2, 
   ArrowRight, ShieldCheck, Lock, Mail, User, 
   Sparkles, CheckCircle2, ChevronRight, Activity,
   Layers, Radio, AlertTriangle, Sun, Moon, Eye, EyeOff
 } from 'lucide-react';
import { useTheme } from '../context/ThemeContext';

export const DEMO_ROLES = [
  {
    tier: 'Tier 1',
    name: 'Plant Operator / HSE',
    roleKey: 'HSE_COMMANDER',
    email: 'operator@dahej-petro.in',
    password: 'demo_password',
    facility: 'PetroChem Complex Alpha (Dahej PCPIR)',
    scope: 'Single Facility & Real-time OT Telemetry',
    color: 'border-blue-200 dark:border-blue-800 hover:border-blue-400 dark:hover:border-blue-600 bg-blue-50/50 dark:bg-blue-950/30',
    badge: 'bg-blue-100 dark:bg-blue-900/60 text-blue-800 dark:text-blue-300'
  },
  {
    tier: 'Tier 2',
    name: 'Regional Authority (GIDC)',
    roleKey: 'DISTRICT_AUTHORITY',
    email: 'inspector@gidc-gujarat.gov.in',
    password: 'demo_password',
    facility: 'Gujarat GIDC Industrial Corridors',
    scope: 'Multi-Facility Cluster Surveillance',
    color: 'border-teal-200 dark:border-teal-800 hover:border-teal-400 dark:hover:border-teal-600 bg-teal-50/50 dark:bg-teal-950/30',
    badge: 'bg-teal-100 dark:bg-teal-900/60 text-teal-800 dark:text-teal-300'
  },
  {
    tier: 'Tier 3',
    name: 'National Command (NDMA)',
    roleKey: 'EXECUTIVE_AUTHORITY',
    email: 'commander@ndma-thermal.gov.in',
    password: 'demo_password',
    facility: 'Pan-India Petrochemical & Refinery Grid',
    scope: 'National Thermal Intelligence & Trends',
    color: 'border-indigo-200 dark:border-indigo-800 hover:border-indigo-400 dark:hover:border-indigo-600 bg-indigo-50/50 dark:bg-indigo-950/30',
    badge: 'bg-indigo-100 dark:bg-indigo-900/60 text-indigo-800 dark:text-indigo-300'
  },
  {
    tier: 'Tier 4',
    name: 'Emergency / Public Safety (NDRF)',
    roleKey: 'FIELD_RESPONDER',
    email: 'response@ndrf-fire.gov.in',
    password: 'demo_password',
    facility: 'District Emergency Operations Center',
    scope: 'Triage, Evacuation & Incident Response',
    color: 'border-amber-200 dark:border-amber-800 hover:border-amber-400 dark:hover:border-amber-600 bg-amber-50/50 dark:bg-amber-950/30',
    badge: 'bg-amber-100 dark:bg-amber-900/60 text-amber-800 dark:text-amber-300'
  }
];

export default function AuthLanding({ onLoginSuccess }) {
  const { theme, toggleTheme, isDark } = useTheme();
  const [isSignUp, setIsSignUp] = useState(false);
  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [selectedRole, setSelectedRole] = useState('HSE_COMMANDER');
  const [organization, setOrganization] = useState('');
  const [errorMessage, setErrorMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const handleManualSubmit = (e) => {
    e.preventDefault();
    if (!email || !password) {
      setErrorMessage('Please provide both User ID / Email and Password.');
      return;
    }
    if (isSignUp && !fullName) {
      setErrorMessage('Please provide your full name for authority provisioning.');
      return;
    }
    setErrorMessage('');
    setIsLoading(true);

    setTimeout(() => {
      setIsLoading(false);
      onLoginSuccess({
        email,
        role: selectedRole,
        isDemo: false,
        name: isSignUp ? fullName : (email.split('@')[0].replace('.', ' ').toUpperCase()),
        organization: organization || (isSignUp ? 'Industrial Authority' : undefined)
      });
    }, 400);
  };

  const handleDemoQuickLogin = (demo) => {
    setEmail(demo.email);
    setPassword(demo.password);
    setSelectedRole(demo.roleKey);
    onLoginSuccess({
      email: demo.email,
      role: demo.roleKey,
      isDemo: true,
      name: demo.name,
      facility: demo.facility,
      tier: demo.tier
    });
  };

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-slate-100 flex flex-col justify-between transition-colors">
      {/* Top Header */}
      <header className="border-b border-slate-200 dark:border-slate-800 bg-white/90 dark:bg-slate-900/90 backdrop-blur-md px-6 py-3.5 flex items-center justify-between sticky top-0 z-20 shadow-xs transition-colors">
        <div className="flex items-center space-x-3">
          <div className="w-8 h-8 rounded-lg bg-blue-600 flex items-center justify-center text-white font-bold shadow-xs">
            <ShieldAlert className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <span className="font-extrabold text-sm tracking-tight text-slate-900 dark:text-slate-100">REACT-X</span>
              <span className="text-[10px] px-2 py-0.5 rounded-full font-semibold bg-blue-50 dark:bg-blue-950/60 text-blue-700 dark:text-blue-300 border border-blue-200 dark:border-blue-800">
                v2.4 Enterprise
              </span>
            </div>
            <p className="text-[11px] text-slate-500 dark:text-slate-400 font-medium">Industrial Thermal Intelligence & Predictive Safety</p>
          </div>
        </div>

        <div className="flex items-center space-x-3 text-xs">
          <span className="hidden sm:inline-flex items-center gap-1.5 text-emerald-700 dark:text-emerald-400 font-medium bg-emerald-50 dark:bg-emerald-950/50 px-2.5 py-1 rounded-full border border-emerald-200 dark:border-emerald-800">
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
            National Thermal Grid Active
          </span>

          {/* Centralized Global Theme Switcher */}
          <button
            onClick={toggleTheme}
            className="p-2 rounded-lg bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-200 border border-slate-200 dark:border-slate-700 cursor-pointer transition shadow-2xs"
            title={`Switch to ${isDark ? 'Light' : 'Dark'} Theme`}
          >
            {isDark ? <Sun className="w-4 h-4 text-amber-400" /> : <Moon className="w-4 h-4 text-slate-600" />}
          </button>

          <a href="#demo-access" className="text-blue-600 dark:text-blue-400 hover:underline font-semibold hidden md:flex items-center gap-1">
            Demo Credentials <ChevronRight className="w-3.5 h-3.5" />
          </a>
        </div>
      </header>

      {/* Main Hero & Auth Container */}
      <main className="max-w-7xl mx-auto w-full px-6 py-10 my-auto grid grid-cols-1 lg:grid-cols-12 gap-12 items-center">
        
        {/* Left Column: Brand & Value Proposition */}
        <div className="lg:col-span-7 space-y-6">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 text-xs font-semibold border border-slate-200 dark:border-slate-700">
            <Satellite className="w-3.5 h-3.5 text-blue-600 dark:text-blue-400" />
            <span>Multi-Sensor Earth Observation + Industrial Signal Fusion</span>
          </div>

          <h1 className="text-3xl sm:text-4xl font-extrabold text-slate-900 dark:text-slate-100 tracking-tight leading-tight">
            Industrial thermal intelligence and predictive emergency response.
          </h1>

          <p className="text-base text-slate-600 dark:text-slate-300 leading-relaxed max-w-2xl">
            REACT-X turns satellite thermal anomalies and plant signals into predictive industrial safety intelligence.
            Designed for continuous facility surveillance, multi-facility regional governance, and rapid hazard mitigation across India.
          </p>

          {/* Core Pipeline Architecture Card */}
          <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 p-5 shadow-xs space-y-3 transition-colors">
            <div className="text-xs font-bold uppercase text-slate-500 dark:text-slate-400 tracking-wider flex items-center gap-2">
              <Layers className="w-4 h-4 text-blue-600 dark:text-blue-400" />
              <span>Core Intelligence Pipeline</span>
            </div>
            
            <div className="grid grid-cols-1 sm:grid-cols-4 gap-3 text-xs">
              <div className="p-3 rounded-lg bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700 space-y-1">
                <div className="font-bold text-slate-900 dark:text-slate-100 flex items-center gap-1.5">
                  <Satellite className="w-3.5 h-3.5 text-blue-600 dark:text-blue-400" />
                  <span>1. Ingestion</span>
                </div>
                <p className="text-[11px] text-slate-500 dark:text-slate-400">NASA FIRMS, INSAT-3DR, Sentinel-2 & Plant OT.</p>
              </div>

              <div className="p-3 rounded-lg bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700 space-y-1">
                <div className="font-bold text-slate-900 dark:text-slate-100 flex items-center gap-1.5">
                  <Activity className="w-3.5 h-3.5 text-teal-600 dark:text-teal-400" />
                  <span>2. ML & Physics</span>
                </div>
                <p className="text-[11px] text-slate-500 dark:text-slate-400">23-feature classifier + Planck curve fitting.</p>
              </div>

              <div className="p-3 rounded-lg bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700 space-y-1">
                <div className="font-bold text-slate-900 dark:text-slate-100 flex items-center gap-1.5">
                  <ShieldCheck className="w-3.5 h-3.5 text-indigo-600 dark:text-indigo-400" />
                  <span>3. Fusion</span>
                </div>
                <p className="text-[11px] text-slate-500 dark:text-slate-400">Dempster-Shafer consensus & conflict mass.</p>
              </div>

              <div className="p-3 rounded-lg bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700 space-y-1">
                <div className="font-bold text-slate-900 dark:text-slate-100 flex items-center gap-1.5">
                  <ShieldAlert className="w-3.5 h-3.5 text-amber-600 dark:text-amber-400" />
                  <span>4. Response</span>
                </div>
                <p className="text-[11px] text-slate-500 dark:text-slate-400">Dispersion plumes, evacuation & ERDMP PDF.</p>
              </div>
            </div>
          </div>
        </div>

        {/* Right Column: Clean Authentication Panel */}
        <div className="lg:col-span-5 bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 p-6 sm:p-8 shadow-sm transition-colors">
          <div className="space-y-1.5 mb-6">
            <div className="flex border-b border-slate-200 dark:border-slate-800 mb-4 pb-2 gap-4">
              <button
                type="button"
                onClick={() => { setIsSignUp(false); setErrorMessage(''); }}
                className={`pb-1 text-sm font-bold border-b-2 cursor-pointer transition-colors ${
                  !isSignUp ? 'border-blue-600 text-blue-600 dark:text-blue-400' : 'border-transparent text-slate-400 hover:text-slate-600 dark:hover:text-slate-300'
                }`}
              >
                Sign In
              </button>
              <button
                type="button"
                onClick={() => { setIsSignUp(true); setErrorMessage(''); }}
                className={`pb-1 text-sm font-bold border-b-2 cursor-pointer transition-colors ${
                  isSignUp ? 'border-blue-600 text-blue-600 dark:text-blue-400' : 'border-transparent text-slate-400 hover:text-slate-600 dark:hover:text-slate-300'
                }`}
              >
                Request Account
              </button>
            </div>

            <h2 className="text-xl font-bold text-slate-900 dark:text-slate-100">
              {isSignUp ? 'Institutional Account Provisioning' : 'Sign in to REACT-X Platform'}
            </h2>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              {isSignUp ? 'Register authorized organizational credentials for monitored facilities.' : 'Access verified thermal surveillance, multi-facility intelligence, and emergency triage.'}
            </p>
          </div>

          {errorMessage && (
            <div className="mb-4 p-3 rounded-lg bg-rose-50 dark:bg-rose-950/50 border border-rose-200 dark:border-rose-800 text-rose-800 dark:text-rose-300 text-xs font-medium flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-rose-600 dark:text-rose-400 shrink-0" />
              <span>{errorMessage}</span>
            </div>
          )}

          <form onSubmit={handleManualSubmit} className="space-y-4">
            {isSignUp && (
              <div>
                <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5">Full Name</label>
                <div className="relative">
                  <User className="w-4 h-4 text-slate-400 absolute left-3 top-3" />
                  <input 
                    type="text" 
                    value={fullName}
                    onChange={(e) => setFullName(e.target.value)}
                    placeholder="Chief Controller Adityaraj"
                    className="w-full pl-9 pr-3 py-2 bg-slate-50 dark:bg-slate-800 border border-slate-300 dark:border-slate-700 rounded-lg text-sm text-slate-900 dark:text-slate-100 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:bg-white dark:focus:bg-slate-900 transition-all"
                    required
                  />
                </div>
              </div>
            )}

            <div>
              <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5">Work Email / User ID</label>
              <div className="relative">
                <Mail className="w-4 h-4 text-slate-400 absolute left-3 top-3" />
                <input 
                  type="email" 
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="operator@dahej-petro.in"
                  className="w-full pl-9 pr-3 py-2 bg-slate-50 dark:bg-slate-800 border border-slate-300 dark:border-slate-700 rounded-lg text-sm text-slate-900 dark:text-slate-100 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:bg-white dark:focus:bg-slate-900 transition-all"
                  required
                />
              </div>
            </div>

            <div>
              <div className="flex items-center justify-between mb-1.5">
                <label className="text-xs font-semibold text-slate-700 dark:text-slate-300">Password</label>
                {!isSignUp && (
                  <a href="#forgot" onClick={(e) => { e.preventDefault(); alert('Demo environment: Please select one of the Quick Demo Logins below.'); }} className="text-xs font-medium text-blue-600 dark:text-blue-400 hover:underline">
                    Forgot?
                  </a>
                )}
              </div>
              <div className="relative">
                <Lock className="w-4 h-4 text-slate-400 absolute left-3 top-3" />
                <input 
                  type={showPassword ? 'text' : 'password'} 
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••••••"
                  className="w-full pl-9 pr-10 py-2 bg-slate-50 dark:bg-slate-800 border border-slate-300 dark:border-slate-700 rounded-lg text-sm text-slate-900 dark:text-slate-100 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:bg-white dark:focus:bg-slate-900 transition-all"
                  required
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-2.5 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200"
                >
                  {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5">Operating Role Tier</label>
              <select 
                value={selectedRole}
                onChange={(e) => setSelectedRole(e.target.value)}
                className="w-full px-3 py-2 bg-slate-50 dark:bg-slate-800 border border-slate-300 dark:border-slate-700 rounded-lg text-xs font-semibold text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:bg-white dark:focus:bg-slate-900 transition-all cursor-pointer"
              >
                <option value="HSE_COMMANDER">Tier 1 — Plant Operator / HSE Commander</option>
                <option value="DISTRICT_AUTHORITY">Tier 2 — Regional Authority (GIDC)</option>
                <option value="EXECUTIVE_AUTHORITY">Tier 3 — National Command (NDMA / MoPNG)</option>
                <option value="FIELD_RESPONDER">Tier 4 — Emergency / Fire & Rescue (NDRF)</option>
              </select>
            </div>

            <button
              type="submit"
              disabled={isLoading}
              className="w-full py-2.5 px-4 bg-blue-600 hover:bg-blue-700 text-white font-semibold rounded-lg text-sm transition-all shadow-xs flex items-center justify-center gap-2 cursor-pointer disabled:opacity-60"
            >
              <span>{isLoading ? 'Authenticating...' : isSignUp ? 'Request Provisioning' : 'Sign In to REACT-X'}</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          </form>

          <div className="mt-4 pt-4 border-t border-slate-200 dark:border-slate-800 text-center">
            <button 
              type="button"
              onClick={() => { setIsSignUp(!isSignUp); setErrorMessage(''); }}
              className="text-xs font-medium text-slate-600 dark:text-slate-400 hover:text-blue-600 dark:hover:text-blue-400 transition-colors cursor-pointer"
            >
              {isSignUp ? 'Already have credentials? Sign in' : 'Need institutional provisioning? Request account'}
            </button>
          </div>
        </div>
      </main>

      {/* Bottom Demo Access Section */}
      <section id="demo-access" className="border-t border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 px-6 py-6 shadow-xs transition-colors">
        <div className="max-w-7xl mx-auto w-full space-y-3">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1">
            <div className="flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-blue-600 dark:text-blue-400" />
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-800 dark:text-slate-200">
                Evaluation Demo Accounts — Instant 1-Click Access
              </h3>
            </div>
            <p className="text-[11px] text-slate-500 dark:text-slate-400">Click any tier below to test live role-tailored intelligence.</p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
            {DEMO_ROLES.map((demo) => (
              <button
                key={demo.tier}
                type="button"
                onClick={() => handleDemoQuickLogin(demo)}
                className={`text-left p-3.5 rounded-xl border transition-all cursor-pointer group shadow-2xs hover:shadow-xs flex flex-col justify-between ${demo.color}`}
              >
                <div className="space-y-1">
                  <div className="flex items-center justify-between">
                    <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${demo.badge}`}>
                      {demo.tier}
                    </span>
                    <span className="text-[10px] text-blue-600 dark:text-blue-400 font-bold group-hover:underline flex items-center gap-0.5">
                      Launch <ArrowRight className="w-3 h-3" />
                    </span>
                  </div>
                  <h4 className="font-bold text-slate-900 dark:text-slate-100 text-xs">{demo.name}</h4>
                  <p className="text-[11px] text-slate-600 dark:text-slate-400 leading-tight">{demo.scope}</p>
                </div>

                <div className="mt-2 pt-2 border-t border-slate-200/60 dark:border-slate-800 font-mono text-[10px] text-slate-500 dark:text-slate-400 space-y-0.5">
                  <div className="truncate"><span className="text-slate-400">ID:</span> {demo.email}</div>
                  <div><span className="text-slate-400">Pass:</span> {demo.password}</div>
                </div>
              </button>
            ))}
          </div>
        </div>
      </section>
    </div>
  );
}

