import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { api } from '../services/api';
import Header from '../components/common/Header';
import Sidebar from '../components/common/Sidebar';
import ActiveEventBanner from '../components/common/ActiveEventBanner';
import HUDStats from '../components/common/HUDStats';
import TimeScrubber from '../components/common/TimeScrubber';
import PlantMap from '../components/map/PlantMap';
import HomeOverview from '../components/dashboard/HomeOverview';
import SimulationLab from '../components/scenario/SimulationLab';
import IncidentIntelligencePanel from '../components/dashboard/IncidentIntelligencePanel';
import ScenarioBuilder from '../components/scenario/ScenarioBuilder';
import ImpactMatrix from '../components/impact/ImpactMatrix';
import EvacuationNavigator from '../components/evacuation/EvacuationNavigator';
import ResourceTactics from '../components/resources/ResourceTactics';
import PrePlanViewer from '../components/preplan/PrePlanViewer';
import IntelligenceHub from '../components/intelligence/IntelligenceHub';
import PreIncidentSafetyCenter from '../components/intelligence/PreIncidentSafetyCenter';
import DominoRiskAnalysis from '../components/intelligence/DominoRiskAnalysis';
import IncidentTimeline from '../components/intelligence/IncidentTimeline';
import DecisionAuditTrail from '../components/intelligence/DecisionAuditTrail';
import HistoricalAnalytics from '../components/intelligence/HistoricalAnalytics';
import ThermalIntelligenceHub from '../components/intelligence/ThermalIntelligenceHub';
import FacilityProfileModal from '../components/intelligence/FacilityProfileModal';
import EmergencyCopilotDrawer from '../components/copilot/EmergencyCopilotDrawer';

// Multi-Level Role Views & Executive Briefing
import FieldResponderView from '../components/roles/FieldResponderView';
import PlantDistrictAuthorityView from '../components/roles/PlantDistrictAuthorityView';
import ExecutiveAuthorityView from '../components/roles/ExecutiveAuthorityView';
import ExecutiveBriefModal from '../components/intelligence/ExecutiveBriefModal';
import { getCanonicalIncidentState, determineGlobalSystemState } from '../utils/canonicalState';

import { 
  Flame, Satellite, Building2, AlertTriangle, Siren, 
  BarChart3, ShieldCheck, Map, Sliders, Users, Navigation, 
  FileText, Clock, FileCheck, Cpu, Radio, ShieldAlert,
  Sparkles, RefreshCw, ChevronRight, CheckCircle2, Database 
} from 'lucide-react';

