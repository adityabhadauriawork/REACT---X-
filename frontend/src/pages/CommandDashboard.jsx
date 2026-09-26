import React, { useState, useEffect, useMemo } from 'react';
import { api } from '../services/api';

import TopBar from '../components/layout/TopBar';
import MetricStrip from '../components/layout/MetricStrip';
import ToolMenu from '../components/layout/ToolMenu';
import CommandMapWorkspace from '../components/map/CommandMapWorkspace';
import ContextIntelligencePanel from '../components/panels/ContextIntelligencePanel';
import ExecutiveBriefModal from '../components/intelligence/ExecutiveBriefModal';
import EmergencyResponseModal from '../components/intelligence/EmergencyResponseModal';

export default function CommandDashboard({
  user,
  currentRole,
  onRoleChange,
  onLogout,
  onSwitchToDemo
}) {
  const [siteData, setSiteData] = useState(null);
  const [chemicals, setChemicals] = useState([]);
  const [presets, setPresets] = useState([]);
  
  // Satellite Datasets
  const [thermalEvents, setThermalEvents] = useState([]);
  const [thermalSources, setThermalSources] = useState([]);
  const [facilities, setFacilities] = useState([]);
  const [persistentClusters, setPersistentClusters] = useState([]);
  
  // Selections: Default to ALL_INDIA for Pan-India overview on startup
  const [selectedFacilityId, setSelectedFacilityId] = useState('ALL_INDIA');
  const [selectedEventId, setSelectedEventId] = useState(null);
  const [selectedSourceId, setSelectedSourceId] = useState(null);
  const [contextTab, setContextTab] = useState('overview');
  const [isContextPanelOpen, setIsContextPanelOpen] = useState(true);
  
  // Simulation & Plume states
  const [simulationResult, setSimulationResult] = useState(null);
  const [impactResult, setImpactResult] = useState(null);
  const [evacuationPlan, setEvacuationPlan] = useState(null);
  const [cascadePathways, setCascadePathways] = useState(null);
  const [currentTimeStep, setCurrentTimeStep] = useState(120);
  const [liveTelemetry, setLiveTelemetry] = useState(null);

  const [showExecutiveBrief, setShowExecutiveBrief] = useState(false);
  const [showSOSModal, setShowSOSModal] = useState(false);

  // Initial Data Fetch
  useEffect(() => {
    const fetchData = async () => {
      try {
        const [siteRes, chemsRes, presetsRes, weatherRes, thermalRes, sourcesRes, facsRes, clustersRes] = await Promise.all([
          api.getSiteData().catch(() => null),
          api.getChemicals().catch(() => []),
          api.getPresets().catch(() => []),
          api.getCurrentWeather(21.6850, 72.5750).catch(() => ({
            temperature_c: 32.0,
            wind_speed_kmh: 8.0,
            wind_direction_deg: 45.0,
            atmospheric_stability: 'D',
            is_live: true
          })),
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

        if (thermalRes && thermalRes.length > 0) {
          setSelectedEventId(thermalRes[0].event_id);
        }
      } catch (err) {
        console.error('Error fetching dashboard data:', err);
      }
    };
    fetchData();
  }, []);

  // Compute selected facility (null when ALL_INDIA)
  const isNationalView = selectedFacilityId === 'ALL_INDIA' || !selectedFacilityId;

  const activeFacility = useMemo(() => {
    if (isNationalView) return null;
    return facilities.find(f => f.id === selectedFacilityId) || facilities[0];
  }, [facilities, selectedFacilityId, isNationalView]);

  const activeThermalEvent = useMemo(() => {
    return thermalEvents.find(e => e.event_id === selectedEventId) || thermalEvents[0];
  }, [thermalEvents, selectedEventId]);

  const activeThermalSource = useMemo(() => {
    return thermalSources.find(s => s.source_id === selectedSourceId) || thermalSources[0];
  }, [thermalSources, selectedSourceId]);

  // Center coords and zoom based on selection
  const mapCenter = useMemo(() => {
    if (isNationalView) {
      return [22.8000, 79.5000]; // Center of India
    }
    if (activeFacility && activeFacility.coordinates) {
      return activeFacility.coordinates;
    }
    return [21.6850, 72.5750];
  }, [activeFacility, isNationalView]);

  const mapZoom = useMemo(() => {
    if (isNationalView) return 5;
    return 13;
  }, [isNationalView]);

  // Handle Search Result Selection
  const handleSearchSelect = (facilityItem) => {
    if (facilityItem && facilityItem.id) {
      setSelectedFacilityId(facilityItem.id);
      setIsContextPanelOpen(true);
    }
  };

  // Run Simulation Handler
  const handleRunSimulation = async () => {
    const facId = activeFacility ? activeFacility.id : 'FAC-DAHEJ-PCH01';
    try {
      const res = await api.runSimulation({
        facility_id: facId,
        asset_id: 'T-04',
        chemical_id: 'CHEM-NH3',
        release_type: 'CONTINUOUS_TOXIC_PLUME',
        release_rate_kg_s: 15.0,
        release_duration_sec: 1800,
        ambient_temperature_c: liveTelemetry?.temperature_c || 32.0,
        wind_speed_m_s: (liveTelemetry?.wind_speed_kmh || 8.0) / 3.6,
        wind_direction_deg: liveTelemetry?.wind_direction_deg || 45.0,
        atmospheric_stability: 'D'
      });
      setSimulationResult(res);
      return res;
    } catch (err) {
      console.warn('Simulation execution fallback:', err);
    }
  };

  // Generate Evacuation Handler
  const handleGenerateEvacuation = async () => {
    const facId = activeFacility ? activeFacility.id : 'FAC-DAHEJ-PCH01';
    try {
      const plan = await api.generateEvacuationRoute(facId, 'T-04');
      setEvacuationPlan(plan);
      return plan;
    } catch (err) {
      console.warn('Evacuation generation fallback:', err);
    }
  };

  // Export PDF Handler
  const handleExportPDF = async () => {
    const facId = activeFacility ? activeFacility.id : 'FAC-DAHEJ-PCH01';
    try {
      await api.exportPrePlanPDF(facId, 'T-04', 'CHEM-NH3');
    } catch (e) {
      console.warn('PDF export download error:', e);
      alert(`PDF export failed: ${e.message || 'Please check backend service.'}`);
    }
  };

  // Handle Tool Menu Action -> Switch Context Panel Tab
  const handleSelectTool = (toolKey) => {
    if (toolKey === 'emergency_sos') {
      setShowSOSModal(true);
      return;
    }
    if (toolKey === 'facilities_all') {
      setSelectedFacilityId('ALL_INDIA');
      setIsContextPanelOpen(true);
      return;
    }

    setIsContextPanelOpen(true);
    if (toolKey === 'live_thermal' || toolKey === 'facility_status' || toolKey === 'facilities_risk') {
      setContextTab('overview');
    } else if (toolKey === 'persistent_sources') {
      setContextTab('overview');
      if (thermalSources.length > 0) setSelectedSourceId(thermalSources[0].source_id);
    } else if (toolKey === 'source_classification') {
      setContextTab('classification');
    } else if (toolKey === 'satellite_comparison') {
      setContextTab('evidence');
    } else if (toolKey === 'domino_risk' || toolKey === 'impact_zones') {
      setContextTab('domino');
    } else if (toolKey === 'evacuation_support' || toolKey === 'resource_allocation' || toolKey === 'preplan_pdf') {
      setContextTab('response');
    }
  };

  return (
    <div className="h-screen w-screen bg-slate-100 dark:bg-slate-950 text-slate-900 dark:text-slate-100 flex flex-col font-sans overflow-hidden transition-colors">
      
      {/* 1. Top Bar */}
      <TopBar
        user={user}
        currentRole={currentRole}
        onRoleChange={onRoleChange}
        facilities={facilities}
        selectedFacilityId={selectedFacilityId}
        onSelectFacility={(id) => {
          setSelectedFacilityId(id);
          setIsContextPanelOpen(true);
        }}
        onSearchSelect={handleSearchSelect}
        onLogout={onLogout}
        onOpenExecutiveBrief={() => setShowExecutiveBrief(true)}
        onSwitchToDemo={onSwitchToDemo}
        liveTelemetry={liveTelemetry}
      />

      {/* 2. Top Metric Strip */}
      <MetricStrip
        facilities={facilities}
        thermalEvents={thermalEvents}
        thermalSources={thermalSources}
        persistentClusters={persistentClusters}
        simulationResult={simulationResult}
        onMetricClick={handleSelectTool}
      />

      {/* 3. Main Master Workspace (Map Canvas + Context Panel) */}
      <div className="flex-1 relative flex overflow-hidden w-full h-full">
        
        {/* Floating Tool Menu (Top Left of Map) */}
        <div className="absolute top-3 left-3 z-[400] pointer-events-auto">
          <ToolMenu onSelectTool={handleSelectTool} />
        </div>

        {/* Center: Dominant Map Canvas */}
        <div className="flex-1 h-full w-full relative bg-slate-100 dark:bg-slate-950">
          <CommandMapWorkspace
            center={mapCenter}
            zoom={mapZoom}
            facilities={facilities}
            thermalEvents={thermalEvents}
            thermalSources={thermalSources}
            persistentClusters={persistentClusters}
            simulationResult={simulationResult}
            currentTimeStep={currentTimeStep}
            onChangeTimeStep={setCurrentTimeStep}
            cascadePathways={cascadePathways}
            evacuationPlan={evacuationPlan}
            selectedFacilityId={selectedFacilityId}
            selectedEventId={selectedEventId}
            selectedSourceId={selectedSourceId}
            onSelectFacility={(id) => {
              setSelectedFacilityId(id);
              setIsContextPanelOpen(true);
            }}
            onSelectThermalEvent={(evt) => {
              setSelectedEventId(evt.event_id);
              if (evt.facility_id) setSelectedFacilityId(evt.facility_id);
              setIsContextPanelOpen(true);
            }}
            onSelectThermalSource={(src) => {
              setSelectedSourceId(src.source_id);
              setIsContextPanelOpen(true);
            }}
          />
        </div>

        {/* Right: Contextual Intelligence Side Panel */}
        {isContextPanelOpen && (
          <ContextIntelligencePanel
            event={activeThermalEvent}
            source={activeThermalSource}
            facility={activeFacility}
            isNationalOverview={isNationalView}
            thermalEvents={thermalEvents}
            thermalSources={thermalSources}
            facilities={facilities}
            initialTab={contextTab}
            simulationResult={simulationResult}
            cascadePathways={cascadePathways}
            onClose={() => setIsContextPanelOpen(false)}
            onSelectThermalEvent={(evt) => setSelectedEventId(evt.event_id)}
            onSelectFacility={(id) => {
              setSelectedFacilityId(id);
              setIsContextPanelOpen(true);
            }}
            onRunSimulation={handleRunSimulation}
            onGenerateEvacuation={handleGenerateEvacuation}
            onExportPDF={handleExportPDF}
            onOpenSOSModal={() => setShowSOSModal(true)}
          />
        )}
      </div>

      {/* 4. Executive Situation Brief Modal */}
      {showExecutiveBrief && (
        <ExecutiveBriefModal
          isOpen={showExecutiveBrief}
          onClose={() => setShowExecutiveBrief(false)}
          simulationResult={simulationResult}
          impactResult={impactResult}
          evacuationPlan={evacuationPlan}
          resourcePlan={null}
          authorizationRecord={null}
          onExportPDF={handleExportPDF}
        />
      )}

      {/* 5. Emergency Response / SOS Modal */}
      {showSOSModal && (
        <EmergencyResponseModal
          isOpen={showSOSModal}
          onClose={() => setShowSOSModal(false)}
          incidentPacket={null}
          facility={activeFacility || facilities[0]}
          isDemo={false}
          onExportPDF={handleExportPDF}
        />
      )}

    </div>
  );
}
