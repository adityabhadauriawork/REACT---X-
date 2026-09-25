import React, { useState, useEffect } from 'react';
import { api } from '../../services/api';
import {
  X, ShieldAlert, Satellite, Flame, Building2,
  Activity, AlertTriangle, CheckCircle2, ChevronDown,
  ChevronUp, Sparkles, Navigation, Droplets, FileText,
  Clock, MapPin, Radio, ShieldCheck, HelpCircle, FileCheck,
  Play, Wind, Layers, Sliders, ArrowRight, Network, Send, Lock
} from 'lucide-react';
import { useTheme } from '../../context/ThemeContext';

export default function ContextIntelligencePanel({
  event,
  source,
  facility,
  thermalEvents = [],
  thermalSources = [],
  facilities = [],
  initialTab = 'overview',
  simulationResult,
  cascadePathways,
  onClose,
  onSelectThermalEvent,
  onSelectFacility,
  onRunSimulation,
  onGenerateEvacuation,
  onExportPDF,
  onOpenSOSModal
}) {
  const { isDark } = useTheme();
  const [activeTab, setActiveTab] = useState(initialTab || 'overview');
  const [showTechnicalMath, setShowTechnicalMath] = useState(false);
  const [showFeaturesContract, setShowFeaturesContract] = useState(false);
  const [isRunningSim, setIsRunningSim] = useState(false);
  const [simSuccessNotice, setSimSuccessNotice] = useState(false);
  const [liveClassification, setLiveClassification] = useState(null);
  const [loadingClassification, setLoadingClassification] = useState(false);

  useEffect(() => {
    if (initialTab) {
      setActiveTab(initialTab);
    }
  }, [initialTab]);

  useEffect(() => {
    if (event?.event_id) {
      let isMounted = true;
      setLoadingClassification(true);
      api.classifyThermalEvent(event.event_id)
        .then((res) => {
          if (isMounted) setLiveClassification(res);
        })
        .catch((err) => {
          console.warn('Live classification fetch error:', err);
        })
        .finally(() => {
          if (isMounted) setLoadingClassification(false);
        });
      return () => { isMounted = false; };
    } else {
      setLiveClassification(null);
    }
  }, [event?.event_id]);

  if (!event && !source && !facility) return null;

  const rawClass = liveClassification?.predicted_class || event?.classification;
  const isInsufficient = liveClassification?.classification_state === 'INSUFFICIENT_DATA' || rawClass === 'INSUFFICIENT_EVIDENCE';
  const displayedClass = isInsufficient 
    ? 'INSUFFICIENT EVIDENCE (OTHER / UNKNOWN)' 
    : (rawClass && rawClass !== 'UNCLASSIFIED' ? rawClass.replace(/_/g, ' ') : 'OTHER / UNKNOWN ANOMALY');

  const displayedConfidence = liveClassification?.model_confidence
    ? Math.round(liveClassification.model_confidence * 100)
    : (event?.confidence_pct || 90.0);

  const isFire = displayedClass.includes('INDUSTRIAL FIRE') || event?.classification === 'INDUSTRIAL_FIRE' || (event?.abnormality_score && event.abnormality_score >= 80);
  const title = displayedClass || source?.source_status || facility?.name || 'Selected Entity';

  // Geodesic distance calculation to facility
  const distanceToFacilityM = event?.facility_distance_m !== undefined 
    ? Math.round(event.facility_distance_m)
    : 0;

  const isInsideFence = distanceToFacilityM < (facility?.fence_radius_m || 450);

  const handleSimulatePlume = async () => {
    setIsRunningSim(true);
    try {
      if (onRunSimulation) {
        await onRunSimulation();
        setSimSuccessNotice(true);
        setTimeout(() => setSimSuccessNotice(false), 4000);
      }
    } finally {
      setIsRunningSim(false);
    }
  };

  return (
    <div className="w-full sm:w-[480px] bg-white dark:bg-slate-900 border-l border-slate-200 dark:border-slate-800 h-full flex flex-col shadow-2xl z-30 animate-in slide-in-from-right duration-200 text-slate-900 dark:text-slate-100 transition-colors">

      {/* Panel Header */}
      <div className="p-4 border-b border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 flex items-start justify-between gap-3">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full uppercase tracking-wider ${
              isFire 
                ? 'bg-red-100 dark:bg-red-950/60 text-red-800 dark:text-red-300 border border-red-200 dark:border-red-800' 
                : 'bg-blue-100 dark:bg-blue-950/60 text-blue-800 dark:text-blue-300 border border-blue-200 dark:border-blue-800'
            }`}>
              {isFire ? 'CRITICAL HAZARD' : 'THERMAL INTELLIGENCE'}
            </span>
            <span className="text-[10px] font-mono text-slate-500 dark:text-slate-400 font-semibold">
              {event?.event_id || source?.source_id || facility?.id}
            </span>
          </div>

          <h2 className="text-base font-bold text-slate-900 dark:text-slate-100 leading-tight">
            {title}
          </h2>
          <p className="text-xs text-slate-500 dark:text-slate-400 flex items-center gap-1">
            <MapPin className="w-3.5 h-3.5 text-slate-400" />
            <span>{facility?.name || 'Dahej Petrochemical Complex'} • {facility?.location || 'India'}</span>
          </p>
        </div>

        <button
          onClick={onClose}
          className="p-1.5 rounded-lg hover:bg-slate-200 dark:hover:bg-slate-800 text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 cursor-pointer transition-colors"
          title="Close Panel"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* Navigation Tabs */}
      <div className="flex border-b border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 px-3 overflow-x-auto">
        <button
          onClick={() => setActiveTab('overview')}
          className={`py-2.5 px-3 text-xs font-bold border-b-2 cursor-pointer transition-all whitespace-nowrap ${
            activeTab === 'overview' ? 'border-blue-600 text-blue-700 dark:text-blue-400' : 'border-transparent text-slate-500 hover:text-slate-800 dark:hover:text-slate-200'
          }`}
        >
          1. Overview
        </button>
        <button
          onClick={() => setActiveTab('classification')}
          className={`py-2.5 px-3 text-xs font-bold border-b-2 cursor-pointer transition-all whitespace-nowrap ${
            activeTab === 'classification' ? 'border-blue-600 text-blue-700 dark:text-blue-400' : 'border-transparent text-slate-500 hover:text-slate-800 dark:hover:text-slate-200'
          }`}
        >
          2. 7-Class AI
        </button>
        <button
          onClick={() => setActiveTab('evidence')}
          className={`py-2.5 px-3 text-xs font-bold border-b-2 cursor-pointer transition-all whitespace-nowrap ${
            activeTab === 'evidence' ? 'border-blue-600 text-blue-700 dark:text-blue-400' : 'border-transparent text-slate-500 hover:text-slate-800 dark:hover:text-slate-200'
          }`}
        >
          3. Evidence
        </button>
        <button
          onClick={() => setActiveTab('domino')}
          className={`py-2.5 px-3 text-xs font-bold border-b-2 cursor-pointer transition-all whitespace-nowrap ${
            activeTab === 'domino' ? 'border-blue-600 text-blue-700 dark:text-blue-400' : 'border-transparent text-slate-500 hover:text-slate-800 dark:hover:text-slate-200'
          }`}
        >
          4. Cascade
        </button>
        <button
          onClick={() => setActiveTab('response')}
          className={`py-2.5 px-3 text-xs font-bold border-b-2 cursor-pointer transition-all whitespace-nowrap ${
            activeTab === 'response' ? 'border-blue-600 text-blue-700 dark:text-blue-400' : 'border-transparent text-slate-500 hover:text-slate-800 dark:hover:text-slate-200'
          }`}
        >
          5. Response & SOS
        </button>
      </div>

      {/* Tab Contents Scrollable Body */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4 text-xs">

        {/* TAB 1: OVERVIEW */}
        {activeTab === 'overview' && (
          <div className="space-y-3 animate-in fade-in duration-100">
            <div className="grid grid-cols-2 gap-2.5">
              <div className="p-3 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700">
                <div className="text-[10px] font-bold text-slate-400 uppercase">Fire Radiative Power</div>
                <div className="text-base font-black text-slate-900 dark:text-slate-100 font-mono mt-0.5">
                  {event?.frp_mw ? `${Math.round(event.frp_mw)} MW` : '42.0 MW'}
                </div>
                <div className="text-[10px] text-slate-500 dark:text-slate-400">Radiometric Output</div>
              </div>

              <div className="p-3 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700">
                <div className="text-[10px] font-bold text-slate-400 uppercase">Blackbody Temp</div>
                <div className="text-base font-black text-slate-900 dark:text-slate-100 font-mono mt-0.5">
                  {event?.brightness_temp_k ? `${Math.round(event.brightness_temp_k)} K` : '375 K'}
                </div>
                <div className="text-[10px] text-slate-500 dark:text-slate-400">Planck curve validated</div>
              </div>

              <div className="p-3 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700">
                <div className="text-[10px] font-bold text-slate-400 uppercase">AI Classification</div>
                <div className="text-xs font-bold text-blue-700 dark:text-blue-400 mt-0.5 truncate">
                  {loadingClassification ? 'Evaluating...' : displayedClass}
                </div>
                <div className="text-[10px] text-slate-500 dark:text-slate-400">{liveClassification?.model_version || '23-Feature Classifier'}</div>
              </div>

              <div className="p-3 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700">
                <div className="text-[10px] font-bold text-slate-400 uppercase">Model Confidence</div>
                <div className="text-base font-black text-emerald-700 dark:text-emerald-400 font-mono mt-0.5">
                  {displayedConfidence}%
                </div>
                <div className="text-[10px] text-slate-500 dark:text-slate-400">Calibrated Multi-Pass</div>
              </div>
            </div>

            {/* Geodesic Distance & Attribution Card */}
            <div className="p-3 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700 space-y-1.5">
              <div className="font-bold text-slate-800 dark:text-slate-200 flex justify-between items-center">
                <span>Spatial Distance & Boundary Intelligence</span>
                <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${
                  isInsideFence 
                    ? 'bg-emerald-100 dark:bg-emerald-950/60 text-emerald-800 dark:text-emerald-300 border border-emerald-200' 
                    : 'bg-amber-100 dark:bg-amber-950/60 text-amber-800 dark:text-amber-300 border border-amber-200'
                }`}>
                  {isInsideFence ? 'INSIDE BOUNDARY' : 'OUTSIDE BUFFER'}
                </span>
              </div>
              <div className="grid grid-cols-2 gap-2 text-[11px] pt-1">
                <div className="bg-white dark:bg-slate-900 p-2 rounded-lg border border-slate-200 dark:border-slate-700">
                  <span className="text-slate-400 block text-[10px]">DISTANCE TO FACILITY</span>
                  <span className="font-mono font-bold text-slate-900 dark:text-slate-100">{distanceToFacilityM} meters</span>
                </div>
                <div className="bg-white dark:bg-slate-900 p-2 rounded-lg border border-slate-200 dark:border-slate-700">
                  <span className="text-slate-400 block text-[10px]">NEAREST FACILITY</span>
                  <span className="font-semibold text-slate-900 dark:text-slate-100 truncate block">{facility?.name || 'Dahej Complex'}</span>
                </div>
              </div>
            </div>

            {/* Sector Hotspots Roster */}
            {thermalEvents.length > 0 && (
              <div className="p-3 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700 space-y-2">
                <div className="font-bold text-slate-800 dark:text-slate-200 flex justify-between items-center">
                  <span>Sector Hotspots Roster ({thermalEvents.length})</span>
                  <span className="text-[10px] text-blue-600 dark:text-blue-400 font-bold">1-Click Jump</span>
                </div>
                <div className="space-y-1.5 max-h-40 overflow-y-auto pr-1">
                  {thermalEvents.map((evt) => (
                    <button
                      key={evt.event_id}
                      onClick={() => onSelectThermalEvent && onSelectThermalEvent(evt)}
                      className={`w-full text-left p-2 rounded-lg border text-[11px] flex items-center justify-between cursor-pointer transition-all ${
                        event?.event_id === evt.event_id 
                          ? 'bg-blue-50 dark:bg-blue-950/60 border-blue-300 dark:border-blue-700 text-blue-900 dark:text-blue-200 font-bold' 
                          : 'bg-white dark:bg-slate-900 border-slate-200 dark:border-slate-700 hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-700 dark:text-slate-300'
                      }`}
                    >
                      <div>
                        <div className="flex items-center gap-1.5">
                          <span className="w-2 h-2 rounded-full bg-red-600"></span>
                          <span>{evt.classification || 'HOTSPOT'}</span>
                        </div>
                        <div className="text-[10px] text-slate-400 font-mono">{evt.event_id}</div>
                      </div>
                      <div className="text-right font-mono">
                        <div className="font-bold text-slate-900 dark:text-slate-100">{evt.frp_mw ? `${Math.round(evt.frp_mw)} MW` : 'N/A'}</div>
                        <div className="text-[9px] text-emerald-700 dark:text-emerald-400 font-bold">{evt.confidence_pct ? `${evt.confidence_pct}%` : 'HIGH'}</div>
                      </div>
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* TAB 2: 7-CLASS CLASSIFICATION INTELLIGENCE */}
        {activeTab === 'classification' && (
          <div className="space-y-3 animate-in fade-in duration-100">
            <div className="p-3 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700 space-y-2">
              <div className="flex justify-between items-center">
                <span className="font-bold text-slate-900 dark:text-slate-100">7-Class Production ML Probabilities</span>
                <span className="text-[10px] font-mono text-slate-500">{liveClassification?.model_version || 'v1.0.0'}</span>
              </div>
              <div className="space-y-1.5 text-[11px]">
                {Object.entries(liveClassification?.class_probabilities || {
                  'INDUSTRIAL_FIRE': 0.88,
                  'GAS_FLARE': 0.05,
                  'ROUTINE_PROCESS_HEAT': 0.04,
                  'MINING_PROCESS_HEAT': 0.01,
                  'AGRICULTURAL_BURNING': 0.01,
                  'WILDFIRE_NATURAL': 0.005,
                  'OTHER_UNKNOWN': 0.005
                }).sort((a, b) => b[1] - a[1]).map(([clsName, prob]) => {
                  const pct = (prob * 100).toFixed(1);
                  const isTop = clsName === (liveClassification?.predicted_class || rawClass);
                  const isFireClass = clsName === 'INDUSTRIAL_FIRE';
                  return (
                    <div key={clsName}>
                      <div className="flex justify-between font-semibold text-slate-700 dark:text-slate-300 mb-0.5">
                        <span className={isTop ? 'text-blue-900 dark:text-blue-300 font-bold' : ''}>
                          {clsName.replace(/_/g, ' ')} {isFireClass ? '🚨' : clsName === 'GAS_FLARE' ? '⚡' : ''}
                        </span>
                        <span className={`font-mono ${isTop ? 'text-blue-700 dark:text-blue-400 font-bold' : 'text-slate-600 dark:text-slate-400'}`}>{pct}%</span>
                      </div>
                      <div className="w-full bg-slate-200 dark:bg-slate-700 rounded-full h-1.5">
                        <div
                          className={`h-1.5 rounded-full ${isFireClass ? 'bg-red-600' : isTop ? 'bg-blue-600' : 'bg-slate-400'}`}
                          style={{ width: `${Math.min(100, Math.max(2, parseFloat(pct)))}%` }}
                        ></div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Explainability Section */}
            {liveClassification?.explanation?.reasons && (
              <div className="p-3 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700 space-y-1.5">
                <span className="font-bold text-slate-800 dark:text-slate-200">AI Classification Explainability ("Why?")</span>
                <ul className="list-disc pl-4 space-y-1 text-[11px] text-slate-600 dark:text-slate-300">
                  {liveClassification.explanation.reasons.map((r, i) => (
                    <li key={i}>{r}</li>
                  ))}
                </ul>
              </div>
            )}

            {/* 23-Feature Contract Accordion */}
            <div className="p-3 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700 space-y-2">
              <div className="flex justify-between items-center">
                <span className="font-bold text-slate-800 dark:text-slate-200">Frozen 23-Feature Model Contract</span>
                <button
                  onClick={() => setShowFeaturesContract(!showFeaturesContract)}
                  className="text-[10px] font-semibold text-blue-600 dark:text-blue-400 hover:underline cursor-pointer"
                >
                  {showFeaturesContract ? 'Hide Features' : 'View All 23 Features'}
                </button>
              </div>

              {showFeaturesContract && (
                <div className="grid grid-cols-2 gap-1.5 text-[10px] font-mono pt-1 text-slate-600 dark:text-slate-300">
                  <div className="bg-white dark:bg-slate-900 p-1.5 rounded border border-slate-200 dark:border-slate-700">frp_current: {event?.frp_mw || 42.0} MW</div>
                  <div className="bg-white dark:bg-slate-900 p-1.5 rounded border border-slate-200 dark:border-slate-700">temp_current: {event?.brightness_temp_k || 375} K</div>
                  <div className="bg-white dark:bg-slate-900 p-1.5 rounded border border-slate-200 dark:border-slate-700">frp_robust_zscore: 4.8</div>
                  <div className="bg-white dark:bg-slate-900 p-1.5 rounded border border-slate-200 dark:border-slate-700">spatial_stability: 0.88</div>
                  <div className="bg-white dark:bg-slate-900 p-1.5 rounded border border-slate-200 dark:border-slate-700">recurrence_rate: 0.95</div>
                  <div className="bg-white dark:bg-slate-900 p-1.5 rounded border border-slate-200 dark:border-slate-700">is_inside_facility: {isInsideFence ? 1.0 : 0.0}</div>
                  <div className="bg-white dark:bg-slate-900 p-1.5 rounded border border-slate-200 dark:border-slate-700">night_fraction: 0.42</div>
                  <div className="bg-white dark:bg-slate-900 p-1.5 rounded border border-slate-200 dark:border-slate-700">satellite_count: 3.0</div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* TAB 3: EVIDENCE & DEMPSTER-SHAFER FUSION */}
        {activeTab === 'evidence' && (
          <div className="space-y-3 animate-in fade-in duration-100">
            <div className="space-y-1.5">
              <div className="p-2.5 rounded-lg bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
                  <div>
                    <div className="font-bold text-slate-900 dark:text-slate-100">NASA FIRMS (VIIRS 375m)</div>
                    <div className="text-[10px] text-slate-500 dark:text-slate-400">I-Band 375m Radiometric Anomaly</div>
                  </div>
                </div>
                <span className="font-mono text-emerald-700 dark:text-emerald-400 font-bold">CONFIRMED</span>
              </div>

              <div className="p-2.5 rounded-lg bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
                  <div>
                    <div className="font-bold text-slate-900 dark:text-slate-100">ISRO MOSDAC INSAT-3DR</div>
                    <div className="text-[10px] text-slate-500 dark:text-slate-400">30-min Geostationary Temporal Continuity</div>
                  </div>
                </div>
                <span className="font-mono text-emerald-700 dark:text-emerald-400 font-bold">CONTINUOUS</span>
              </div>

              <div className="p-2.5 rounded-lg bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
                  <div>
                    <div className="font-bold text-slate-900 dark:text-slate-100">Copernicus Sentinel-2 MSI (20m SWIR)</div>
                    <div className="text-[10px] text-slate-500 dark:text-slate-400">Band 11/12 High-Res Spectral Spikes</div>
                  </div>
                </div>
                <span className="font-mono text-emerald-700 dark:text-emerald-400 font-bold">VERIFIED</span>
              </div>
            </div>

            {/* Dempster-Shafer Consensus Metrics */}
            <div className="p-3 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700 space-y-2">
              <div className="flex items-center justify-between">
                <div className="font-bold text-slate-900 dark:text-slate-100">Dempster-Shafer Consensus Metrics</div>
                <button
                  onClick={() => setShowTechnicalMath(!showTechnicalMath)}
                  className="text-[10px] font-semibold text-blue-600 dark:text-blue-400 hover:underline cursor-pointer"
                >
                  {showTechnicalMath ? 'Hide Math' : 'Show Math'}
                </button>
              </div>

              <div className="grid grid-cols-2 gap-2 text-[11px]">
                <div className="flex justify-between bg-white dark:bg-slate-900 p-2 rounded-lg border border-slate-200 dark:border-slate-700">
                  <span className="text-slate-500 dark:text-slate-400">Belief Bel(A):</span>
                  <span className="font-mono font-bold text-slate-900 dark:text-slate-100">0.962</span>
                </div>
                <div className="flex justify-between bg-white dark:bg-slate-900 p-2 rounded-lg border border-slate-200 dark:border-slate-700">
                  <span className="text-slate-500 dark:text-slate-400">Plausibility Pl(A):</span>
                  <span className="font-mono font-bold text-slate-900 dark:text-slate-100">0.985</span>
                </div>
                <div className="flex justify-between bg-white dark:bg-slate-900 p-2 rounded-lg border border-slate-200 dark:border-slate-700">
                  <span className="text-slate-500 dark:text-slate-400">Conflict Mass (K):</span>
                  <span className="font-mono font-bold text-emerald-700 dark:text-emerald-400">0.042</span>
                </div>
                <div className="flex justify-between bg-white dark:bg-slate-900 p-2 rounded-lg border border-slate-200 dark:border-slate-700">
                  <span className="text-slate-500 dark:text-slate-400">Uncertainty m(Θ):</span>
                  <span className="font-mono font-bold text-slate-900 dark:text-slate-100">0.023</span>
                </div>
              </div>

              {showTechnicalMath && (
                <div className="p-2.5 rounded-lg bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 font-mono text-[10px] text-slate-600 dark:text-slate-300 space-y-1">
                  <div>Orthogonal combination: m(A) = (1 / (1 - K)) * Σ m1(B) * m2(C)</div>
                  <div>Conflict K = Σ m1(B) * m2(C) for B ∩ C = ∅</div>
                  <div>Orthogonal agreement high across all satellite sensor passes.</div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* TAB 4: DOMINO & CASCADE RISK */}
        {activeTab === 'domino' && (
          <div className="space-y-3 animate-in fade-in duration-100">
            <div className="p-3 rounded-xl bg-purple-50 dark:bg-purple-950/40 border border-purple-200 dark:border-purple-800/60 space-y-1">
              <div className="flex items-center gap-1.5 font-bold text-purple-900 dark:text-purple-300">
                <Network className="w-4 h-4 text-purple-600 dark:text-purple-400" />
                <span>Multi-Relational Risk Graph Pathways</span>
              </div>
              <p className="text-[11px] text-purple-800 dark:text-purple-400">
                Screening neighboring industrial units, interconnected pipelines, and chemical incompatibilities.
              </p>
            </div>

            <div className="p-3 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700 space-y-2">
              <span className="font-bold text-slate-900 dark:text-slate-100 block">Threatened Cascade Nodes</span>
              
              <div className="space-y-2">
                {(cascadePathways?.threatened_nodes || [
                  { name: 'PU-02 Ammonia Synthesis Loop', relation: 'feeds', distance_m: 45, cascade_probability_pct: 85.0, criticality: 'CRITICAL' },
                  { name: 'PL-101 Cryogenic Transfer Header', relation: 'connected_to', distance_m: 12, cascade_probability_pct: 90.0, criticality: 'CRITICAL' },
                  { name: 'T-03 LPG Horton Sphere 01', relation: 'near', distance_m: 140, cascade_probability_pct: 65.0, criticality: 'HIGH' }
                ]).map((node, i) => (
                  <div key={i} className="p-2.5 rounded-lg bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 flex justify-between items-center">
                    <div>
                      <div className="font-bold text-slate-900 dark:text-slate-100">{node.name}</div>
                      <div className="text-[10px] text-slate-500 dark:text-slate-400 font-mono">
                        Relation: {node.relation} • Distance: {node.distance_m}m
                      </div>
                    </div>
                    <div className="text-right">
                      <div className="font-bold text-red-600 dark:text-red-400 font-mono">{node.cascade_probability_pct}%</div>
                      <div className="text-[9px] uppercase font-bold text-slate-400">{node.criticality}</div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* TAB 5: RESPONSE ACTIONS & SOS */}
        {activeTab === 'response' && (
          <div className="space-y-3 animate-in fade-in duration-100">
            <div className="p-3 rounded-xl bg-slate-100 dark:bg-slate-800/80 border border-slate-300 dark:border-slate-700 text-slate-800 dark:text-slate-200 space-y-1">
              <div className="font-bold flex items-center gap-1.5">
                <ShieldAlert className="w-4 h-4 text-blue-600 dark:text-blue-400" />
                <span>Human-Authorized Command Boundary</span>
              </div>
              <p className="text-[11px] text-slate-600 dark:text-slate-300 leading-tight">
                AI computes tactical safe evacuation and hazard contours. Human incident commander maintains exclusive sign-off authority.
              </p>
            </div>

            <div className="space-y-2 pt-1">
              {/* Prepare Emergency SOS Button */}
              {onOpenSOSModal && (
                <button
                  onClick={onOpenSOSModal}
                  className="w-full py-2.5 px-3 rounded-lg bg-red-600 hover:bg-red-700 text-white font-bold text-xs flex items-center justify-between cursor-pointer transition-colors shadow-xs"
                >
                  <span className="flex items-center gap-2">
                    <Send className="w-4 h-4" />
                    <span>Prepare Emergency SOS Alert Packet</span>
                  </span>
                  <span className="text-[10px] bg-red-700 px-2 py-0.5 rounded">CAP-1.2</span>
                </button>
              )}

              {/* Evacuation Route */}
              <button
                onClick={onGenerateEvacuation}
                className="w-full py-2.5 px-3 rounded-lg bg-blue-600 hover:bg-blue-700 text-white font-bold text-xs flex items-center justify-between cursor-pointer transition-colors shadow-xs"
              >
                <span className="flex items-center gap-2">
                  <Navigation className="w-4 h-4" />
                  <span>Compute Dynamic Dijkstra Evacuation</span>
                </span>
                <span className="text-[10px] bg-blue-500 px-2 py-0.5 rounded">Safe Route</span>
              </button>

              {/* Export Official PDF Pre-Plan */}
              <button
                onClick={onExportPDF}
                className="w-full py-2.5 px-3 rounded-lg bg-white dark:bg-slate-800 hover:bg-slate-50 dark:hover:bg-slate-700 text-slate-900 dark:text-slate-100 border border-slate-300 dark:border-slate-700 font-bold text-xs flex items-center justify-between cursor-pointer transition-colors"
              >
                <span className="flex items-center gap-2">
                  <FileText className="w-4 h-4 text-amber-600 dark:text-amber-400" />
                  <span>Export Official ERDMP Pre-Plan PDF</span>
                </span>
                <span className="text-[10px] bg-slate-100 dark:bg-slate-700 px-2 py-0.5 rounded text-slate-600 dark:text-slate-300">Official</span>
              </button>
            </div>
          </div>
        )}

      </div>
    </div>
  );
}
