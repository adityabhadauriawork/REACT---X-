import React, { useEffect, useState, useMemo } from 'react';
import { 
  MapContainer, TileLayer, GeoJSON, Marker, 
  Popup, Polyline, Circle, Tooltip, useMap 
} from 'react-leaflet';
import L from 'leaflet';
import { 
  Layers, Eye, EyeOff, Shield, Flame, 
  Users, Navigation, Droplets, MapPin, Compass,
  Satellite, Building2, Radio, Activity, Cpu, Siren 
} from 'lucide-react';

// Custom Map Controller to smoothly pan/zoom when coordinates change
function MapRecenter({ center, zoom }) {
  const map = useMap();
  useEffect(() => {
    if (center && center[0] && center[1]) {
      map.setView(center, zoom || 15, { animate: true });
    }
  }, [center, zoom, map]);
  return null;
}

export default function PlantMap({ 
  siteData, 
  simulationResult, 
  currentTimeStep = 120, 
  evacuationPlan, 
  selectedAssetId, 
  onSelectAsset,
  thermalEvents = [],
  thermalSources = [],
  facilities = [],
  persistentClusters = [],
  selectedEventId,
  selectedSourceId,
  onSelectThermalEvent,
  onSelectThermalSource,
  onOpenFacilityProfile,
  onInitiateHandoff
}) {
  // Layer visibility toggles
  const [layers, setLayers] = useState({
    thermalSources: true,
    satelliteHotspots: true,
    facilities: true,
    persistentClusters: true,
    threatZones: true,
    evacuationRoute: true,
    assets: true,
    workers: true,
    roads: true,
    assemblyPoints: true,
    gates: true,
    resources: true,
    boundary: true
  });

  const [showLayerPanel, setShowLayerPanel] = useState(false);

  const plant = siteData?.plant;
  const centerCoords = useMemo(() => {
    return plant?.center ? [plant.center[0], plant.center[1]] : [21.6850, 72.5750];
  }, [plant]);

  // Create custom DivIcons
  const createIcon = (htmlContent, className = '', size = [32, 32]) => {
    return L.divIcon({
      html: htmlContent,
      className: `custom-leaflet-icon ${className}`,
      iconSize: size,
      iconAnchor: [size[0] / 2, size[1] / 2],
      popupAnchor: [0, -size[1] / 2]
    });
  };

  // 1. Satellite Thermal Anomaly Icon Generator
  const hotspotIcon = (event, isSelected) => {
    const isFire = event.classification === 'INDUSTRIAL_FIRE' || event.abnormality_score >= 80.0;
    const isFlare = event.classification === 'GAS_FLARE';
    const isMining = event.classification === 'MINING_PROCESS_HEAT';
    const isAgri = event.classification === 'AGRICULTURAL_BURNING';
    const isRoutine = event.classification === 'ROUTINE_PROCESS_HEAT';

    let colorClass = 'bg-amber-500 border-amber-300 text-slate-950';
    let ringClass = 'ring-2 ring-amber-400/60';
    let label = '🔥';

    if (isFire) {
      colorClass = 'bg-red-600 border-red-300 text-white animate-pulse';
      ringClass = 'ring-4 ring-red-500/80 animate-ping';
      label = '🚨';
    } else if (isFlare) {
      colorClass = 'bg-orange-500 border-orange-300 text-slate-950';
      ringClass = 'ring-2 ring-orange-400/70';
      label = '⚡';
    } else if (isRoutine) {
      colorClass = 'bg-purple-600 border-purple-300 text-white';
      ringClass = 'ring-2 ring-purple-400/60';
      label = '🏭';
    } else if (isMining) {
      colorClass = 'bg-amber-700 border-amber-400 text-white';
      label = '⛏️';
    } else if (isAgri) {
      colorClass = 'bg-yellow-500 border-yellow-300 text-slate-950';
      label = '🌾';
    }

    if (isSelected) {
      ringClass += ' ring-offset-2 ring-offset-black ring-cyan-400';
    }

    const html = `
      <div class="relative flex items-center justify-center w-8 h-8 rounded-full border-2 shadow-2xl font-mono text-xs font-black ${colorClass} ${ringClass} transition-all">
        <span>${label}</span>
        <span class="absolute -top-1.5 -right-1 px-1 rounded bg-black/90 text-cyan-300 text-[8px] font-bold border border-cyan-500/50">
          ${event.frp_mw ? Math.round(event.frp_mw) : ''}M
        </span>
      </div>
    `;
    return createIcon(html, '', [32, 32]);
  };

  // 1b. Thermal Source Object (Spatiotemporal Cluster & Abnormality) Icon Generator
  const thermalSourceIcon = (src, isSelected) => {
    const isAbnormal = src.abnormality_status === 'ABNORMAL_THERMAL_BEHAVIOUR' || (src.abnormality_score && src.abnormality_score >= 65.0);
    const isWatch = src.abnormality_status === 'WATCH' || (src.abnormality_score && src.abnormality_score >= 35.0);
    const isPersistent = src.source_status === 'PERSISTENT_SOURCE';
    const isRecurring = src.source_status === 'RECURRING_SOURCE';
    
    let colorClass = 'bg-cyan-500 border-cyan-300 text-slate-950';
    let ringClass = 'ring-2 ring-cyan-400/60';
    let label = '✨';

    if (isAbnormal) {
      colorClass = 'bg-rose-600 border-rose-300 text-white animate-pulse';
      ringClass = 'ring-4 ring-rose-500/80 shadow-rose-900/50';
      label = '🚨';
    } else if (isWatch) {
      colorClass = 'bg-amber-500 border-amber-300 text-slate-950';
      ringClass = 'ring-3 ring-amber-400/80';
      label = '⚠️';
    } else if (isPersistent) {
      colorClass = 'bg-purple-600 border-purple-300 text-white';
      ringClass = 'ring-2 ring-purple-500/50';
      label = '⚡';
    } else if (isRecurring) {
      colorClass = 'bg-indigo-600 border-indigo-300 text-white';
      ringClass = 'ring-2 ring-indigo-400/50';
      label = '🔥';
    }

    if (isSelected) {
      ringClass += ' ring-offset-2 ring-offset-black ring-cyan-400';
    }

    const html = `
      <div class="relative flex items-center justify-center w-8 h-8 rounded-lg border-2 shadow-2xl font-mono text-xs font-black ${colorClass} ${ringClass} transition-all">
        <span>${label}</span>
        <span class="absolute -top-1.5 -right-1 px-1 rounded bg-black/90 text-cyan-300 text-[8px] font-bold border border-cyan-500/50">
          ${src.observation_count || 1}x
        </span>
      </div>
    `;
    return createIcon(html, '', [32, 32]);
  };

  // 2. Industrial Facility Marker Icon
  const facilityIcon = (fac) => {
    const isAbnormal = fac.current_status !== 'NOMINAL_OPERATIONS' || fac.current_abnormality_score > 30.0;
    const bg = isAbnormal ? 'bg-red-950 border-red-500 text-red-400' : 'bg-cyan-950 border-cyan-500 text-cyan-300';
    const html = `
      <div class="flex items-center space-x-1 px-2 py-1 rounded-lg border shadow-xl font-mono text-[9px] font-bold ${bg} backdrop-blur-md">
        <span>🏭</span>
        <span class="truncate max-w-[100px]">${fac.name.split(' - ')[0]}</span>
      </div>
    `;
    return createIcon(html, '', [120, 24]);
  };

  // 3. Plant Asset Icon
  const assetIcon = (asset, isSelected, isSource) => {
    let bg = 'bg-slate-900 border-slate-600 text-slate-200';
    let ring = '';

    if (isSource) {
      bg = 'bg-red-950 border-red-500 text-red-300 animate-pulse';
      ring = 'ring-4 ring-red-500/50';
    } else if (isSelected) {
      bg = 'bg-cyan-950 border-cyan-400 text-cyan-300';
      ring = 'ring-2 ring-cyan-400';
    } else if (asset.type === 'STORAGE_TANK') {
      bg = 'bg-indigo-950/90 border-indigo-500/80 text-indigo-300';
    } else if (asset.type === 'PROCESS_UNIT') {
      bg = 'bg-purple-950/90 border-purple-500/80 text-purple-300';
    } else if (asset.type === 'CONTROL_ROOM') {
      bg = 'bg-emerald-950/90 border-emerald-500/80 text-emerald-300';
    }

    const html = `
      <div class="relative flex items-center justify-center w-8 h-8 rounded-lg border shadow-lg font-mono text-[10px] font-bold ${bg} ${ring} transition-all">
        <span>${asset.id}</span>
        ${asset.chemical_id ? `<span class="absolute -top-1 -right-1 w-2.5 h-2.5 rounded-full bg-rose-500 border border-slate-900"></span>` : ''}
      </div>
    `;
    return createIcon(html, '', [32, 32]);
  };

  const apIcon = (ap) => {
    const isCompromised = ap.status === 'COMPROMISED';
    const bg = isCompromised 
      ? 'bg-red-950 border-red-500 text-red-400' 
      : 'bg-emerald-950 border-emerald-500 text-emerald-400';
    const html = `
      <div class="flex items-center justify-center w-7 h-7 rounded-full border shadow-md font-mono text-[9px] font-extrabold ${bg}">
        ${ap.id}
      </div>
    `;
    return createIcon(html, '', [28, 28]);
  };

  const gateIcon = (gate) => {
    const html = `
      <div class="flex items-center justify-center px-1.5 py-0.5 rounded bg-slate-900 border border-slate-600 shadow text-[9px] font-mono font-bold text-cyan-300">
        ${gate.id}
      </div>
    `;
    return createIcon(html, '', [36, 20]);
  };

  const workerIcon = (worker) => {
    const html = `
      <div class="w-3 h-3 rounded-full bg-cyan-400 border border-slate-950 shadow-md transition-transform hover:scale-150" title="${worker.name} (${worker.role})"></div>
    `;
    return createIcon(html, '', [12, 12]);
  };

  const resourceIcon = (res) => {
    const html = `
      <div class="flex items-center justify-center w-6 h-6 rounded-md bg-amber-950 border border-amber-500 shadow-md text-amber-300 text-[10px] font-bold font-mono">
        🚨
      </div>
    `;
    return createIcon(html, '', [24, 24]);
  };

  // Threat GeoJSON slice
  const activeGeoJSON = useMemo(() => {
    if (!simulationResult) return null;
    const slice = simulationResult.time_steps.find(ts => ts.time_step_sec === currentTimeStep);
    return slice ? slice.geojson : simulationResult.current_geojson;
  }, [simulationResult, currentTimeStep]);

  const geojsonStyle = (feature) => {
    const props = feature.properties || {};
    return {
      fillColor: props.color || '#ef4444',
      fillOpacity: props.fillOpacity || 0.35,
      color: props.stroke || '#b91c1c',
      weight: 2,
      dashArray: props.zone_id === 'YELLOW_ZONE_CAUTION' ? '4, 4' : null,
    };
  };

  const onEachHazardFeature = (feature, layer) => {
    const props = feature.properties || {};
    layer.bindTooltip(`
      <div class="font-mono text-xs p-1">
        <b style="color:${props.color}">${props.name}</b><br/>
        <span class="text-slate-300">${props.threshold_label}</span><br/>
        <span>Max Reach: <b>${props.max_distance_m}m</b></span>
      </div>
    `, { sticky: true, className: 'leaflet-dark-tooltip' });
  };

  return (
    <div className="relative w-full h-full min-h-[580px] rounded-xl overflow-hidden border border-slate-800 bg-[#06090e] shadow-2xl">
      
      {/* Map Layer Controls floating bar */}
      <div className="absolute top-3 right-3 z-[400] flex flex-col items-end space-y-2">
        <button
          onClick={() => setShowLayerPanel(!showLayerPanel)}
          className="flex items-center space-x-1.5 bg-slate-900/90 backdrop-blur hover:bg-slate-800 text-slate-200 text-xs font-mono px-3 py-1.5 rounded-lg border border-slate-700 shadow-lg transition-all"
        >
          <Layers className="w-4 h-4 text-cyan-400" />
          <span>MAP LAYERS ({Object.values(layers).filter(Boolean).length})</span>
        </button>

        {showLayerPanel && (
          <div className="bg-slate-900/95 backdrop-blur border border-slate-700 rounded-xl p-3 shadow-2xl space-y-2 w-64 font-mono text-xs max-h-[80vh] overflow-y-auto custom-scrollbar">
            <div className="font-bold text-white uppercase text-[10px] pb-1 border-b border-slate-800 flex justify-between">
              <span>Geospatial Intelligence Layers</span>
              <span className="text-cyan-400 font-bold">REACT-X GIS</span>
            </div>
            
            {/* PRIMARY LAYERS */}
            <div className="text-[10px] text-cyan-400 font-bold uppercase pt-1">Primary Surveillance Layers</div>
            <label className="flex items-center justify-between text-slate-300 hover:text-white cursor-pointer">
              <span className="flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded-full bg-purple-500 animate-pulse"></span>
                Thermal Source Objects (Clusters)
              </span>
              <input 
                type="checkbox" 
                checked={layers.thermalSources} 
                onChange={(e) => setLayers({ ...layers, thermalSources: e.target.checked })} 
                className="accent-cyan-400"
              />
            </label>

            <label className="flex items-center justify-between text-slate-300 hover:text-white cursor-pointer">
              <span className="flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded-full bg-red-500 animate-pulse"></span>
                NASA FIRMS Thermal Hotspots
              </span>
              <input 
                type="checkbox" 
                checked={layers.satelliteHotspots} 
                onChange={(e) => setLayers({ ...layers, satelliteHotspots: e.target.checked })} 
                className="accent-cyan-400"
              />
            </label>

            <label className="flex items-center justify-between text-slate-300 hover:text-white cursor-pointer">
              <span className="flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded-full bg-cyan-400"></span>
                OSM & Industrial Facilities
              </span>
              <input 
                type="checkbox" 
                checked={layers.facilities} 
                onChange={(e) => setLayers({ ...layers, facilities: e.target.checked })} 
                className="accent-cyan-400"
              />
            </label>

            <label className="flex items-center justify-between text-slate-300 hover:text-white cursor-pointer">
              <span className="flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded-full bg-red-600"></span>
                Dispersion Threat Zones (Risk)
              </span>
              <input 
                type="checkbox" 
                checked={layers.threatZones} 
                onChange={(e) => setLayers({ ...layers, threatZones: e.target.checked })} 
                className="accent-cyan-400"
              />
            </label>

            {/* SECONDARY LAYERS */}
            <div className="text-[10px] text-cyan-400 font-bold uppercase pt-1.5 border-t border-slate-800">Secondary Context Layers</div>
            <label className="flex items-center justify-between text-slate-300 hover:text-white cursor-pointer">
              <span className="flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded-full bg-amber-400"></span>
                Persistent Heat Baselines
              </span>
              <input 
                type="checkbox" 
                checked={layers.persistentClusters} 
                onChange={(e) => setLayers({ ...layers, persistentClusters: e.target.checked })} 
                className="accent-cyan-400"
              />
            </label>

            <label className="flex items-center justify-between text-slate-300 hover:text-white cursor-pointer">
              <span className="flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded-full bg-emerald-400"></span>
                Safe Evacuation Corridors
              </span>
              <input 
                type="checkbox" 
                checked={layers.evacuationRoute} 
                onChange={(e) => setLayers({ ...layers, evacuationRoute: e.target.checked })} 
                className="accent-cyan-400"
              />
            </label>

            <label className="flex items-center justify-between text-slate-300 hover:text-white cursor-pointer">
              <span className="flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded-full bg-indigo-400"></span>
                Plant Assets & Tanks
              </span>
              <input 
                type="checkbox" 
                checked={layers.assets} 
                onChange={(e) => setLayers({ ...layers, assets: e.target.checked })} 
                className="accent-cyan-400"
              />
            </label>

            <label className="flex items-center justify-between text-slate-300 hover:text-white cursor-pointer">
              <span className="flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded-full bg-slate-400"></span>
                Internal Road Grid
              </span>
              <input 
                type="checkbox" 
                checked={layers.roads} 
                onChange={(e) => setLayers({ ...layers, roads: e.target.checked })} 
                className="accent-cyan-400"
              />
            </label>
          </div>
        )}
      </div>

      {/* Map Legend Overlay */}
      <div className="absolute bottom-3 left-3 z-[400] bg-slate-900/95 backdrop-blur border border-slate-800 rounded-lg p-2.5 shadow-lg font-mono text-[10px] space-y-1">
        <div className="font-bold text-white uppercase border-b border-slate-800 pb-0.5 flex justify-between">
          <span>Satellite & Hazard Legend</span>
        </div>
        <div className="grid grid-cols-2 gap-x-3 gap-y-0.5 pt-0.5">
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-red-600 border border-red-300 animate-pulse"></span>
            <span className="text-red-300 font-bold">Industrial Fire</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-orange-500 border border-orange-300"></span>
            <span className="text-orange-300">Gas Flare</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-purple-600 border border-purple-300"></span>
            <span className="text-purple-300">Process Heat</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-yellow-500 border border-yellow-300"></span>
            <span className="text-yellow-300">Agri Burning</span>
          </div>
        </div>
      </div>

      {/* Leaflet Map */}
      <MapContainer
        center={centerCoords}
        zoom={14}
        scrollWheelZoom={true}
        style={{ width: '100%', height: '100%', minHeight: '580px' }}
      >
        <MapRecenter center={centerCoords} zoom={14} />

        {/* Dark TileLayer */}
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; NASA FIRMS'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />

        {/* 1. Industrial Facilities Boundaries & Markers */}
        {layers.facilities && facilities.map((fac) => {
          const isAbnormal = fac.current_status !== 'NOMINAL_OPERATIONS' || fac.current_abnormality_score > 30.0;
          return (
            <React.Fragment key={fac.id}>
              {/* Facility Fence Boundary Circle */}
              <Circle
                center={fac.coordinates}
                radius={fac.fence_radius_m}
                pathOptions={{
                  color: isAbnormal ? '#ef4444' : '#06b6d4',
                  fillColor: isAbnormal ? '#ef4444' : '#0891b2',
                  fillOpacity: 0.12,
                  weight: 1.5,
                  dashArray: '5, 5'
                }}
              />

              {/* Facility Marker */}
              <Marker
                position={fac.coordinates}
                icon={facilityIcon(fac)}
                eventHandlers={{
                  click: () => onOpenFacilityProfile && onOpenFacilityProfile(fac)
                }}
              >
                <Popup className="leaflet-dark-popup" maxWidth={300}>
                  <div className="font-mono text-xs space-y-1.5 text-slate-200">
                    <div className="flex justify-between items-center border-b border-slate-700 pb-1">
                      <span className="font-bold text-white text-xs">{fac.name}</span>
                      <span className="text-cyan-300 font-bold">{fac.sector}</span>
                    </div>
                    <div className="text-[10px] text-slate-400">
                      Operator: <b className="text-white">{fac.operator_name}</b><br/>
                      Baseline: <b className="text-amber-400">{fac.baseline_mean_frp_mw} MW</b> (Diurnal: {fac.expected_diurnal_ratio})
                    </div>
                    <button
                      type="button"
                      onClick={() => onOpenFacilityProfile && onOpenFacilityProfile(fac)}
                      className="w-full py-1 bg-cyan-600/30 hover:bg-cyan-600/50 text-cyan-200 border border-cyan-500/40 rounded font-bold text-[10px] mt-1"
                    >
                      VIEW FACILITY THERMAL PROFILE
                    </button>
                  </div>
                </Popup>
              </Marker>
            </React.Fragment>
          );
        })}

        {/* 2. Persistent Thermal Cluster Baselines */}
        {layers.persistentClusters && persistentClusters.map((cluster) => (
          <Circle
            key={cluster.cluster_id}
            center={cluster.center_coordinates}
            radius={cluster.radius_m}
            pathOptions={{
              color: cluster.is_abnormal ? '#ef4444' : '#f59e0b',
              fillColor: cluster.is_abnormal ? '#ef4444' : '#f59e0b',
              fillOpacity: 0.15,
              weight: 1.5,
              dashArray: '4, 4'
            }}
          >
            <Tooltip className="leaflet-dark-tooltip">
              <div className="font-mono text-[10px]">
                <b>Persistent Source: {cluster.primary_source_type}</b><br/>
                Baseline Mean: {cluster.mean_frp_mw} MW | Z={cluster.frp_deviation_zscore}
              </div>
            </Tooltip>
          </Circle>
        ))}

        {/* 2b. Spatiotemporal Thermal Source Objects (Clusters) */}
        {layers.thermalSources && thermalSources.map((source) => {
          const isSelected = selectedSourceId === source.source_id;
          return (
            <Marker
              key={source.source_id}
              position={[source.centroid_lat, source.centroid_lon]}
              icon={thermalSourceIcon(source, isSelected)}
              eventHandlers={{
                click: () => onSelectThermalSource && onSelectThermalSource(source.source_id)
              }}
            >
              <Popup className="leaflet-dark-popup" maxWidth={360} minWidth={280}>
                <div className="font-mono text-xs space-y-2 text-slate-200 p-0.5">
                  <div className="flex items-center justify-between border-b border-slate-700/80 pb-1">
                    <span className="font-extrabold text-purple-400">{source.source_id}</span>
                    <span className="px-1.5 py-0.2 rounded text-[9px] font-bold border bg-purple-500/20 text-purple-300 border-purple-500/50">
                      {source.source_status.replace('_', ' ')}
                    </span>
                  </div>

                  <div className="grid grid-cols-2 gap-1.5 text-[10px] bg-slate-950/80 p-2 rounded-lg border border-slate-800">
                    <div>
                      <span className="text-slate-500 block text-[9px]">OBSERVATIONS</span>
                      <span className="text-white font-bold">{source.observation_count} passes ({source.active_days_count} active days)</span>
                    </div>
                    <div>
                      <span className="text-slate-500 block text-[9px]">MEAN / MAX FRP</span>
                      <span className="text-amber-400 font-bold text-xs">{source.mean_frp_mw} / {source.max_frp_mw} MW</span>
                    </div>
                    <div>
                      <span className="text-slate-500 block text-[9px]">SATELLITES & SENSORS</span>
                      <span className="text-cyan-300 font-bold">{source.unique_satellite_count} sats / {source.unique_sensor_count} sensors</span>
                    </div>
                    <div>
                      <span className="text-slate-500 block text-[9px]">DIURNAL RATIO (D/N)</span>
                      <span className="text-slate-200">{source.diurnal_ratio} ({source.day_detection_count}D / {source.night_detection_count}N)</span>
                    </div>
                  </div>

                  <div className="text-[10px] space-y-0.5 text-slate-400 bg-slate-900/50 p-1.5 rounded border border-slate-800/80">
                    <div>First Seen: <b className="text-slate-200">{new Date(source.first_detected).toLocaleDateString()}</b></div>
                    <div>Last Seen: <b className="text-slate-200">{new Date(source.last_detected).toLocaleDateString()}</b></div>
                    <div>Attributed Facility: <b className={source.primary_attributed_facility_name ? 'text-white' : 'text-slate-500 italic'}>
                      {source.primary_attributed_facility_name || 'UNATTRIBUTED'}
                    </b></div>
                    <div>Attribution Status: <b className="text-cyan-300">{source.attribution_status.replace(/_/g, ' ')}</b> ({Math.round((source.facility_attribution_confidence || 0) * 100)}% conf)</div>
                  </div>

                  {source.candidate_facilities && source.candidate_facilities.length > 0 && (
                    <div className="pt-1 border-t border-slate-800 text-[9px] text-slate-400">
                      <span className="text-slate-500 block">CANDIDATE FACILITIES ({source.candidate_facilities.length}):</span>
                      {source.candidate_facilities.slice(0, 2).map((c, i) => (
                        <div key={i} className="flex justify-between text-slate-300">
                          <span>#{c.rank} {c.facility_name.split(' - ')[0]}</span>
                          <span className="text-cyan-400 font-bold">{c.distance_m}m</span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </Popup>
            </Marker>
          );
        })}

        {/* 3. NASA FIRMS Satellite Thermal Hotspots */}
        {layers.satelliteHotspots && thermalEvents.map((hotspot) => {
          const isSelected = selectedEventId === hotspot.event_id;
          const isClassified = hotspot.classification && hotspot.classification !== 'UNCLASSIFIED';
          return (
            <Marker
              key={hotspot.event_id}
              position={[hotspot.latitude, hotspot.longitude]}
              icon={hotspotIcon(hotspot, isSelected)}
              eventHandlers={{
                click: () => onSelectThermalEvent && onSelectThermalEvent(hotspot.event_id)
              }}
            >
              <Popup className="leaflet-dark-popup" maxWidth={340} minWidth={260}>
                <div className="font-mono text-xs space-y-2 text-slate-200 p-0.5">
                  <div className="flex items-center justify-between border-b border-slate-700/80 pb-1">
                    <span className="font-extrabold text-cyan-400">{hotspot.event_id}</span>
                    <span className={`px-1.5 py-0.2 rounded text-[9px] font-bold border ${
                      hotspot.is_live_data 
                        ? 'bg-cyan-500/20 text-cyan-300 border-cyan-500/50' 
                        : 'bg-amber-500/20 text-amber-300 border-amber-500/40'
                    }`}>
                      {hotspot.is_live_data ? 'LIVE NASA SATELLITE' : 'DEMO / SIMULATION'}
                    </span>
                  </div>

                  <div className="grid grid-cols-2 gap-1.5 text-[10px] bg-slate-950/80 p-2 rounded-lg border border-slate-800">
                    <div>
                      <span className="text-slate-500 block text-[9px]">SATELLITE & SENSOR</span>
                      <span className="text-white font-bold">{hotspot.source_satellite} ({hotspot.sensor_name || 'VIIRS'})</span>
                    </div>
                    <div>
                      <span className="text-slate-500 block text-[9px]">FIRE POWER (FRP)</span>
                      <span className="text-amber-400 font-bold text-xs">{hotspot.frp_mw} MW</span>
                    </div>
                    <div>
                      <span className="text-slate-500 block text-[9px]">BRIGHTNESS TEMP</span>
                      <span className="text-slate-200">{hotspot.brightness_temp_k ? `${hotspot.brightness_temp_k} K` : 'N/A'}</span>
                    </div>
                    <div>
                      <span className="text-slate-500 block text-[9px]">CONFIDENCE</span>
                      <span className="text-emerald-400 font-bold">{hotspot.confidence} ({hotspot.confidence_pct || 90}%)</span>
                    </div>
                  </div>

                  <div className="text-[10px] space-y-0.5 text-slate-400 bg-slate-900/50 p-1.5 rounded border border-slate-800/80">
                    <div>Acquisition: <b className="text-slate-200">{new Date(hotspot.acquisition_timestamp).toUTCString()}</b></div>
                    <div>Pass: <b className="text-cyan-300">{hotspot.day_night === 'D' ? 'Daytime Overpass' : 'Nighttime Overpass'}</b></div>
                    <div>Facility: <b className={hotspot.attributed_facility_name ? 'text-white' : 'text-slate-500 italic'}>{hotspot.attributed_facility_name || 'Pending Spatial KD-Tree Index'}</b></div>
                    <div>Classification: <b className={isClassified ? 'text-amber-300' : 'text-slate-400'}>{isClassified ? hotspot.classification.replace(/_/g, ' ') : 'Pending ML Model'}</b></div>
                  </div>

                  {hotspot.attributed_facility_id && (
                    <button
                      type="button"
                      onClick={() => {
                        const fac = facilities.find(f => f.id === hotspot.attributed_facility_id);
                        if (onInitiateHandoff && fac) onInitiateHandoff(fac, hotspot);
                      }}
                      className="w-full bg-gradient-to-r from-red-600 to-amber-600 hover:from-red-500 hover:to-amber-500 text-white font-bold py-1.5 rounded-lg text-[10px] shadow transition-all flex items-center justify-center space-x-1"
                    >
                      <Siren className="w-3.5 h-3.5" />
                      <span>OPEN RESPONSE WORKSPACE</span>
                    </button>
                  )}
                </div>
              </Popup>
            </Marker>
          );
        })}

        {/* 4. Plant Internal Boundary */}
        {layers.boundary && plant?.bounds && (
          <Polyline
            positions={plant.bounds}
            pathOptions={{ color: '#06b6d4', weight: 2, dashArray: '6, 6', opacity: 0.7 }}
          >
            <Tooltip permanent direction="top" className="leaflet-dark-tooltip">
              {plant.name} Unit Perimeter
            </Tooltip>
          </Polyline>
        )}

        {/* 5. Internal Roads */}
        {layers.roads && siteData?.roads?.map((road) => (
          <Polyline
            key={road.id}
            positions={road.coordinates}
            pathOptions={{ 
              color: road.status === 'BLOCKED' ? '#ef4444' : '#64748b', 
              weight: road.width_m ? Math.max(3, road.width_m / 2) : 4,
              opacity: road.status === 'BLOCKED' ? 0.9 : 0.6,
              dashArray: road.status === 'BLOCKED' ? '4, 4' : null
            }}
          />
        ))}

        {/* 6. Hazard Dispersion Threat Zones (GeoJSON) */}
        {layers.threatZones && activeGeoJSON && (
          <GeoJSON
            key={`hazard-${currentTimeStep}-${JSON.stringify(simulationResult?.source_coordinates)}`}
            data={activeGeoJSON}
            style={geojsonStyle}
            onEachFeature={onEachHazardFeature}
          />
        )}

        {/* 7. Evacuation Route Polyline */}
        {layers.evacuationRoute && evacuationPlan?.primary_evacuation_route?.route_coordinates && (
          <Polyline
            positions={evacuationPlan.primary_evacuation_route.route_coordinates}
            pathOptions={{ color: '#10b981', weight: 6, opacity: 0.95 }}
          >
            <Tooltip sticky className="leaflet-dark-tooltip">
              <div className="font-mono text-xs">
                <b className="text-emerald-400">Safe Evacuation Route</b><br/>
                Distance: {evacuationPlan.primary_evacuation_route.total_distance_m}m (~{evacuationPlan.primary_evacuation_route.estimated_evac_time_min} min)
              </div>
            </Tooltip>
          </Polyline>
        )}

        {/* 8. Plant Assets */}
        {layers.assets && siteData?.assets?.map((asset) => {
          const isSelected = selectedAssetId === asset.id;
          const isSource = simulationResult?.source_asset_id === asset.id;
          return (
            <Marker
              key={asset.id}
              position={asset.coordinates}
              icon={assetIcon(asset, isSelected, isSource)}
              eventHandlers={{
                click: () => onSelectAsset && onSelectAsset(asset.id)
              }}
            >
              <Popup className="leaflet-dark-popup" maxWidth={300}>
                <div className="font-mono text-xs space-y-1.5 text-slate-200">
                  <div className="flex justify-between items-center border-b border-slate-700 pb-1">
                    <span className="font-bold text-cyan-400">{asset.id}</span>
                    <span className="text-amber-300 text-[10px]">{asset.criticality}</span>
                  </div>
                  <div className="font-bold text-white text-xs">{asset.name}</div>
                  <div className="text-[10px] text-slate-400">{asset.chemical_id || 'Chemical Unit'}</div>
                </div>
              </Popup>
            </Marker>
          );
        })}

        {/* 9. Assembly Points */}
        {layers.assemblyPoints && siteData?.assembly_points?.map((ap) => (
          <Marker
            key={ap.id}
            position={ap.coordinates}
            icon={apIcon(ap)}
          />
        ))}

        {/* 10. Gates */}
        {layers.gates && siteData?.gates?.map((g) => (
          <Marker
            key={g.id}
            position={g.coordinates}
            icon={gateIcon(g)}
          />
        ))}

        {/* 11. Workers */}
        {layers.workers && siteData?.workers?.map((w) => (
          <Marker
            key={w.id}
            position={w.coordinates}
            icon={workerIcon(w)}
          />
        ))}

        {/* 12. Resources */}
        {layers.resources && siteData?.emergency_resources?.map((res) => (
          <Marker
            key={res.id}
            position={res.coordinates}
            icon={resourceIcon(res)}
          />
        ))}

      </MapContainer>
    </div>
  );
}
