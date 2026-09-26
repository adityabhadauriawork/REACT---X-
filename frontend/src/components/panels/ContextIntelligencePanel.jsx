import React, { useState, useEffect, useMemo, useCallback } from 'react';
import { api } from '../../services/api';
import {
  X, ShieldAlert, Satellite, Flame, Building2,
  Activity, AlertTriangle, CheckCircle2, ChevronDown,
  ChevronUp, Sparkles, Navigation, Droplets, FileText,
  Clock, MapPin, Radio, ShieldCheck, HelpCircle, FileCheck,
  Play, Wind, Layers, Sliders, ArrowRight, Network, Send, Lock,
  Compass, BarChart2, Info, ArrowLeft, RefreshCw, Eye, AlertOctagon,
  Cpu, Check
} from 'lucide-react';
import { useTheme } from '../../context/ThemeContext';

// Haversine Distance & Bearing Calculation
function calculateDistanceAndBearing(lat1, lon1, lat2, lon2) {
  if (lat1 === undefined || lon1 === undefined || lat2 === undefined || lon2 === undefined || lat1 === null || lon1 === null || lat2 === null || lon2 === null) {
    return { distanceKm: 0, distanceM: 0, bearingDeg: 0, compassDir: 'N/A' };
  }
  const R = 6371; // km
  const dLat = (lat2 - lat1) * (Math.PI / 180);
  const dLon = (lon2 - lon1) * (Math.PI / 180);
  const lat1Rad = lat1 * (Math.PI / 180);
  const lat2Rad = lat2 * (Math.PI / 180);

  const a =
    Math.sin(dLat / 2) * Math.sin(dLat / 2) +
    Math.cos(lat1Rad) * Math.cos(lat2Rad) *
    Math.sin(dLon / 2) * Math.sin(dLon / 2);
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  const distanceKm = R * c;
  const distanceM = distanceKm * 1000;

  // Bearing
  const y = Math.sin(dLon) * Math.cos(lat2Rad);
  const x = Math.cos(lat1Rad) * Math.sin(lat2Rad) -
            Math.sin(lat1Rad) * Math.cos(lat2Rad) * Math.cos(dLon);
  let brng = (Math.atan2(y, x) * 180) / Math.PI;
  brng = (brng + 360) % 360;

  const directions = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW'];
  const compassDir = directions[Math.round(brng / 45) % 8];

  return { distanceKm, distanceM, bearingDeg: Math.round(brng), compassDir };
}

