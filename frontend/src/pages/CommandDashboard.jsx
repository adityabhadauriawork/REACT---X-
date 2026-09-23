import React, { useState, useEffect, useMemo } from 'react';
import { api } from '../services/api';

import TopBar from '../components/layout/TopBar';
import MetricStrip from '../components/layout/MetricStrip';
import ToolMenu from '../components/layout/ToolMenu';
import CommandMapWorkspace from '../components/map/CommandMapWorkspace';
import ContextIntelligencePanel from '../components/panels/ContextIntelligencePanel';
import ExecutiveBriefModal from '../components/intelligence/ExecutiveBriefModal';

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
  
  // Selections
  const [selectedFacilityId, setSelectedFacilityId] = useState('FAC-IN-DAHEJ-001');
  const [selectedEventId, setSelectedEventId] = useState(null);
  const [selectedSourceId, setSelectedSourceId] = useState(null);
  const [contextTab, setContextTab] = useState('overview');
  const [isContextPanelOpen, setIsContextPanelOpen] = useState(true);
  
  // Simulation & Plume states
  const [simulationResult, setSimulationResult] = useState(null);
  const [impactResult, setImpactResult] = useState(null);
  const [evacuationPlan, setEvacuationPlan] = useState(null);
  const [currentTimeStep, setCurrentTimeStep] = useState(120);
  const [liveTelemetry, setLiveTelemetry] = useState(null);

  const [showExecutiveBrief, setShowExecutiveBrief] = useState(false);

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

        if (facsRes && facsRes.length > 0) {
          setSelectedFacilityId(facsRes[0].id);
        }
        if (thermalRes && thermalRes.length > 0) {
          setSelectedEventId(thermalRes[0].event_id);
        }
      } catch (err) {
        console.error('Error fetching dashboard data:', err);
      }
    };
    fetchData();
  }, []);

  // Compute selected items
  const activeFacility = useMemo(() => {
    return facilities.find(f => f.id === selectedFacilityId) || facilities[0] || {
      id: 'FAC-IN-DAHEJ-001',
      name: 'Dahej Petrochemical Complex',
      location: 'Dahej PCPIR, Gujarat',
      coordinates: [21.6850, 72.5750],
      current_status: 'NOMINAL_OPERATIONS',
      current_abnormality_score: 12.0
    };
  }, [facilities, selectedFacilityId]);

  const activeThermalEvent = useMemo(() => {
    return thermalEvents.find(e => e.event_id === selectedEventId) || thermalEvents[0];
  }, [thermalEvents, selectedEventId]);

  const activeThermalSource = useMemo(() => {
    return thermalSources.find(s => s.source_id === selectedSourceId) || thermalSources[0];
  }, [thermalSources, selectedSourceId]);

  // Center coords on selected facility or default India industrial corridor
  const mapCenter = useMemo(() => {
    if (activeFacility && activeFacility.coordinates) {
      return activeFacility.coordinates;
    }
    return [21.6850, 72.5750];
  }, [activeFacility]);

  // Handle Search Result Selection
  const handleSearchSelect = (facilityItem) => {
    if (facilityItem && facilityItem.id) {
      setSelectedFacilityId(facilityItem.id);
      setIsContextPanelOpen(true);
    }
  };

  // Run Simulation Handler
  const handleRunSimulation = async () => {
    try {
      const res = await api.runSimulation({
        facility_id: selectedFacilityId,
        asset_id: 'T-04',
        chemical_id: 'CH-NH3',
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
    try {
      const plan = await api.generateEvacuationRoute(selectedFacilityId, 'T-04');
      setEvacuationPlan(plan);
      return plan;
    } catch (err) {
      console.warn('Evacuation generation fallback:', err);
    }
  };

  // Export PDF Handler
  const handleExportPDF = async () => {
    try {
      const blob = await api.exportPrePlanPDF(selectedFacilityId, 'T-04', 'CH-NH3');
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `REACT-X_ERDMP_Plan_${selectedFacilityId}.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
    } catch (e) {
      console.warn('PDF export download fallback:', e);
      window.open(`/api/preplan/export/pdf?facility_id=${selectedFacilityId}&asset_id=T-04`, '_blank');
    }
  };

  // Handle Tool Menu Action -> Switch Context Panel Tab
  const handleSelectTool = (toolKey) => {
    setIsContextPanelOpen(true);
    
    if (toolKey === 'live_thermal' || toolKey === 'facility_status') {
      setContextTab('overview');
    } else if (toolKey === 'persistent_sources') {
      setContextTab('overview');
      if (thermalSources.length > 0) setSelectedSourceId(thermalSources[0].source_id);
    } else if (toolKey === 'source_classification' || toolKey === 'satellite_comparison' || toolKey === 'historical_analysis') {
      setContextTab('evidence');
    } else if (toolKey === 'hazard_prediction' || toolKey === 'preventive_whatif' || toolKey === 'trend_analysis') {
      setContextTab('prediction');
    } else if (toolKey === 'domino_risk' || toolKey === 'impact_zones') {
      setContextTab('consequence');
    } else if (toolKey === 'evacuation_support' || toolKey === 'resource_allocation' || toolKey === 'preplan_pdf') {
      setContextTab('response');
    }
  };

  return (
    <div className="h-screen w-screen bg-slate-100 text-slate-900 flex flex-col font-sans overflow-hidden">
      
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

      {/* 2. Top 5-Metric Strip */}
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

        {/* Center: Dominant Light GIS Map Canvas */}
        <div className="flex-1 h-full w-full relative">
          <CommandMapWorkspace
            center={mapCenter}
            zoom={14}
            facilities={facilities}
            thermalEvents={thermalEvents}
            thermalSources={thermalSources}
            persistentClusters={persistentClusters}
            simulationResult={simulationResult}
            currentTimeStep={currentTimeStep}
            onChangeTimeStep={setCurrentTimeStep}
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

        {/* Right: Redesigned Contextual Intelligence Side Panel */}
        {isContextPanelOpen && (
          <ContextIntelligencePanel
            event={activeThermalEvent}
            source={activeThermalSource}
            facility={activeFacility}
            thermalEvents={thermalEvents}
            thermalSources={thermalSources}
            facilities={facilities}
            initialTab={contextTab}
            simulationResult={simulationResult}
            onClose={() => setIsContextPanelOpen(false)}
            onSelectThermalEvent={(evt) => setSelectedEventId(evt.event_id)}
            onSelectFacility={(id) => setSelectedFacilityId(id)}
            onRunSimulation={handleRunSimulation}
            onGenerateEvacuation={handleGenerateEvacuation}
            onExportPDF={handleExportPDF}
          />
        )}
      </div>

      {/* 4. Executive Situation Brief Modal (Clean Light Theme) */}
      {showExecutiveBrief && (
        <ExecutiveBriefModal
          isOpen={showExecutiveBrief}
          onClose={() => setShowExecutiveBrief(false)}
          siteData={siteData}
          simulationResult={simulationResult}
          impactResult={impactResult}
          evacuationPlan={evacuationPlan}
          currentRole={currentRole}
        />
      )}

    </div>
  );
}