export default function CommandCenter() {
  const [siteData, setSiteData] = useState(null);
  const [chemicals, setChemicals] = useState([]);
  const [presets, setPresets] = useState([]);
  
  // Satellite Thermal Intelligence Datasets
  const [thermalEvents, setThermalEvents] = useState([]);
  const [thermalSources, setThermalSources] = useState([]);
  const [facilities, setFacilities] = useState([]);
  const [persistentClusters, setPersistentClusters] = useState([]);
  const [selectedThermalEventId, setSelectedThermalEventId] = useState('FIRMS-VIIRS-20260830-DHJ-01');
  const [selectedThermalSourceId, setSelectedThermalSourceId] = useState(null);
  const [selectedFacilityForModal, setSelectedFacilityForModal] = useState(null);
  const [showFacilityModal, setShowFacilityModal] = useState(false);

  // Single Source of Truth for Meteorology:
  const [liveTelemetry, setLiveTelemetry] = useState(null);
  const [weatherMode, setWeatherMode] = useState('LIVE');
  const [demoWeather, setDemoWeather] = useState({
    wind_speed_kmh: 8.0,
    wind_direction_deg: 45.0,
    wind_direction_cardinal: 'NE',
    ambient_temp_c: 32.0,
    atmospheric_stability: 'D'
  });
  const [isRefreshingWeather, setIsRefreshingWeather] = useState(false);
  
  // Active Simulation & Impact states (AUTHORITATIVE SINGLE SOURCE OF TRUTH)
  const [simulationResult, setSimulationResult] = useState(null);
  const [impactResult, setImpactResult] = useState(null);
  const [evacuationPlan, setEvacuationPlan] = useState(null);
  const [resourcePlan, setResourcePlan] = useState(null);
  
  // Prototype Role Selection & UI State
  const [currentRole, setCurrentRole] = useState('HSE_COMMANDER'); // FIELD_RESPONDER, HSE_COMMANDER, PLANT_MANAGER, DISTRICT_AUTHORITY, EXECUTIVE_AUTHORITY, DEMO_ADMIN
  const [showExecutiveBrief, setShowExecutiveBrief] = useState(false);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

  const [currentTimeStep, setCurrentTimeStep] = useState(120);
  const [selectedAssetId, setSelectedAssetId] = useState('T-04');

  // Navigation state (Default: Home Executive Overview)
  const [activeTab, setActiveTab] = useState('home');
  
  const [loading, setLoading] = useState(false);
  const [isExporting, setIsExporting] = useState(false);
  const [error, setError] = useState(null);

  // 1. Initial Data Fetching
  const loadInitialData = async () => {
    try {
      setLoading(true);
      setError(null);
      const [siteRes, chemsRes, presetsRes, weatherRes, thermalRes, sourcesRes, facsRes, clustersRes] = await Promise.all([
        api.getSiteData(),
        api.getChemicals(),
        api.getPresets(),
        api.getCurrentWeather(21.6850, 72.5750).catch(err => {
          console.warn('Weather fetch fallback active:', err);
          return {
            temperature_c: 32.0,
            wind_speed_kmh: 8.0,
            wind_direction_deg: 45.0,
            wind_direction_cardinal: 'NE',
            atmospheric_stability: 'D',
            source: 'Local Scenario Data (Offline Fallback)',
            is_live: false,
            timestamp: new Date().toISOString()
          };
        }),
        api.getThermalEvents().catch(() => []),
        api.getThermalSources().catch(() => []),
        api.getIndustrialFacilities().catch(() => []),
        api.getPersistentThermalSources().catch(() => [])
      ]);

      setSiteData(siteRes);
      setChemicals(chemsRes);
      setPresets(presetsRes);
      setLiveTelemetry(weatherRes);
      setThermalEvents(thermalRes);
      setThermalSources(sourcesRes);
      setFacilities(facsRes);
      setPersistentClusters(clustersRes);

      if (thermalRes.length > 0) {
        setSelectedThermalEventId(thermalRes[0].event_id);
      }
      if (sourcesRes.length > 0) {
        setSelectedThermalSourceId(sourcesRes[0].source_id);
      }
    } catch (err) {
      console.error('Failed to load initial data:', err);
      setError('Could not connect to FastAPI backend at http://127.0.0.1:8000. Please ensure the backend is running.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadInitialData();
  }, []);

  // Compute Active Meteorology Parameter Object
  const activeWeather = useMemo(() => {
    if (weatherMode === 'LIVE' && liveTelemetry) {
      return {
        mode: 'LIVE',
        wind_speed_kmh: liveTelemetry.wind_speed_kmh,
        wind_speed_m_s: liveTelemetry.wind_speed_m_s,
        wind_direction_deg: liveTelemetry.wind_direction_deg,
        wind_direction_cardinal: liveTelemetry.wind_direction_cardinal,
        temperature_c: liveTelemetry.temperature_c,
        atmospheric_stability: liveTelemetry.atmospheric_stability,
        source: liveTelemetry.source || 'Open-Meteo REST API',
        timestamp: liveTelemetry.timestamp
      };
    } else {
      const u_ms = Number((demoWeather.wind_speed_kmh / 3.6).toFixed(2));
      return {
        mode: 'DEMO',
        wind_speed_kmh: demoWeather.wind_speed_kmh,
        wind_speed_m_s: u_ms,
        wind_direction_deg: demoWeather.wind_direction_deg,
        wind_direction_cardinal: demoWeather.wind_direction_cardinal,
        temperature_c: demoWeather.ambient_temp_c,
        atmospheric_stability: demoWeather.atmospheric_stability,
        source: 'Scenario Override Parameter',
        timestamp: new Date().toISOString()
      };
    }
  }, [weatherMode, liveTelemetry, demoWeather]);

  const handleRefreshWeather = async () => {
    try {
      setIsRefreshingWeather(true);
      const res = await api.getCurrentWeather(21.6850, 72.5750);
      setLiveTelemetry(res);
    } catch (err) {
      console.error('Failed to refresh weather:', err);
    } finally {
      setIsRefreshingWeather(false);
    }
  };

  // Synchronized Simulation Execution (Downstream Emergency Response Layer)
  const executeSimulation = useCallback(async (scenarioParams) => {
    try {
      setLoading(true);
      setError(null);

      const simRes = await api.runSimulation(scenarioParams);
      setSimulationResult(simRes);
      setSelectedAssetId(simRes.source_asset_id);

      const impactRes = await api.analyzeImpact(simRes, 120);
      setImpactResult(impactRes);

      let originCoords = null;
      let originName = null;
      if (siteData?.assets) {
        const sourceAsset = siteData.assets.find(a => a.id === simRes.source_asset_id);
        if (sourceAsset) {
          originCoords = sourceAsset.coordinates;
          originName = sourceAsset.name;
        }
      }

      const [evacRes, resRes] = await Promise.all([
        api.calculateEvacuationRoute(simRes, impactRes, originCoords, originName),
        api.optimizeResources(simRes, impactRes)
      ]);

      setEvacuationPlan(evacRes);
      setResourcePlan(resRes);
      setCurrentTimeStep(120);

      // Transition to Map / Command
      setActiveTab('dashboard');

    } catch (err) {
      console.error('Simulation execution failed:', err);
      setError(err.message || 'Simulation execution encountered an error.');
    } finally {
      setLoading(false);
    }
  }, [siteData]);

  // Primary Demo Launcher (T-04 Ammonia Cryogenic Header Rupture)
  const handleLoadPrimaryDemo = () => {
    const t04Preset = presets.find(p => p.id === 'PRESET-AMMONIA-T04') || {
      asset_id: 'T-04',
      chemical_id: 'CHEM-NH3',
      incident_type: 'TOXIC_GAS_RELEASE',
      release_rate_kg_s: 18.5,
      release_duration_min: 30,
      wind_speed_m_s: activeWeather.wind_speed_m_s,
      wind_direction_deg: activeWeather.wind_direction_deg,
      ambient_temp_c: activeWeather.temperature_c,
      atmospheric_stability: activeWeather.atmospheric_stability
    };

    executeSimulation({
      ...t04Preset,
      wind_speed_m_s: activeWeather.wind_speed_m_s,
      wind_direction_deg: activeWeather.wind_direction_deg,
      ambient_temp_c: activeWeather.temperature_c,
      atmospheric_stability: activeWeather.atmospheric_stability
    });
  };

  // Satellite Thermal Anomaly -> Emergency Response Handoff Handler
  const handleInitiateHandoff = async (facility, hotspot) => {
    try {
      setShowFacilityModal(false);
      setLoading(true);

      const eventId = hotspot?.event_id || selectedThermalEventId;
      const facId = facility?.id || 'FAC-DAHEJ-PCH01';

      await api.executeThermalHandoff({
        event_id: eventId,
        facility_id: facId,
        initiator_role: currentRole,
        initiator_name: 'NTRO Thermal Watch Officer'
      });

      // Launch Authoritative Consequence Simulation for Target Asset
      executeSimulation({
        asset_id: 'T-04',
        chemical_id: 'CHEM-NH3',
        incident_type: 'TOXIC_GAS_RELEASE',
        release_rate_kg_s: 18.5,
        release_duration_min: 30,
        wind_speed_m_s: activeWeather.wind_speed_m_s,
        wind_direction_deg: activeWeather.wind_direction_deg,
        ambient_temp_c: activeWeather.temperature_c,
        atmospheric_stability: activeWeather.atmospheric_stability
      });

    } catch (err) {
      console.error('Emergency handoff failed:', err);
      alert('Emergency handoff bridge encountered an issue. Initiating direct command simulation.');
      handleLoadPrimaryDemo();
    } finally {
      setLoading(false);
    }
  };

  const handleOpenFacilityProfile = (facility) => {
    setSelectedFacilityForModal(facility);
    setShowFacilityModal(true);
  };

  const handleExportPDF = async () => {
    try {
      setIsExporting(true);
      await api.downloadPrePlanPDF({
        simulation_result: simulationResult,
        impact_result: impactResult,
        evacuation_plan: evacuationPlan,
        resource_plan: resourcePlan,
        author_name: 'REACT-X Autonomous Response Engine',
        facility_ref: 'PetroChem Complex Alpha (Dahej PCPIR)'
      });
    } catch (err) {
      console.error('PDF export failed:', err);
      alert('PDF export failed. Please ensure backend ReportLab engine is ready.');
    } finally {
      setIsExporting(false);
    }
  };

  // Global Navigation Switcher
  const navigateToTab = (tabId) => {
    if (tabId === 'executive_brief') {
      setShowExecutiveBrief(true);
      return;
    }
    if (tabId === 'context_dossier') {
      if (facilities.length > 0) {
        handleOpenFacilityProfile(facilities[0]);
      }
      return;
    }
    setActiveTab(tabId);
  };

  const canonicalState = useMemo(() => {
    return getCanonicalIncidentState({
      plantInfo: siteData?.plant,
      simulationResult,
      impactResult,
      evacuationPlan,
      resourcePlan,
      activeWeather,
      currentTimeStep
    });
  }, [siteData, simulationResult, impactResult, evacuationPlan, resourcePlan, activeWeather, currentTimeStep]);

  const globalSystemState = useMemo(() => {
    return determineGlobalSystemState({
      simulationResult,
      impactResult,
      thermalEvents,
      facilities
    });
  }, [simulationResult, impactResult, thermalEvents, facilities]);

  const isLiveData = useMemo(() => {
    return thermalEvents.some(e => e.is_live_data);
  }, [thermalEvents]);

  const abnormalCount = useMemo(() => {
    return thermalEvents.filter(e => e.abnormality_score >= 50.0 || e.risk_level === 'CRITICAL').length;
  }, [thermalEvents]);

  const activeFacilityHotspots = useMemo(() => {
    if (!selectedFacilityForModal) return [];
    return thermalEvents.filter(e => e.attributed_facility_id === selectedFacilityForModal.id);
  }, [selectedFacilityForModal, thermalEvents]);

  const selectedThermalEvent = useMemo(() => {
    return thermalEvents.find(e => e.event_id === selectedThermalEventId) || thermalEvents[0];
  }, [thermalEvents, selectedThermalEventId]);

  const selectedFacility = useMemo(() => {
    if (selectedThermalEvent?.attributed_facility_id) {
      return facilities.find(f => f.id === selectedThermalEvent.attributed_facility_id) || facilities[0];
    }
    return facilities[0];
  }, [facilities, selectedThermalEvent]);

  return (
    <div className="min-h-screen bg-[#060a12] text-slate-100 flex flex-col font-sans selection:bg-cyan-500/30">
      
      {/* 1. TOP GLOBAL APPLICATION HEADER */}
      <Header
        plantInfo={siteData?.plant}
        globalSystemState={globalSystemState}
        activeSimulation={simulationResult}
        impactResult={impactResult}
        activeWeather={activeWeather}
        liveTelemetry={liveTelemetry}
        isLiveData={isLiveData}
        currentRole={currentRole}
        onRoleChange={setCurrentRole}
        onOpenExecutiveBrief={() => setShowExecutiveBrief(true)}
        onRefreshWeather={handleRefreshWeather}
        isRefreshingWeather={isRefreshingWeather}
        onLoadPrimaryDemo={handleLoadPrimaryDemo}
        onExportPDF={handleExportPDF}
        isExporting={isExporting}
        loading={loading}
      />

      {/* Main Workspace with Left Sidebar */}
      <div className="flex-1 flex overflow-hidden">
        
        {/* 2. COLLAPSIBLE LEFT SIDEBAR NAVIGATION */}
        <Sidebar
          activeTab={activeTab}
          onNavigateTab={navigateToTab}
          activeThermalCount={thermalEvents.length}
          abnormalThermalCount={abnormalCount}
          isLiveData={isLiveData}
          collapsed={sidebarCollapsed}
          onToggleCollapse={() => setSidebarCollapsed(!sidebarCollapsed)}
        />

        {/* 3. CENTRAL CONTENT WORKSPACE */}
        <main className="flex-1 overflow-y-auto p-3 sm:p-4 space-y-2.5 custom-scrollbar">
          
          {/* Active Event Status Banner */}
          <ActiveEventBanner
            globalSystemState={globalSystemState}
            simulationResult={simulationResult}
            impactResult={impactResult}
            thermalEvents={thermalEvents}
            facilities={facilities}
            onNavigateTab={navigateToTab}
            onOpenFacilityProfile={handleOpenFacilityProfile}
          />

          {/* System Error Banner */}
          {error && (
            <div className="bg-red-950/80 border border-red-500/80 p-3 rounded-xl flex items-center justify-between text-xs text-red-200 shadow-lg font-mono">
              <div className="flex items-center space-x-2">
                <AlertTriangle className="w-4 h-4 text-red-400 shrink-0" />
                <span><b>SYSTEM ALERT:</b> {error}</span>
              </div>
              <button
                type="button"
                onClick={loadInitialData}
                className="flex items-center space-x-1 px-3 py-1 bg-red-900/60 hover:bg-red-800 border border-red-400/50 rounded font-bold transition-all text-xs"
              >
                <RefreshCw className="w-3 h-3" />
                <span>Retry</span>
              </button>
            </div>
          )}

          {/* ROLE-SPECIFIC VIEWS */}
          {currentRole === 'FIELD_RESPONDER' && (
            <FieldResponderView
              canonicalState={canonicalState}
              simulationResult={simulationResult}
              impactResult={impactResult}
              evacuationPlan={evacuationPlan}
              resourcePlan={resourcePlan}
              siteData={siteData}
              activeWeather={activeWeather}
              currentTimeStep={currentTimeStep}
              selectedAssetId={selectedAssetId}
              onSelectAsset={setSelectedAssetId}
            />
          )}

          {(currentRole === 'PLANT_MANAGER' || currentRole === 'DISTRICT_AUTHORITY') && (
            <PlantDistrictAuthorityView
              roleName={currentRole === 'PLANT_MANAGER' ? 'Plant General Manager' : 'District Emergency Authority'}
              canonicalState={canonicalState}
              simulationResult={simulationResult}
              impactResult={impactResult}
              evacuationPlan={evacuationPlan}
              resourcePlan={resourcePlan}
              siteData={siteData}
              activeWeather={activeWeather}
              currentTimeStep={currentTimeStep}
              selectedAssetId={selectedAssetId}
              onSelectAsset={setSelectedAssetId}
              onOpenExecutiveBrief={() => setShowExecutiveBrief(true)}
            />
          )}

          {currentRole === 'EXECUTIVE_AUTHORITY' && (
            <ExecutiveAuthorityView
              canonicalState={canonicalState}
              simulationResult={simulationResult}
              impactResult={impactResult}
              evacuationPlan={evacuationPlan}
              resourcePlan={resourcePlan}
              siteData={siteData}
              activeWeather={activeWeather}
              currentTimeStep={currentTimeStep}
              selectedAssetId={selectedAssetId}
              onSelectAsset={setSelectedAssetId}
              onExportPDF={handleExportPDF}
            />
          )}

          {/* PRIMARY COMMAND & INTELLIGENCE CENTER (HSE_COMMANDER / DEMO_ADMIN) */}
          {(currentRole === 'HSE_COMMANDER' || currentRole === 'DEMO_ADMIN') && (
            <>
              {/* Compact HUD Metric Bar (Answers the 5 core overview questions) */}
              <HUDStats
                canonicalState={canonicalState}
                impactResult={impactResult}
                simulationResult={simulationResult}
                resourcePlan={resourcePlan}
                thermalEvents={thermalEvents}
                facilities={facilities}
                persistentClusters={persistentClusters}
                isLiveData={isLiveData}
              />

              {/* VIEW 0: HOME — EXECUTIVE OVERVIEW & TASK LAUNCHER */}
              {activeTab === 'home' && (
                <HomeOverview
                  onNavigate={navigateToTab}
                  activeThermalCount={thermalEvents.length}
                  abnormalCount={1}
                  facilitiesCount={facilities.length || 10}
                  dataMode={isLiveData ? 'LIVE' : 'SIMULATION'}
                  onSelectFacility={handleOpenFacilityProfile}
                />
              )}

              {/* VIEW 1: OVERVIEW — COMMAND MAP & HOTSPOT TRIAGE */}
              {(activeTab === 'dashboard' || activeTab === 'response_command') && (
                <div className="grid grid-cols-1 lg:grid-cols-12 gap-3 items-stretch">
                  <div className="lg:col-span-8 xl:col-span-9 space-y-2.5 flex flex-col">
                    <div className="flex-1 min-h-[580px] h-[calc(100vh-270px)] rounded-xl overflow-hidden border border-slate-800 shadow-2xl">
                      <PlantMap
                        siteData={siteData}
                        simulationResult={simulationResult}
                        currentTimeStep={currentTimeStep}
                        evacuationPlan={evacuationPlan}
                        selectedAssetId={selectedAssetId}
                        onSelectAsset={setSelectedAssetId}
                        thermalEvents={thermalEvents}
                        thermalSources={thermalSources}
                        facilities={facilities}
                        persistentClusters={persistentClusters}
                        selectedEventId={selectedThermalEventId}
                        selectedSourceId={selectedThermalSourceId}
                        onSelectThermalEvent={(id) => {
                          setSelectedThermalEventId(id);
                        }}
                        onSelectThermalSource={(srcId) => {
                          setSelectedThermalSourceId(srcId);
                        }}
                        onOpenFacilityProfile={handleOpenFacilityProfile}
                        onInitiateHandoff={handleInitiateHandoff}
                      />
                    </div>
                    {simulationResult && (
                      <TimeScrubber
                        timeSteps={simulationResult.time_steps}
                        currentTimeStep={currentTimeStep}
                        onSelectTimeStep={setCurrentTimeStep}
                      />
                    )}
                  </div>

                  <div className="lg:col-span-4 xl:col-span-3 min-h-[580px] h-[calc(100vh-270px)] flex flex-col">
                    <IncidentIntelligencePanel
                      simulationResult={simulationResult}
                      impactResult={impactResult}
                      evacuationPlan={evacuationPlan}
                      resourcePlan={resourcePlan}
                      activeWeather={activeWeather}
                      liveTelemetry={liveTelemetry}
                      weatherMode={weatherMode}
                      onWeatherModeChange={setWeatherMode}
                      presets={presets}
                      onSelectPreset={(p) => executeSimulation({
                        ...p,
                        wind_speed_m_s: activeWeather.wind_speed_m_s,
                        wind_direction_deg: activeWeather.wind_direction_deg,
                        ambient_temp_c: activeWeather.temperature_c,
                        atmospheric_stability: activeWeather.atmospheric_stability
                      })}
                      onNavigateTab={navigateToTab}
                      onRunSimulation={executeSimulation}
                      loading={loading}
                      selectedThermalEvent={selectedThermalEvent}
                      selectedFacility={selectedFacility}
                      onOpenFacilityProfile={handleOpenFacilityProfile}
                      onInitiateHandoff={handleInitiateHandoff}
                    />
                  </div>
                </div>
              )}

              {/* VIEW 2: THERMAL INTELLIGENCE SUITE */}
              {(activeTab === 'thermal_live' || activeTab === 'thermal_sources' || activeTab === 'thermal_firms' || activeTab === 'thermal_classification' || activeTab === 'thermal_persistence') && (
                <ThermalIntelligenceHub
                  initialTab={
                    activeTab === 'thermal_sources'
                      ? 'sources'
                      : (activeTab === 'thermal_firms' 
                          ? 'live_events' 
                          : (activeTab === 'thermal_classification' 
                              ? 'classification' 
                              : (activeTab === 'thermal_persistence' ? 'persistence' : 'sources')))
                  }
                  onSelectHotspot={setSelectedThermalEventId}
                  onInitiateHandoff={handleInitiateHandoff}
                  onOpenFacilityProfile={handleOpenFacilityProfile}
                />
              )}

              {/* VIEW 3: INDUSTRIAL CONTEXT — FACILITIES & INFRASTRUCTURE */}
              {(activeTab === 'context_facilities' || activeTab === 'context_infrastructure') && (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3 font-mono text-xs">
                  {facilities.map((fac) => {
                    const isAbnormal = fac.current_status !== 'NOMINAL_OPERATIONS' || fac.current_abnormality_score > 30.0;
                    return (
                      <div 
                        key={fac.id} 
                        className={`p-3.5 rounded-xl border space-y-2.5 transition-all cursor-pointer ${
                          isAbnormal ? 'bg-red-950/40 border-red-500/60 shadow-lg' : 'bg-slate-950/80 border-slate-800 hover:border-slate-700'
                        }`}
                        onClick={() => handleOpenFacilityProfile(fac)}
                      >
                        <div className="flex justify-between items-center">
                          <span className="px-1.5 py-0.2 rounded bg-cyan-500/10 text-cyan-300 font-bold text-[10px] border border-cyan-500/30">
                            {fac.id}
                          </span>
                          <span className={`px-2 py-0.2 rounded text-[9px] font-bold border ${
                            isAbnormal ? 'bg-red-500/20 text-red-300 border-red-500/50' : 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40'
                          }`}>
                            {fac.current_status.replace('_', ' ')}
                          </span>
                        </div>

                        <div>
                          <h4 className="font-extrabold text-white text-xs">{fac.name}</h4>
                          <span className="text-[10px] text-slate-400">{fac.operator_name} • {fac.district}</span>
                        </div>

                        <div className="grid grid-cols-2 gap-2 text-[10px] bg-slate-900/80 p-2 rounded-lg border border-slate-800">
                          <div>
                            <span className="text-slate-500 block text-[9px]">BASELINE FRP</span>
                            <span className="text-amber-400 font-bold">{fac.baseline_mean_frp_mw} MW</span>
                          </div>
                          <div>
                            <span className="text-slate-500 block text-[9px]">ABNORMALITY</span>
                            <span className={`font-bold ${isAbnormal ? 'text-red-400' : 'text-emerald-400'}`}>
                              {fac.current_abnormality_score.toFixed(1)}%
                            </span>
                          </div>
                        </div>

                        <div className="flex items-center justify-between text-[10px] text-slate-500 pt-1 border-t border-slate-800">
                          <span>Radius: {fac.fence_radius_m}m</span>
                          <span className="text-cyan-400 flex items-center gap-0.5 font-bold">
                            View Profile <ChevronRight className="w-3 h-3" />
                          </span>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}

              {/* VIEW 4: INDUSTRIAL CONTEXT — PRE-INCIDENT SAFETY CENTER */}
              {activeTab === 'safety_center' && (
                <PreIncidentSafetyCenter
                  onNavigateToSimulator={(assetId) => {
                    setSelectedAssetId(assetId);
                    navigateToTab('simulator');
                  }}
                  onNavigateToEvacuation={() => navigateToTab('evacuation')}
                />
              )}

              {/* VIEW: SIMULATION LAB & REFERENCE ENVIRONMENT */}
              {(activeTab === 'simulation' || activeTab === 'demo') && (
                <SimulationLab onNavigate={navigateToTab} />
              )}

              {/* VIEW 5: RISK & PREDICTION — WHAT-IF SIMULATOR */}
              {(activeTab === 'simulator' || activeTab === 'risk_baselines') && (
                <div className="grid grid-cols-1 lg:grid-cols-12 gap-3 items-start">
                  <div className="lg:col-span-7">
                    <ScenarioBuilder
                      assets={siteData?.assets}
                      chemicals={chemicals}
                      presets={presets}
                      weatherMode={weatherMode}
                      onWeatherModeChange={setWeatherMode}
                      liveTelemetry={liveTelemetry}
                      demoWeather={demoWeather}
                      onDemoWeatherChange={setDemoWeather}
                      onRefreshWeather={handleRefreshWeather}
                      isRefreshingWeather={isRefreshingWeather}
                      onRunSimulation={executeSimulation}
                      loading={loading}
                      selectedAssetId={selectedAssetId}
                      onSelectAsset={setSelectedAssetId}
                    />
                  </div>
                  <div className="lg:col-span-5 min-h-[560px] h-[calc(100vh-270px)] rounded-xl overflow-hidden border border-slate-800 shadow-xl">
                    <PlantMap
                      siteData={siteData}
                      simulationResult={simulationResult}
                      currentTimeStep={currentTimeStep}
                      evacuationPlan={evacuationPlan}
                      selectedAssetId={selectedAssetId}
                      onSelectAsset={setSelectedAssetId}
                      thermalEvents={thermalEvents}
                      facilities={facilities}
                      persistentClusters={persistentClusters}
                      selectedEventId={selectedThermalEventId}
                      onSelectThermalEvent={setSelectedThermalEventId}
                      onOpenFacilityProfile={handleOpenFacilityProfile}
                      onInitiateHandoff={handleInitiateHandoff}
                    />
                  </div>
                </div>
              )}

              {/* VIEW 6: RISK & PREDICTION — DOMINO / CASCADE RISK */}
              {activeTab === 'domino' && (
                <div className="grid grid-cols-1 lg:grid-cols-12 gap-3 items-start">
                  <div className="lg:col-span-7">
                    <DominoRiskAnalysis
                      simulationResult={simulationResult}
                      impactResult={impactResult}
                    />
                  </div>
                  <div className="lg:col-span-5 min-h-[560px] h-[calc(100vh-270px)] rounded-xl overflow-hidden border border-slate-800 shadow-xl">
                    <PlantMap
                      siteData={siteData}
                      simulationResult={simulationResult}
                      currentTimeStep={currentTimeStep}
                      evacuationPlan={evacuationPlan}
                      selectedAssetId={selectedAssetId}
                      onSelectAsset={setSelectedAssetId}
                      thermalEvents={thermalEvents}
                      facilities={facilities}
                      persistentClusters={persistentClusters}
                      selectedEventId={selectedThermalEventId}
                      onSelectThermalEvent={setSelectedThermalEventId}
                      onOpenFacilityProfile={handleOpenFacilityProfile}
                      onInitiateHandoff={handleInitiateHandoff}
                    />
                  </div>
                </div>
              )}

              {/* VIEW 7: RESPONSE — IMPACT & PERSONNEL */}
              {activeTab === 'impact' && (
                <div className="grid grid-cols-1 lg:grid-cols-12 gap-3 items-start">
                  <div className="lg:col-span-7">
                    <ImpactMatrix impactResult={impactResult} />
                  </div>
                  <div className="lg:col-span-5 min-h-[560px] h-[calc(100vh-270px)] rounded-xl overflow-hidden border border-slate-800 shadow-xl">
                    <PlantMap
                      siteData={siteData}
                      simulationResult={simulationResult}
                      currentTimeStep={currentTimeStep}
                      evacuationPlan={evacuationPlan}
                      selectedAssetId={selectedAssetId}
                      onSelectAsset={setSelectedAssetId}
                      thermalEvents={thermalEvents}
                      facilities={facilities}
                      persistentClusters={persistentClusters}
                      selectedEventId={selectedThermalEventId}
                      onSelectThermalEvent={setSelectedThermalEventId}
                      onOpenFacilityProfile={handleOpenFacilityProfile}
                      onInitiateHandoff={handleInitiateHandoff}
                    />
                  </div>
                </div>
              )}

              {/* VIEW 8: RESPONSE — SAFE EVACUATION */}
              {activeTab === 'evacuation' && (
                <div className="grid grid-cols-1 lg:grid-cols-12 gap-3 items-start">
                  <div className="lg:col-span-6">
                    <EvacuationNavigator evacuationPlan={evacuationPlan} />
                  </div>
                  <div className="lg:col-span-6 min-h-[580px] h-[calc(100vh-270px)] rounded-xl overflow-hidden border border-slate-800 shadow-xl">
                    <PlantMap
                      siteData={siteData}
                      simulationResult={simulationResult}
                      currentTimeStep={currentTimeStep}
                      evacuationPlan={evacuationPlan}
                      selectedAssetId={selectedAssetId}
                      onSelectAsset={setSelectedAssetId}
                      thermalEvents={thermalEvents}
                      facilities={facilities}
                      persistentClusters={persistentClusters}
                      selectedEventId={selectedThermalEventId}
                      onSelectThermalEvent={setSelectedThermalEventId}
                      onOpenFacilityProfile={handleOpenFacilityProfile}
                      onInitiateHandoff={handleInitiateHandoff}
                    />
                  </div>
                </div>
              )}

              {/* VIEW 9: RESPONSE — TACTICAL RESOURCE DISPATCH */}
              {activeTab === 'resources' && (
                <div className="grid grid-cols-1 lg:grid-cols-12 gap-3 items-start">
                  <div className="lg:col-span-7">
                    <ResourceTactics resourcePlan={resourcePlan} />
                  </div>
                  <div className="lg:col-span-5 min-h-[560px] h-[calc(100vh-270px)] rounded-xl overflow-hidden border border-slate-800 shadow-xl">
                    <PlantMap
                      siteData={siteData}
                      simulationResult={simulationResult}
                      currentTimeStep={currentTimeStep}
                      evacuationPlan={evacuationPlan}
                      selectedAssetId={selectedAssetId}
                      onSelectAsset={setSelectedAssetId}
                      thermalEvents={thermalEvents}
                      facilities={facilities}
                      persistentClusters={persistentClusters}
                      selectedEventId={selectedThermalEventId}
                      onSelectThermalEvent={setSelectedThermalEventId}
                      onOpenFacilityProfile={handleOpenFacilityProfile}
                      onInitiateHandoff={handleInitiateHandoff}
                    />
                  </div>
                </div>
              )}

              {/* VIEW 10: RESPONSE — FIRE PRE-PLAN DOCUMENT */}
              {activeTab === 'preplan' && (
                <PrePlanViewer
                  plantInfo={siteData?.plant}
                  simulationResult={simulationResult}
                  impactResult={impactResult}
                  evacuationPlan={evacuationPlan}
                  resourcePlan={resourcePlan}
                  onExportPDF={handleExportPDF}
                  isExporting={isExporting}
                />
              )}

              {/* VIEW 11: ANALYSIS & GOVERNANCE — HISTORICAL ANALYTICS */}
              {activeTab === 'analytics' && (
                <HistoricalAnalytics />
              )}

              {/* VIEW 12: ANALYSIS & GOVERNANCE — INCIDENT TIMELINE */}
              {activeTab === 'timeline' && (
                <IncidentTimeline
                  simulationResult={simulationResult}
                  impactResult={impactResult}
                  evacuationPlan={evacuationPlan}
                  resourcePlan={resourcePlan}
                  authorizationStatus={null}
                />
              )}

              {/* VIEW 13: ANALYSIS & GOVERNANCE — DECISION AUDIT TRAIL */}
              {activeTab === 'audit' && (
                <DecisionAuditTrail incidentId={simulationResult?.id} />
              )}

              {/* VIEW 14: ANALYSIS & GOVERNANCE — HUMAN AUTHORIZATION & FEED HEALTH */}
              {(activeTab === 'authorization' || activeTab === 'system_health') && (
                <div className="bg-slate-950/80 rounded-xl border border-slate-800 p-4 space-y-3 font-mono text-xs shadow-xl">
                  <div className="flex justify-between items-center border-b border-slate-800 pb-2">
                    <span className="font-bold text-white uppercase flex items-center gap-2">
                      <Database className="w-4 h-4 text-cyan-400" />
                      REACT-X Multi-Modal Telemetry & Ingestion Pipeline Status
                    </span>
                    <span className="text-emerald-400 font-bold">ALL FEEDS OPERATIONAL</span>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-[11px]">
                    <div className="bg-slate-900/60 p-3 rounded-lg border border-slate-800 space-y-1.5">
                      <div className="flex justify-between">
                        <span className="text-slate-400">NASA FIRMS VIIRS (S-NPP / NOAA-20):</span>
                        <span className="text-emerald-400 font-bold">ACTIVE (375m I-Band)</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-slate-400">NASA FIRMS MODIS (Terra / Aqua):</span>
                        <span className="text-emerald-400 font-bold">ACTIVE (1km Thermal)</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-slate-400">VIIRS Nightfire (EOG Academic):</span>
                        <span className="text-amber-300 font-bold text-[10px]">ACADEMIC DATA / OFFLINE VALIDATION</span>
                      </div>
                    </div>

                    <div className="bg-slate-900/60 p-3 rounded-lg border border-slate-800 space-y-1.5">
                      <div className="flex justify-between">
                        <span className="text-slate-400">Sentinel-2 Copernicus SWIR (20m):</span>
                        <span className="text-cyan-300 font-bold">SYNCED</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-slate-400">INSAT-3DR Geostationary TIR:</span>
                        <span className="text-emerald-400 font-bold">ACTIVE (15m Scans)</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-slate-400">OSM / GEM Industrial Facilities:</span>
                        <span className="text-white font-bold">{facilities.length} Complexes Indexed</span>
                      </div>
                    </div>
                  </div>
                </div>
              )}

            </>
          )}

        </main>
      </div>

      {/* Floating AI Copilot Drawer */}
      <EmergencyCopilotDrawer
        simulationResult={simulationResult}
        impactResult={impactResult}
        evacuationPlan={evacuationPlan}
        resourcePlan={resourcePlan}
        userRole={currentRole}
        onNavigateTab={navigateToTab}
      />

      {/* Global Executive Situation Brief Modal */}
      <ExecutiveBriefModal
        isOpen={showExecutiveBrief}
        onClose={() => setShowExecutiveBrief(false)}
        simulationResult={simulationResult}
        impactResult={impactResult}
        evacuationPlan={evacuationPlan}
        resourcePlan={resourcePlan}
        authorizationRecord={null}
        onExportPDF={handleExportPDF}
      />

      {/* Global Industrial Facility Profile Dossier Modal */}
      <FacilityProfileModal
        isOpen={showFacilityModal}
        onClose={() => setShowFacilityModal(false)}
        facility={selectedFacilityForModal}
        activeHotspots={activeFacilityHotspots}
        onInitiateHandoff={handleInitiateHandoff}
      />

    </div>
  );
}