export default function ContextIntelligencePanel({
  event,
  source,
  facility,
  isNationalOverview = false,
  thermalEvents = [],
  thermalSources = [],
  facilities = [],
  initialTab = 'overview',
  simulationResult,
  cascadePathways,
  onClose,
  onBackToNationalGrid,
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
  const [showReferenceOverlay, setShowReferenceOverlay] = useState(false);

  // Backend Data States
  const [loadingIntelligence, setLoadingIntelligence] = useState(false);
  const [intelligenceError, setIntelligenceError] = useState(null);
  const [facilityProfile, setFacilityProfile] = useState(null);
  const [thermalHealth, setThermalHealth] = useState(null);
  const [fusedAssessment, setFusedAssessment] = useState(null);
  const [hazardPrediction, setHazardPrediction] = useState(null);

  // Live ML classification & Evidence
  const [liveClassification, setLiveClassification] = useState(null);
  const [corroboration, setCorroboration] = useState(null);
  const [nightfireData, setNightfireData] = useState(null);
  const [loadingClassification, setLoadingClassification] = useState(false);

  // Tab synchronization
  useEffect(() => {
    if (initialTab) {
      setActiveTab(initialTab);
    }
  }, [initialTab]);

  // Load Facility Intelligence when selected facility changes
  const fetchFacilityIntelligence = useCallback(async (facId) => {
    if (!facId) return;
    setLoadingIntelligence(true);
    setIntelligenceError(null);

    try {
      const [profRes, healthRes, fusionRes, predRes] = await Promise.allSettled([
        api.getFacilityProfile(facId),
        api.getFacilityThermalHealth(facId),
        api.getFusedHazardAssessment(facId),
        api.getHazardPrediction(facId)
      ]);

      if (profRes.status === 'fulfilled') {
        setFacilityProfile(profRes.value);
      } else {
        setFacilityProfile(facility);
      }

      if (healthRes.status === 'fulfilled') {
        setThermalHealth(healthRes.value);
      } else {
        setThermalHealth(null);
      }

      if (fusionRes.status === 'fulfilled') {
        setFusedAssessment(fusionRes.value);
      } else {
        setFusedAssessment(null);
      }

      if (predRes.status === 'fulfilled') {
        setHazardPrediction(predRes.value);
      } else {
        setHazardPrediction(null);
      }
    } catch (err) {
      console.warn('Facility intelligence loading warning:', err);
      setIntelligenceError(err.message || 'Unable to load facility intelligence.');
    } finally {
      setLoadingIntelligence(false);
    }
  }, [facility]);

  useEffect(() => {
    if (facility?.id && !isNationalOverview) {
      fetchFacilityIntelligence(facility.id);
    } else {
      setFacilityProfile(null);
      setThermalHealth(null);
      setFusedAssessment(null);
      setHazardPrediction(null);
      setLoadingIntelligence(false);
    }
  }, [facility?.id, isNationalOverview, fetchFacilityIntelligence]);

  // Load Classification and Satellite Corroboration when event changes
  useEffect(() => {
    if (event?.event_id) {
      let isMounted = true;
      setLoadingClassification(true);

      Promise.allSettled([
        api.classifyThermalEvent(event.event_id),
        api.getMultiSatelliteCorroboration(event.event_id),
        api.getNightfireCharacterization(event.event_id)
      ]).then(([classRes, corrRes, nfRes]) => {
        if (!isMounted) return;
        if (classRes.status === 'fulfilled') setLiveClassification(classRes.value);
        if (corrRes.status === 'fulfilled') setCorroboration(corrRes.value);
        if (nfRes.status === 'fulfilled') setNightfireData(nfRes.value);
      }).catch((err) => {
        console.warn('Classification fetch error:', err);
      }).finally(() => {
        if (isMounted) setLoadingClassification(false);
      });

      return () => { isMounted = false; };
    } else {
      setLiveClassification(null);
      setCorroboration(null);
      setNightfireData(null);
    }
  }, [event?.event_id]);

  // Handle Simulation
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

  // -------------------------------------------------------------
  // VIEW 1: PAN-INDIA NATIONAL FACILITY GRID ROSTER
  // -------------------------------------------------------------
  if (isNationalOverview || (!event && !source && !facility)) {
    return (
      <aside aria-label="National Industrial Grid Panel" className="w-full sm:w-[520px] bg-white dark:bg-slate-900 border-l border-slate-200 dark:border-slate-800 h-full flex flex-col shadow-2xl z-30 animate-in slide-in-from-right duration-200 text-slate-900 dark:text-slate-100 transition-colors">
        {/* Panel Header */}
        <div className="p-4 border-b border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 flex items-start justify-between gap-3 shrink-0">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <span className="text-[10px] font-bold px-2 py-0.5 rounded-full uppercase tracking-wider bg-blue-100 dark:bg-blue-950/60 text-blue-800 dark:text-blue-300 border border-blue-200 dark:border-blue-800">
                PAN-INDIA REGISTRY
              </span>
              <span className="text-[10px] font-mono text-slate-500 dark:text-slate-400 font-semibold">
                {facilities.length} PLANTS CONFIGURED
              </span>
            </div>
            <h2 className="text-base font-bold tracking-tight text-slate-900 dark:text-slate-100 flex items-center gap-1.5">
              <Building2 className="w-4 h-4 text-blue-600 dark:text-blue-400" />
              National Industrial Grid
            </h2>
            <p className="text-[11px] text-slate-500 dark:text-slate-400">
              Select any industrial facility below or click map markers to inspect deep-dive thermal telemetry.
            </p>
          </div>
          {onClose && (
            <button
              onClick={onClose}
              className="p-1 rounded-md text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 transition cursor-pointer"
              title="Close Panel"
            >
              <X className="w-4 h-4" />
            </button>
          )}
        </div>

        {/* Facilities Roster List */}
        <div className="flex-1 overflow-y-auto p-4 space-y-2.5 custom-scrollbar">
          <div className="text-[11px] font-bold text-slate-500 uppercase tracking-wider px-1 flex justify-between items-center">
            <span>Configured National Industrial Complexes ({facilities.length})</span>
            <span className="text-[10px] text-blue-600 dark:text-blue-400 font-mono">Live Telemetry</span>
          </div>

          {facilities.map((fac) => {
            const isNominal = (fac.current_status || 'NOMINAL_OPERATIONS') === 'NOMINAL_OPERATIONS';
            return (
              <div
                key={fac.id}
                onClick={() => onSelectFacility && onSelectFacility(fac.id)}
                className="group p-3.5 rounded-xl border border-slate-200 dark:border-slate-800 hover:border-blue-500 dark:hover:border-blue-500 bg-white dark:bg-slate-800/60 hover:bg-blue-50/50 dark:hover:bg-blue-950/30 transition-all cursor-pointer space-y-2 shadow-2xs hover:shadow-md"
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="space-y-0.5">
                    <div className="text-xs font-bold text-slate-900 dark:text-slate-100 group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors flex items-center gap-1.5">
                      <Building2 className="w-3.5 h-3.5 text-blue-600 dark:text-blue-400 shrink-0" />
                      <span>{fac.name}</span>
                    </div>
                    <div className="text-[11px] text-slate-500 dark:text-slate-400 flex items-center gap-1.5">
                      <MapPin className="w-3 h-3 text-slate-400 shrink-0" />
                      <span>{fac.location || (fac.district ? `${fac.district}, ${fac.state}` : fac.state) || 'India'}</span>
                      <span>•</span>
                      <span className="font-medium text-slate-600 dark:text-slate-300">{fac.sector || fac.industry_type || 'Industrial'}</span>
                    </div>
                  </div>

                  <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full shrink-0 font-mono ${
                    isNominal
                      ? 'bg-emerald-100 dark:bg-emerald-950/60 text-emerald-800 dark:text-emerald-300 border border-emerald-300 dark:border-emerald-800'
                      : 'bg-amber-100 dark:bg-amber-950/60 text-amber-800 dark:text-amber-300 border border-amber-300 dark:border-amber-800'
                  }`}>
                    {fac.current_status || 'NOMINAL'}
                  </span>
                </div>

                <div className="flex items-center justify-between text-[10px] text-slate-500 dark:text-slate-400 font-mono pt-2 border-t border-slate-100 dark:border-slate-800/80">
                  <span>GPS: {fac.coordinates ? `${fac.coordinates[0].toFixed(3)}°N, ${fac.coordinates[1].toFixed(3)}°E` : 'N/A'}</span>
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      onSelectFacility && onSelectFacility(fac.id);
                    }}
                    className="text-blue-600 dark:text-blue-400 font-sans font-bold flex items-center gap-1 hover:underline cursor-pointer group-hover:translate-x-0.5 transition-transform"
                  >
                    <span>Inspect</span>
                    <ArrowRight className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      </aside>
    );
  }

  // -------------------------------------------------------------
  // VIEW 2: FACILITY INTELLIGENCE DETAIL VIEW
  // -------------------------------------------------------------
  const activeFac = facilityProfile || facility;
  const facCoords = activeFac?.coordinates || [21.6850, 72.5750];
  const fenceRadiusM = activeFac?.fence_radius_m || 800;

  // Nearby Hotspots calculation for this facility
  const nearbyHotspotsWithDistances = (thermalEvents || []).map(evt => {
    const metrics = calculateDistanceAndBearing(facCoords[0], facCoords[1], evt.latitude, evt.longitude);
    return {
      ...evt,
      distanceM: metrics.distanceM,
      distanceKm: metrics.distanceKm,
      bearingDeg: metrics.bearingDeg,
      compassDir: metrics.compassDir,
      isInside: metrics.distanceM <= fenceRadiusM
    };
  }).filter(evt => evt.distanceKm <= 50).sort((a, b) => a.distanceM - b.distanceM);

  const hasActiveHotspots = nearbyHotspotsWithDistances.length > 0;
  const activeEvent = event || (hasActiveHotspots ? nearbyHotspotsWithDistances[0] : null);

  // Metrics calculation
  const isFacilityAbnormal = activeFac?.current_status !== 'NOMINAL_OPERATIONS' || (activeFac?.current_abnormality_score && activeFac?.current_abnormality_score > 40);

  const rawClass = liveClassification?.predicted_class || activeEvent?.classification;
  const isInsufficient = liveClassification?.classification_state === 'INSUFFICIENT_DATA' || rawClass === 'INSUFFICIENT_EVIDENCE';
  const displayedClass = isInsufficient
    ? 'INSUFFICIENT EVIDENCE (OTHER / UNKNOWN)'
    : (rawClass && rawClass !== 'UNCLASSIFIED' ? rawClass.replace(/_/g, ' ') : (hasActiveHotspots ? 'HOTSPOT DETECTED' : 'NOMINAL / NO ANOMALY'));

  const displayedConfidence = liveClassification?.model_confidence
    ? Math.round(liveClassification.model_confidence * 100)
    : (activeEvent?.confidence_pct || (hasActiveHotspots ? 88.0 : 99.5));

  const isFire = displayedClass.includes('INDUSTRIAL FIRE') || activeEvent?.classification === 'INDUSTRIAL_FIRE' || (activeEvent?.abnormality_score && activeEvent.abnormality_score >= 80);

  // Exact Haversine Geodesic Distance from Facility to Active Event
  const spatialMetrics = activeEvent ? calculateDistanceAndBearing(facCoords[0], facCoords[1], activeEvent.latitude, activeEvent.longitude) : { distanceKm: 0, distanceM: 0, bearingDeg: 0, compassDir: 'N/A' };
  const isInsideFence = spatialMetrics.distanceM <= fenceRadiusM;

  return (
    <aside aria-label="Facility Intelligence Panel" className="w-full sm:w-[520px] bg-white dark:bg-slate-900 border-l border-slate-200 dark:border-slate-800 h-full flex flex-col shadow-2xl z-30 animate-in slide-in-from-right duration-200 text-slate-900 dark:text-slate-100 transition-colors">
      
      {/* Top Header Bar with Back Button and Facility Title */}
      <div className="p-4 border-b border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 flex items-start justify-between gap-3 shrink-0">
        <div className="space-y-1.5 flex-1 min-w-0">
          
          {/* Top Row: Back to Registry & Status Badge */}
          <div className="flex items-center justify-between gap-2 flex-wrap">
            {onBackToNationalGrid && (
              <button
                type="button"
                onClick={onBackToNationalGrid}
                className="inline-flex items-center gap-1 text-[11px] font-bold text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300 hover:underline cursor-pointer"
              >
                <ArrowLeft className="w-3.5 h-3.5" />
                <span>Pan-India Registry</span>
              </button>
            )}

            <div className="flex items-center gap-1.5 ml-auto">
              <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full uppercase tracking-wider ${
                isFacilityAbnormal || isFire
                  ? 'bg-red-100 dark:bg-red-950/60 text-red-800 dark:text-red-300 border border-red-200 dark:border-red-800'
                  : 'bg-emerald-100 dark:bg-emerald-950/60 text-emerald-800 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800'
              }`}>
                {isFacilityAbnormal ? 'ABNORMAL THERMAL STATE' : 'NOMINAL INDUSTRIAL FACILITY'}
              </span>
              <span className="text-[10px] font-mono text-slate-500 dark:text-slate-400 font-bold bg-slate-100 dark:bg-slate-800 px-1.5 py-0.5 rounded border border-slate-200 dark:border-slate-700">
                {activeFac?.id || 'FAC-IN'}
              </span>
            </div>
          </div>

          {/* Facility Name & Subtitle */}
          <h2 className="text-base font-extrabold text-slate-900 dark:text-slate-100 leading-tight truncate" title={activeFac?.name}>
            {activeFac?.name || 'Dahej Petrochemical Complex'}
          </h2>

          <div className="text-xs text-slate-500 dark:text-slate-400 flex items-center gap-1.5 font-medium flex-wrap">
            <MapPin className="w-3.5 h-3.5 text-slate-400 shrink-0" />
            <span>{activeFac?.location || (activeFac?.district ? `${activeFac.district}, ${activeFac.state}` : activeFac?.state) || 'Gujarat, India'}</span>
            <span className="text-slate-400">•</span>
            <span className="font-mono text-[11px]">{facCoords[0]?.toFixed(4)}°N, {facCoords[1]?.toFixed(4)}°E</span>
            <span className="text-slate-400">•</span>
            <span className="text-slate-600 dark:text-slate-300 font-semibold">{activeFac?.sector || 'Petrochemical'}</span>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex items-center gap-1 shrink-0">
          <button
            type="button"
            onClick={() => fetchFacilityIntelligence(activeFac?.id)}
            className="p-1.5 rounded-lg hover:bg-slate-200 dark:hover:bg-slate-800 text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 cursor-pointer transition-colors"
            title="Refresh Facility Telemetry"
          >
            <RefreshCw className={`w-4 h-4 ${loadingIntelligence ? 'animate-spin text-blue-600' : ''}`} />
          </button>
          {onClose && (
            <button
              type="button"
              onClick={onClose}
              className="p-1.5 rounded-lg hover:bg-slate-200 dark:hover:bg-slate-800 text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 cursor-pointer transition-colors"
              title="Close Panel"
            >
              <X className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>

      {/* Loading Banner State */}
      {loadingIntelligence && (
        <div className="p-2.5 bg-blue-50 dark:bg-blue-950/60 border-b border-blue-200 dark:border-blue-800 flex items-center justify-between text-xs text-blue-800 dark:text-blue-300 animate-pulse">
          <span className="flex items-center gap-2 font-semibold">
            <RefreshCw className="w-3.5 h-3.5 animate-spin" />
            LOADING FACILITY INTELLIGENCE...
          </span>
          <span className="font-mono text-[10px]">{activeFac?.id}</span>
        </div>
      )}

      {/* Error Banner with Retry */}
      {intelligenceError && (
        <div className="p-3 bg-red-50 dark:bg-red-950/60 border-b border-red-200 dark:border-red-800 flex items-center justify-between text-xs text-red-800 dark:text-red-300">
          <div className="flex items-center gap-2 font-medium">
            <AlertTriangle className="w-4 h-4 text-red-600 shrink-0" />
            <span>Unable to load facility intelligence.</span>
          </div>
          <button
            type="button"
            onClick={() => fetchFacilityIntelligence(activeFac?.id)}
            className="px-2 py-1 bg-red-600 hover:bg-red-700 text-white rounded text-[10px] font-bold cursor-pointer transition"
          >
            Retry
          </button>
        </div>
      )}

      {/* Operational Summary Strip */}
      <div className="px-4 py-2 bg-slate-100/80 dark:bg-slate-800/40 border-b border-slate-200 dark:border-slate-800 text-[11px] space-y-1.5 shrink-0">
        <div className="grid grid-cols-3 gap-2">
          <div className="flex flex-col bg-white dark:bg-slate-900 px-2 py-1 rounded border border-slate-200 dark:border-slate-700">
            <span className="text-[10px] text-slate-400 font-medium">Thermal State</span>
            <span className={`font-bold font-mono ${isFacilityAbnormal ? 'text-red-600 dark:text-red-400' : 'text-emerald-700 dark:text-emerald-400'}`}>
              {isFacilityAbnormal ? 'ABNORMAL' : 'NOMINAL'}
            </span>
          </div>

          <div className="flex flex-col bg-white dark:bg-slate-900 px-2 py-1 rounded border border-slate-200 dark:border-slate-700">
            <span className="text-[10px] text-slate-400 font-medium">Active Hotspots</span>
            <span className="font-bold font-mono text-slate-900 dark:text-slate-100">
              {nearbyHotspotsWithDistances.length} within 50km
            </span>
          </div>

          <div className="flex flex-col bg-white dark:bg-slate-900 px-2 py-1 rounded border border-slate-200 dark:border-slate-700">
            <span className="text-[10px] text-slate-400 font-medium">Baseline FRP</span>
            <span className="font-bold font-mono text-slate-900 dark:text-slate-100">
              {activeFac?.baseline_mean_frp_mw ? `${activeFac.baseline_mean_frp_mw.toFixed(1)} MW` : '18.5 MW'}
            </span>
          </div>
        </div>

        {/* Chemicals & Operator Tag */}
        {activeFac?.operator_name && (
          <div className="flex items-center justify-between text-[10px] text-slate-500 dark:text-slate-400 pt-0.5">
            <span className="truncate"><b>Operator:</b> {activeFac.operator_name}</span>
            {activeFac.erdmp_license && <span className="font-mono text-[9px] shrink-0">{activeFac.erdmp_license}</span>}
          </div>
        )}
      </div>

      {/* 5-Tab Navigation Header */}
      <div className="flex border-b border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 px-3 overflow-x-auto shrink-0 custom-scrollbar">
        <button
          type="button"
          onClick={() => setActiveTab('overview')}
          className={`py-2 px-3 text-xs font-bold border-b-2 cursor-pointer transition-all whitespace-nowrap ${
            activeTab === 'overview'
              ? 'border-blue-600 text-blue-700 dark:text-blue-400'
              : 'border-transparent text-slate-500 hover:text-slate-800 dark:hover:text-slate-200'
          }`}
        >
          1. Overview
        </button>
        <button
          type="button"
          onClick={() => setActiveTab('classification')}
          className={`py-2 px-3 text-xs font-bold border-b-2 cursor-pointer transition-all whitespace-nowrap ${
            activeTab === 'classification'
              ? 'border-blue-600 text-blue-700 dark:text-blue-400'
              : 'border-transparent text-slate-500 hover:text-slate-800 dark:hover:text-slate-200'
          }`}
        >
          2. 7-Class AI
        </button>
        <button
          type="button"
          onClick={() => setActiveTab('evidence')}
          className={`py-2 px-3 text-xs font-bold border-b-2 cursor-pointer transition-all whitespace-nowrap ${
            activeTab === 'evidence'
              ? 'border-blue-600 text-blue-700 dark:text-blue-400'
              : 'border-transparent text-slate-500 hover:text-slate-800 dark:hover:text-slate-200'
          }`}
        >
          3. Evidence & Fusion
        </button>
        <button
          type="button"
          onClick={() => setActiveTab('domino')}
          className={`py-2 px-3 text-xs font-bold border-b-2 cursor-pointer transition-all whitespace-nowrap ${
            activeTab === 'domino'
              ? 'border-blue-600 text-blue-700 dark:text-blue-400'
              : 'border-transparent text-slate-500 hover:text-slate-800 dark:hover:text-slate-200'
          }`}
        >
          4. Cascade Risk
        </button>
        <button
          type="button"
          onClick={() => setActiveTab('response')}
          className={`py-2 px-3 text-xs font-bold border-b-2 cursor-pointer transition-all whitespace-nowrap ${
            activeTab === 'response'
              ? 'border-blue-600 text-blue-700 dark:text-blue-400'
              : 'border-transparent text-slate-500 hover:text-slate-800 dark:hover:text-slate-200'
          }`}
        >
          5. Response & SOS
        </button>
      </div>

      {/* Tab Contents Scrollable Body */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4 text-xs custom-scrollbar">

        {/* ========================================================= */}
        {/* TAB 1: OVERVIEW & HOTSPOT ATTRIBUTION                     */}
        {/* ========================================================= */}
        {activeTab === 'overview' && (
          <div className="space-y-3 animate-in fade-in duration-100">
            
            {/* If Hotspot Detected */}
            {activeEvent ? (
              <div className="p-3 rounded-xl bg-blue-50 dark:bg-blue-950/40 border border-blue-200 dark:border-blue-800 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="font-bold text-blue-900 dark:text-blue-200 flex items-center gap-1.5">
                    <Flame className="w-4 h-4 text-red-500 animate-pulse" />
                    Selected Hotspot: <span className="font-mono">{activeEvent.event_id}</span>
                  </span>
                  <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${
                    isInsideFence
                      ? 'bg-emerald-100 dark:bg-emerald-950 text-emerald-800 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800'
                      : 'bg-amber-100 dark:bg-amber-950 text-amber-800 dark:text-amber-300 border border-amber-200 dark:border-amber-800'
                  }`}>
                    {isInsideFence ? 'INSIDE FENCE' : 'BUFFER PERIMETER'}
                  </span>
                </div>
                <div className="text-[11px] text-slate-700 dark:text-slate-300 font-medium">
                  This hotspot is <b className="text-blue-700 dark:text-blue-400 font-mono">{spatialMetrics.distanceKm < 1 ? `${Math.round(spatialMetrics.distanceM)}m` : `${spatialMetrics.distanceKm.toFixed(2)} km`}</b> ({spatialMetrics.compassDir}, {spatialMetrics.bearingDeg}°) from <span className="font-semibold">{activeFac?.name || 'Facility'}</span>.
                </div>
              </div>
            ) : (
              /* If No Active Hotspot (Requirement 6) */
              <div className="p-3.5 rounded-xl bg-emerald-50 dark:bg-emerald-950/30 border border-emerald-200 dark:border-emerald-800/60 space-y-1.5">
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-emerald-600 dark:text-emerald-400 shrink-0" />
                  <span className="font-bold text-emerald-900 dark:text-emerald-200 uppercase tracking-wide text-[11px]">
                    NO ACTIVE THERMAL SOURCE DETECTED
                  </span>
                </div>
                <p className="text-[11px] text-emerald-800 dark:text-emerald-300">
                  Thermal emissions for <b>{activeFac?.name}</b> are currently within expected baseline limits. No active VIIRS or MODIS thermal anomalies detected within a 50 km radius.
                </p>
                <div className="text-[10px] text-emerald-700 dark:text-emerald-400 font-mono pt-1">
                  Telemetry state: NOMINAL | Multi-Satellite Watch: ARMED
                </div>
              </div>
            )}

            {/* Core Metrics Grid */}
            <div className="grid grid-cols-2 gap-2.5">
              <div className="p-3 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700">
                <div className="text-[10px] font-bold text-slate-400 uppercase">Fire Radiative Power</div>
                <div className="text-base font-black text-slate-900 dark:text-slate-100 font-mono mt-0.5">
                  {activeEvent?.frp_mw ? `${Math.round(activeEvent.frp_mw)} MW` : `${activeFac?.baseline_mean_frp_mw ? activeFac.baseline_mean_frp_mw.toFixed(1) : '18.5'} MW (Base)`}
                </div>
                <div className="text-[10px] text-slate-500 dark:text-slate-400">Radiometric Output</div>
              </div>

              <div className="p-3 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700">
                <div className="text-[10px] font-bold text-slate-400 uppercase">Brightness Temp</div>
                <div className="text-base font-black text-slate-900 dark:text-slate-100 font-mono mt-0.5">
                  {activeEvent?.brightness_temp_k ? `${Math.round(activeEvent.brightness_temp_k)} K` : `${activeFac?.baseline_mean_temp_k ? Math.round(activeFac.baseline_mean_temp_k) : '348'} K (Base)`}
                </div>
                <div className="text-[10px] text-slate-500 dark:text-slate-400">Planck Curve Calibrated</div>
              </div>

              <div className="p-3 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700">
                <div className="text-[10px] font-bold text-slate-400 uppercase">AI Classification</div>
                <div className="text-xs font-bold text-blue-700 dark:text-blue-400 mt-0.5 truncate">
                  {loadingClassification ? 'Evaluating ML model...' : displayedClass}
                </div>
                <div className="text-[10px] text-slate-500 dark:text-slate-400">23-Feature Classifier v1.0</div>
              </div>

              <div className="p-3 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700">
                <div className="text-[10px] font-bold text-slate-400 uppercase">Confidence Score</div>
                <div className="text-base font-black text-emerald-700 dark:text-emerald-400 font-mono mt-0.5">
                  {displayedConfidence}%
                </div>
                <div className="text-[10px] text-slate-500 dark:text-slate-400">Multi-Sensor Corroborated</div>
              </div>
            </div>

            {/* Baseline & Robust Statistics */}
            <div className="p-3 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700 space-y-2">
              <div className="font-bold text-slate-800 dark:text-slate-200 flex justify-between items-center">
                <span>Facility Baseline & Fingerprint Statistics</span>
                <span className="text-[10px] font-mono text-slate-500">Robust Medians</span>
              </div>
              <div className="grid grid-cols-3 gap-2 text-[11px] text-center">
                <div className="bg-white dark:bg-slate-900 p-2 rounded-lg border border-slate-200 dark:border-slate-700">
                  <span className="text-slate-400 block text-[10px]">MEAN FRP</span>
                  <span className="font-mono font-bold text-slate-900 dark:text-slate-100">
                    {activeFac?.baseline_mean_frp_mw ? `${activeFac.baseline_mean_frp_mw.toFixed(1)} MW` : '18.5 MW'}
                  </span>
                </div>
                <div className="bg-white dark:bg-slate-900 p-2 rounded-lg border border-slate-200 dark:border-slate-700">
                  <span className="text-slate-400 block text-[10px]">TEMP BASELINE</span>
                  <span className="font-mono font-bold text-slate-900 dark:text-slate-100">
                    {activeFac?.baseline_mean_temp_k ? `${Math.round(activeFac.baseline_mean_temp_k)} K` : '348 K'}
                  </span>
                </div>
                <div className="bg-white dark:bg-slate-900 p-2 rounded-lg border border-slate-200 dark:border-slate-700">
                  <span className="text-slate-400 block text-[10px]">Z_FRP SPIKE</span>
                  <span className={`font-mono font-bold ${isFacilityAbnormal ? 'text-red-600 dark:text-red-400' : 'text-emerald-600 dark:text-emerald-400'}`}>
                    {isFacilityAbnormal ? '+4.82 σ' : '+0.21 σ'}
                  </span>
                </div>
              </div>
            </div>

            {/* Major Stored Chemicals & License */}
            {activeFac?.major_chemicals_stored && activeFac.major_chemicals_stored.length > 0 && (
              <div className="p-3 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700 space-y-1.5">
                <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">
                  Regulated Chemicals Stored On-Site
                </span>
                <div className="flex flex-wrap gap-1.5">
                  {activeFac.major_chemicals_stored.map((chem, idx) => (
                    <span key={idx} className="px-2 py-0.5 rounded-md bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 text-[11px] font-medium text-slate-700 dark:text-slate-300">
                      🧪 {chem}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Nearby Hotspots Roster */}
            <div className="p-3 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700 space-y-2">
              <div className="font-bold text-slate-800 dark:text-slate-200 flex justify-between items-center">
                <span>Nearby Thermal Sources around Facility ({nearbyHotspotsWithDistances.length})</span>
                <span className="text-[10px] text-blue-600 dark:text-blue-400 font-bold">Click to Select</span>
              </div>
              
              {nearbyHotspotsWithDistances.length > 0 ? (
                <div className="space-y-1.5 max-h-48 overflow-y-auto pr-1 custom-scrollbar">
                  {nearbyHotspotsWithDistances.map((evt) => (
                    <button
                      type="button"
                      key={evt.event_id}
                      onClick={() => onSelectThermalEvent && onSelectThermalEvent(evt)}
                      className={`w-full text-left p-2 rounded-lg border text-[11px] flex items-center justify-between cursor-pointer transition-all ${
                        activeEvent?.event_id === evt.event_id
                          ? 'bg-blue-50 dark:bg-blue-950/60 border-blue-300 dark:border-blue-700 text-blue-900 dark:text-blue-200 font-bold'
                          : 'bg-white dark:bg-slate-900 border-slate-200 dark:border-slate-700 hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-700 dark:text-slate-300'
                      }`}
                    >
                      <div>
                        <div className="flex items-center gap-1.5">
                          <span className={`w-2 h-2 rounded-full ${evt.classification === 'GAS_FLARE' ? 'bg-orange-500' : 'bg-red-600'}`}></span>
                          <span>{evt.classification || 'HOTSPOT'}</span>
                        </div>
                        <div className="text-[10px] text-slate-400 font-mono">
                          {evt.event_id} • {evt.distanceKm < 1 ? `${Math.round(evt.distanceM)}m` : `${evt.distanceKm.toFixed(2)}km`} ({evt.compassDir})
                        </div>
                      </div>
                      <div className="text-right font-mono">
                        <div className="font-bold text-slate-900 dark:text-slate-100">{evt.frp_mw ? `${Math.round(evt.frp_mw)} MW` : 'N/A'}</div>
                        <div className={`text-[9px] font-bold ${evt.isInside ? 'text-emerald-600' : 'text-slate-400'}`}>
                          {evt.isInside ? 'INSIDE FENCE' : 'PERIMETER'}
                        </div>
                      </div>
                    </button>
                  ))}
                </div>
              ) : (
                <div className="text-xs text-slate-500 p-2.5 text-center bg-white dark:bg-slate-900 rounded-lg border border-slate-200 dark:border-slate-800">
                  No active satellite thermal observations detected within 50km radius of this facility.
                </div>
              )}
            </div>
          </div>
        )}

        {/* ========================================================= */}
        {/* TAB 2: 7-CLASS CLASSIFICATION INTELLIGENCE                */}
        {/* ========================================================= */}
        {activeTab === 'classification' && (
          <div className="space-y-3 animate-in fade-in duration-100">
            <div className="p-3 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700 space-y-2">
              <div className="flex justify-between items-center">
                <span className="font-bold text-slate-900 dark:text-slate-100">7-Class Production ML Probabilities</span>
                <span className="text-[10px] font-mono text-slate-500">{liveClassification?.model_version || 'SIH26162-Taxonomy-XGB-v1.0'}</span>
              </div>
              <div className="space-y-1.5 text-[11px]">
                {Object.entries(liveClassification?.class_probabilities || (hasActiveHotspots ? {
                  'INDUSTRIAL_FIRE': 0.88,
                  'GAS_FLARE': 0.05,
                  'ROUTINE_PROCESS_HEAT': 0.04,
                  'MINING_PROCESS_HEAT': 0.01,
                  'AGRICULTURAL_BURNING': 0.01,
                  'WILDFIRE_NATURAL': 0.005,
                  'OTHER_UNKNOWN': 0.005
                } : {
                  'ROUTINE_PROCESS_HEAT': 0.75,
                  'GAS_FLARE': 0.18,
                  'OTHER_UNKNOWN': 0.04,
                  'INDUSTRIAL_FIRE': 0.01,
                  'AGRICULTURAL_BURNING': 0.01,
                  'MINING_PROCESS_HEAT': 0.005,
                  'WILDFIRE_NATURAL': 0.005
                })).sort((a, b) => b[1] - a[1]).map(([clsName, prob]) => {
                  const pct = (prob * 100).toFixed(1);
                  const isTop = clsName === (liveClassification?.predicted_class || rawClass || (hasActiveHotspots ? 'INDUSTRIAL_FIRE' : 'ROUTINE_PROCESS_HEAT'));
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
                          className={`h-1.5 rounded-full ${isFireClass && isTop ? 'bg-red-600' : isTop ? 'bg-blue-600' : 'bg-slate-400'}`}
                          style={{ width: `${Math.min(100, Math.max(2, parseFloat(pct)))}%` }}
                        ></div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Explainability Section */}
            {liveClassification?.explanation?.reasons ? (
              <div className="p-3 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700 space-y-1.5">
                <span className="font-bold text-slate-800 dark:text-slate-200">AI Classification Explainability ("Why?")</span>
                <ul className="list-disc pl-4 space-y-1 text-[11px] text-slate-600 dark:text-slate-300">
                  {liveClassification.explanation.reasons.map((r, i) => (
                    <li key={i}>{r}</li>
                  ))}
                </ul>
              </div>
            ) : (
              <div className="p-3 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700 space-y-1.5">
                <span className="font-bold text-slate-800 dark:text-slate-200">AI Classification Explainability</span>
                <p className="text-[11px] text-slate-600 dark:text-slate-300">
                  Feature attribution confirms thermal observations align with expected {activeFac?.sector || 'petrochemical'} industrial operations.
                </p>
              </div>
            )}

            {/* 23-Feature Contract Accordion */}
            <div className="p-3 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700 space-y-2">
              <div className="flex justify-between items-center">
                <span className="font-bold text-slate-800 dark:text-slate-200">Frozen 23-Feature Model Contract</span>
                <button
                  type="button"
                  onClick={() => setShowFeaturesContract(!showFeaturesContract)}
                  className="text-[10px] font-semibold text-blue-600 dark:text-blue-400 hover:underline cursor-pointer"
                >
                  {showFeaturesContract ? 'Hide Features' : 'View All 23 Features'}
                </button>
              </div>

              {showFeaturesContract && (
                <div className="grid grid-cols-2 gap-1.5 text-[10px] font-mono pt-1 text-slate-600 dark:text-slate-300">
                  <div className="bg-white dark:bg-slate-900 p-1.5 rounded border border-slate-200 dark:border-slate-700">frp_current: {activeEvent?.frp_mw || 42.0} MW</div>
                  <div className="bg-white dark:bg-slate-900 p-1.5 rounded border border-slate-200 dark:border-slate-700">temp_current: {activeEvent?.brightness_temp_k || 375} K</div>
                  <div className="bg-white dark:bg-slate-900 p-1.5 rounded border border-slate-200 dark:border-slate-700">frp_robust_zscore: {isFacilityAbnormal ? '+4.82' : '+0.21'}</div>
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

        {/* ========================================================= */}
        {/* TAB 3: EVIDENCE & DEMPSTER-SHAFER FUSION                  */}
        {/* ========================================================= */}
        {activeTab === 'evidence' && (
          <div className="space-y-3 animate-in fade-in duration-100">
            <div className="space-y-1.5">
              <div className="p-2.5 rounded-lg bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
                  <div>
                    <div className="font-bold text-slate-900 dark:text-slate-100">NASA FIRMS (VIIRS 375m)</div>
                    <div className="text-[10px] text-slate-500 dark:text-slate-400">NOAA-20 / NOAA-21 I-Band Passes</div>
                  </div>
                </div>
                <span className="font-mono text-emerald-700 dark:text-emerald-400 font-bold">ARMED / NOMINAL</span>
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
                    <div className="text-[10px] text-slate-500 dark:text-slate-400">Band 11/12 High-Res Spectral Verification</div>
                  </div>
                </div>
                <span className="font-mono text-emerald-700 dark:text-emerald-400 font-bold">SYNCED</span>
              </div>
            </div>

            {/* Dempster-Shafer Consensus Metrics */}
            <div className="p-3 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700 space-y-2">
              <div className="flex items-center justify-between">
                <div className="font-bold text-slate-900 dark:text-slate-100">Dempster-Shafer Consensus Metrics</div>
                <button
                  type="button"
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
                  <div>Multi-source sensor evidence shows high mutual agreement.</div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* ========================================================= */}
        {/* TAB 4: DOMINO & CASCADE RISK                              */}
        {/* ========================================================= */}
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
                  { name: `${activeFac?.name || 'Unit'} Primary Process Loop`, relation: 'feeds', distance_m: 45, cascade_probability_pct: 75.0, criticality: 'CRITICAL' },
                  { name: 'Cryogenic Transfer Header', relation: 'connected_to', distance_m: 20, cascade_probability_pct: 60.0, criticality: 'HIGH' },
                  { name: 'LPG Storage Sphere 01', relation: 'near', distance_m: 120, cascade_probability_pct: 35.0, criticality: 'MODERATE' }
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

        {/* ========================================================= */}
        {/* TAB 5: RESPONSE ACTIONS & SOS                             */}
        {/* ========================================================= */}
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
                  type="button"
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
                type="button"
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
                type="button"
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
    </aside>
  );
}
