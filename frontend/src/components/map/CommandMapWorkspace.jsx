import React, { useEffect, useState, useMemo, useRef } from 'react';
import { 
  MapContainer, TileLayer, GeoJSON, Marker, 
  Circle, Tooltip, Polyline, useMap 
} from 'react-leaflet';
import L from 'leaflet';
import { 
  Layers, Flame, Satellite, Building2, 
  ShieldAlert, Navigation, ChevronDown, ChevronUp, Clock,
  CheckCircle2, Info, Network, AlertTriangle
} from 'lucide-react';
import { useTheme } from '../../context/ThemeContext';

// Map Controller with comprehensive ResizeObserver and smooth pan/zoom
function MapController({ center, zoom }) {
  const map = useMap();
  
  useEffect(() => {
    const handleResize = () => {
      try {
        map.invalidateSize();
      } catch (e) {}
    };

    // Invalidate immediately and after transition animations
    const t1 = setTimeout(handleResize, 50);
    const t2 = setTimeout(handleResize, 250);
    const t3 = setTimeout(handleResize, 600);

    const container = map.getContainer();
    let ro = null;
    if (typeof ResizeObserver !== 'undefined' && container) {
      ro = new ResizeObserver(() => {
        handleResize();
      });
      ro.observe(container);
    }

    if (center && center[0] && center[1]) {
      map.setView(center, zoom || map.getZoom() || 14, { animate: true });
    }

    return () => {
      clearTimeout(t1);
      clearTimeout(t2);
      clearTimeout(t3);
      if (ro && container) ro.unobserve(container);
    };
  }, [center, zoom, map]);

  return null;
}

export default function CommandMapWorkspace({
  center = [21.6850, 72.5750],
  zoom = 14,
  facilities = [],
  thermalEvents = [],
  thermalSources = [],
  persistentClusters = [],
  simulationResult = null,
  currentTimeStep = 120,
  onChangeTimeStep,
  cascadePathways = null,
  evacuationPlan = null,
  selectedFacilityId = null,
  selectedEventId = null,
  selectedSourceId = null,
  onSelectFacility,
  onSelectThermalEvent,
  onSelectThermalSource
}) {
  const { isDark } = useTheme();
  const mapContainerRef = useRef(null);

  const [layers, setLayers] = useState({
    facilities: true,
    thermalHotspots: true,
    persistentSources: true,
    threatZones: true,
    cascadePathways: true,
    evacuationRoutes: true
  });

  const [showLayersDropdown, setShowLayersDropdown] = useState(false);
  const [showLegend, setShowLegend] = useState(true);

  // Custom DivIcon Helper
  const createDivIcon = (htmlContent, size = [28, 28]) => {
    return L.divIcon({
      html: htmlContent,
      className: 'custom-map-icon',
      iconSize: size,
      iconAnchor: [size[0] / 2, size[1] / 2],
      popupAnchor: [0, -size[1] / 2]
    });
  };

  // Thermal Hotspot Icon Generator
  const getHotspotIcon = (evt, isSelected) => {
    const isFire = evt.classification === 'INDUSTRIAL_FIRE' || (evt.abnormality_score && evt.abnormality_score >= 80);
    const isFlare = evt.classification === 'GAS_FLARE';
    const isMining = evt.classification === 'MINING_PROCESS_HEAT';
    const isAgri = evt.classification === 'AGRICULTURAL_BURNING';
    const isRoutine = evt.classification === 'ROUTINE_PROCESS_HEAT';

    let bgClass = 'bg-amber-500 text-white';
    let label = '🔥';

    if (isFire) {
      bgClass = 'bg-red-600 text-white animate-pulse';
      label = '🚨';
    } else if (isFlare) {
      bgClass = 'bg-orange-500 text-white';
      label = '⚡';
    } else if (isRoutine) {
      bgClass = 'bg-purple-600 text-white';
      label = '🏭';
    } else if (isAgri) {
      bgClass = 'bg-yellow-500 text-slate-950';
      label = '🌾';
    }

    const ring = isSelected ? 'ring-3 ring-blue-500 ring-offset-2 dark:ring-offset-slate-900' : 'shadow-md';

    const html = `
      <div class="relative flex items-center justify-center w-7 h-7 rounded-full border-2 border-white dark:border-slate-800 text-xs font-bold ${bgClass} ${ring} transition-transform hover:scale-110">
        <span>${label}</span>
        ${evt.frp_mw ? `<span class="absolute -top-1.5 -right-2 px-1 rounded bg-slate-900 text-white text-[8px] font-mono font-bold">${Math.round(evt.frp_mw)}M</span>` : ''}
      </div>
    `;
    return createDivIcon(html, [28, 28]);
  };

  // Facility Marker Icon Generator
  const getFacilityIcon = (fac, isSelected) => {
    const isAbnormal = fac.current_status !== 'NOMINAL_OPERATIONS' || (fac.current_abnormality_score && fac.current_abnormality_score > 40);
    const bgClass = isAbnormal ? 'bg-red-600 text-white' : 'bg-blue-600 text-white';
    const ring = isSelected ? 'ring-3 ring-blue-500 ring-offset-2 dark:ring-offset-slate-900' : 'shadow-md';

    const html = `
      <div class="flex items-center justify-center w-7 h-7 rounded-lg border-2 border-white dark:border-slate-800 text-xs font-bold ${bgClass} ${ring} transition-transform hover:scale-110">
        🏢
      </div>
    `;
    return createDivIcon(html, [28, 28]);
  };

  // Threat GeoJSON slice
  const activeGeoJSON = useMemo(() => {
    if (!simulationResult) return null;
    const slice = simulationResult.time_steps?.find(ts => ts.time_step_sec === currentTimeStep);
    return slice ? slice.geojson : simulationResult.current_geojson;
  }, [simulationResult, currentTimeStep]);

  const geojsonStyle = (feature) => {
    const props = feature.properties || {};
    return {
      fillColor: props.color || '#ef4444',
      fillOpacity: props.fillOpacity || 0.35,
      color: props.stroke || '#dc2626',
      weight: 2,
      dashArray: props.zone_id === 'YELLOW_ZONE_CAUTION' ? '4, 4' : null
    };
  };

  // Active Cascade Links
  const cascadeLinks = useMemo(() => {
    if (!cascadePathways || !cascadePathways.threatened_nodes) return [];
    return cascadePathways.threatened_nodes;
  }, [cascadePathways]);

  return (
    <div ref={mapContainerRef} className="relative w-full h-full min-h-[400px] bg-slate-100 dark:bg-slate-950 flex flex-col overflow-hidden">
      
      {/* Top Floating Controls: Layers & Active Simulation Slider */}
      <div className="absolute top-3 right-3 z-[400] flex flex-col items-end space-y-2 pointer-events-auto">
        
        {/* Layer Toggle Button */}
        <div className="relative">
          <button
            onClick={() => setShowLayersDropdown(!showLayersDropdown)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-white/95 dark:bg-slate-900/95 backdrop-blur hover:bg-white dark:hover:bg-slate-900 text-slate-800 dark:text-slate-100 font-bold text-xs border border-slate-300 dark:border-slate-700 shadow-md cursor-pointer transition-all"
          >
            <Layers className="w-4 h-4 text-blue-600 dark:text-blue-400" />
            <span>LAYERS ({Object.values(layers).filter(Boolean).length})</span>
            <ChevronDown className="w-3.5 h-3.5 text-slate-500" />
          </button>

          {showLayersDropdown && (
            <div className="absolute right-0 top-full mt-1.5 w-64 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl shadow-xl p-3 z-50 text-xs space-y-2">
              <div className="font-bold text-slate-900 dark:text-slate-100 pb-1 border-b border-slate-100 dark:border-slate-800 flex justify-between">
                <span>Map Overlays</span>
                <span className="text-blue-600 dark:text-blue-400 text-[10px] font-bold">GIS Active</span>
              </div>

              <div className="space-y-1.5">
                <label className="flex items-center justify-between text-slate-700 dark:text-slate-300 cursor-pointer">
                  <span className="flex items-center gap-1.5">🏢 Industrial Facilities</span>
                  <input 
                    type="checkbox" 
                    checked={layers.facilities} 
                    onChange={(e) => setLayers({ ...layers, facilities: e.target.checked })} 
                    className="accent-blue-600"
                  />
                </label>

                <label className="flex items-center justify-between text-slate-700 dark:text-slate-300 cursor-pointer">
                  <span className="flex items-center gap-1.5">🔥 Live Thermal Hotspots</span>
                  <input 
                    type="checkbox" 
                    checked={layers.thermalHotspots} 
                    onChange={(e) => setLayers({ ...layers, thermalHotspots: e.target.checked })} 
                    className="accent-blue-600"
                  />
                </label>

                <label className="flex items-center justify-between text-slate-700 dark:text-slate-300 cursor-pointer">
                  <span className="flex items-center gap-1.5">⚡ Persistent Flare Sources</span>
                  <input 
                    type="checkbox" 
                    checked={layers.persistentSources} 
                    onChange={(e) => setLayers({ ...layers, persistentSources: e.target.checked })} 
                    className="accent-blue-600"
                  />
                </label>

                <label className="flex items-center justify-between text-slate-700 dark:text-slate-300 cursor-pointer">
                  <span className="flex items-center gap-1.5">🚨 Threat & Hazard Plumes</span>
                  <input 
                    type="checkbox" 
                    checked={layers.threatZones} 
                    onChange={(e) => setLayers({ ...layers, threatZones: e.target.checked })} 
                    className="accent-blue-600"
                  />
                </label>

                <label className="flex items-center justify-between text-slate-700 dark:text-slate-300 cursor-pointer">
                  <span className="flex items-center gap-1.5">🔗 Domino / Cascade Chain</span>
                  <input 
                    type="checkbox" 
                    checked={layers.cascadePathways} 
                    onChange={(e) => setLayers({ ...layers, cascadePathways: e.target.checked })} 
                    className="accent-blue-600"
                  />
                </label>

                <label className="flex items-center justify-between text-slate-700 dark:text-slate-300 cursor-pointer">
                  <span className="flex items-center gap-1.5">🧭 Evacuation Routes</span>
                  <input 
                    type="checkbox" 
                    checked={layers.evacuationRoutes} 
                    onChange={(e) => setLayers({ ...layers, evacuationRoutes: e.target.checked })} 
                    className="accent-blue-600"
                  />
                </label>
              </div>
            </div>
          )}
        </div>

        {/* Time Step Scrubber (When Active Simulation Exists) */}
        {simulationResult && simulationResult.time_steps && (
          <div className="bg-white/95 dark:bg-slate-900/95 backdrop-blur border border-slate-300 dark:border-slate-700 rounded-xl p-2.5 shadow-md text-xs space-y-1 w-60 font-medium text-slate-800 dark:text-slate-100">
            <div className="flex justify-between items-center">
              <span className="flex items-center gap-1 font-bold">
                <Clock className="w-3.5 h-3.5 text-blue-600 dark:text-blue-400" /> Plume Dispersion
              </span>
              <span className="font-mono text-blue-700 dark:text-blue-400 font-bold">T+{currentTimeStep}s</span>
            </div>
            <input 
              type="range"
              min={0}
              max={120}
              step={30}
              value={currentTimeStep}
              onChange={(e) => onChangeTimeStep && onChangeTimeStep(Number(e.target.value))}
              className="w-full accent-blue-600 cursor-pointer"
            />
            <div className="flex justify-between text-[10px] text-slate-400 font-mono">
              <span>0s (Origin)</span>
              <span>30s</span>
              <span>60s</span>
              <span>120s (Steady)</span>
            </div>
          </div>
        )}
      </div>

      {/* Bottom Left: Collapsible Minimal Map Legend */}
      <div className="absolute bottom-3 left-3 z-[400] pointer-events-auto">
        {showLegend ? (
          <div className="bg-white/95 dark:bg-slate-900/95 backdrop-blur border border-slate-300 dark:border-slate-700 rounded-xl p-2.5 shadow-md text-xs space-y-1.5 max-w-xs animate-in fade-in duration-100">
            <div className="flex items-center justify-between font-bold text-slate-900 dark:text-slate-100 pb-1 border-b border-slate-100 dark:border-slate-800">
              <span className="text-[11px] uppercase tracking-wider text-slate-500 dark:text-slate-400">Map Legend</span>
              <button 
                onClick={() => setShowLegend(false)}
                className="text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 p-0.5 rounded cursor-pointer"
                title="Collapse Legend"
              >
                <ChevronDown className="w-3.5 h-3.5" />
              </button>
            </div>

            <div className="grid grid-cols-2 gap-x-3 gap-y-1 text-[11px] font-medium text-slate-700 dark:text-slate-300">
              <div className="flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded-full bg-red-600"></span>
                <span>Industrial Fire 🚨</span>
              </div>
              <div className="flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded-full bg-orange-500"></span>
                <span>Gas Flare ⚡</span>
              </div>
              <div className="flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded-full bg-purple-600"></span>
                <span>Process Heat 🏭</span>
              </div>
              <div className="flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded-full bg-yellow-500"></span>
                <span>Agri Burning 🌾</span>
              </div>
              <div className="flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded-sm bg-blue-600"></span>
                <span>Plant Boundary 🏢</span>
              </div>
              <div className="flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded-full bg-rose-500 opacity-60"></span>
                <span>ERPG Threat Zone</span>
              </div>
            </div>
          </div>
        ) : (
          <button
            onClick={() => setShowLegend(true)}
            className="px-2.5 py-1.5 rounded-lg bg-white/95 dark:bg-slate-900/95 backdrop-blur border border-slate-300 dark:border-slate-700 shadow-md text-xs font-bold text-slate-700 dark:text-slate-200 hover:text-blue-600 flex items-center gap-1 cursor-pointer"
          >
            <span>Legend</span>
            <ChevronUp className="w-3.5 h-3.5" />
          </button>
        )}
      </div>

      {/* Leaflet Map Canvas */}
      <MapContainer
        center={center}
        zoom={zoom}
        scrollWheelZoom={true}
        style={{ width: '100%', height: '100%', minHeight: '400px' }}
      >
        <MapController center={center} zoom={zoom} />

        {/* Dynamic Light / Dark Basemap Tiles */}
        {isDark ? (
          <TileLayer
            key="carto-dark"
            attribution='&copy; <a href="https://carto.com/">CARTO</a> &copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
            url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
            maxZoom={19}
          />
        ) : (
          <TileLayer
            key="osm-light"
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            maxZoom={19}
          />
        )}

        {/* 1. Industrial Facilities Fences & Markers */}
        {layers.facilities && facilities.map((fac) => {
          const isSelected = selectedFacilityId === fac.id;
          const isAbnormal = fac.current_status !== 'NOMINAL_OPERATIONS' || (fac.current_abnormality_score && fac.current_abnormality_score > 40);

          return (
            <React.Fragment key={fac.id}>
              {fac.coordinates && (
                <>
                  <Circle
                    center={fac.coordinates}
                    radius={fac.fence_radius_m || 450}
                    pathOptions={{
                      color: isAbnormal ? '#dc2626' : (isDark ? '#38bdf8' : '#0284c7'),
                      fillColor: isAbnormal ? '#fee2e2' : (isDark ? '#0369a1' : '#e0f2fe'),
                      fillOpacity: isDark ? 0.25 : 0.18,
                      weight: isSelected ? 2.5 : 1.5,
                      dashArray: '5, 5'
                    }}
                  />
                  <Marker
                    position={fac.coordinates}
                    icon={getFacilityIcon(fac, isSelected)}
                    eventHandlers={{
                      click: () => onSelectFacility && onSelectFacility(fac.id)
                    }}
                  >
                    <Tooltip direction="top" offset={[0, -14]} opacity={0.95}>
                      <div>
                        <b>{fac.name}</b><br/>
                        <span className="text-slate-500 dark:text-slate-400">{fac.location}</span>
                      </div>
                    </Tooltip>
                  </Marker>
                </>
              )}
            </React.Fragment>
          );
        })}

        {/* 2. Thermal Hotspots & Anomalies */}
        {layers.thermalHotspots && thermalEvents.map((evt) => {
          if (!evt.latitude || !evt.longitude) return null;
          const isSelected = selectedEventId === evt.event_id;

          return (
            <Marker
              key={evt.event_id}
              position={[evt.latitude, evt.longitude]}
              icon={getHotspotIcon(evt, isSelected)}
              eventHandlers={{
                click: () => onSelectThermalEvent && onSelectThermalEvent(evt)
              }}
            >
              <Tooltip direction="top" offset={[0, -14]} opacity={0.95}>
                <div>
                  <b className="text-red-600 dark:text-red-400">{evt.classification || 'THERMAL ANOMALY'}</b><br/>
                  <span>FRP: <b>{evt.frp_mw ? Math.round(evt.frp_mw) : 'N/A'} MW</b></span> • 
                  <span> Temp: <b>{evt.brightness_temp_k ? Math.round(evt.brightness_temp_k) : 'N/A'} K</b></span>
                </div>
              </Tooltip>
            </Marker>
          );
        })}

        {/* 3. Domino / Cascade Pathway Overlays */}
        {layers.cascadePathways && cascadeLinks.length > 0 && center && (
          <>
            {cascadeLinks.map((node, idx) => {
              const targetCoords = [center[0] + (idx === 0 ? 0.001 : (idx === 1 ? -0.0015 : 0.002)), center[1] + (idx === 0 ? 0.0015 : (idx === 1 ? 0.002 : -0.0015))];
              return (
                <React.Fragment key={`cascade-pathway-${idx}`}>
                  <Polyline
                    positions={[center, targetCoords]}
                    pathOptions={{
                      color: node.cascade_probability_pct > 80 ? '#ef4444' : '#f59e0b',
                      weight: 3,
                      dashArray: '6, 6',
                      opacity: 0.85
                    }}
                  />
                  <Circle
                    center={targetCoords}
                    radius={45}
                    pathOptions={{
                      color: node.cascade_probability_pct > 80 ? '#dc2626' : '#d97706',
                      fillColor: node.cascade_probability_pct > 80 ? '#fee2e2' : '#fef3c7',
                      fillOpacity: 0.4
                    }}
                  >
                    <Tooltip direction="top">
                      <div>
                        <b>{node.name}</b><br/>
                        <span>Cascade Risk: <b className="text-red-600">{node.cascade_probability_pct}%</b></span>
                      </div>
                    </Tooltip>
                  </Circle>
                </React.Fragment>
              );
            })}
          </>
        )}

        {/* 4. Dispersion Plume GeoJSON Layer */}
        {layers.threatZones && activeGeoJSON && (
          <GeoJSON
            key={`plume-geojson-${currentTimeStep}`}
            data={activeGeoJSON}
            style={geojsonStyle}
          />
        )}

        {/* 5. Evacuation Dynamic Routing Polylines & Assembly Markers */}
        {layers.evacuationRoutes && evacuationPlan && (
          <>
            {/* Primary Route */}
            {evacuationPlan.primary_evacuation_route?.route_coordinates && evacuationPlan.primary_evacuation_route.route_coordinates.length > 0 && (
              <>
                <Polyline
                  positions={evacuationPlan.primary_evacuation_route.route_coordinates}
                  pathOptions={{
                    color: '#16a34a',
                    weight: 5,
                    opacity: 0.95,
                    dashArray: '8, 8'
                  }}
                />
                {evacuationPlan.primary_evacuation_route.assembly_point_coords && (
                  <Marker
                    position={evacuationPlan.primary_evacuation_route.assembly_point_coords}
                    icon={createDivIcon(
                      `<div class="w-7 h-7 rounded-full bg-emerald-600 border-2 border-white dark:border-slate-900 flex items-center justify-center text-white text-xs shadow-lg font-bold">🟢</div>`,
                      [28, 28]
                    )}
                  >
                    <Tooltip direction="top" offset={[0, -14]} opacity={0.95}>
                      <div>
                        <b className="text-emerald-700 dark:text-emerald-400">Designated Safe Assembly Point</b><br/>
                        <span>{evacuationPlan.primary_evacuation_route.recommended_assembly_point_name || 'Designated Safe Gate'}</span><br/>
                        <span className="text-slate-500 dark:text-slate-400 font-mono text-[10px]">Distance: {evacuationPlan.primary_evacuation_route.total_distance_m?.toFixed(0)}m</span>
                      </div>
                    </Tooltip>
                  </Marker>
                )}
              </>
            )}

            {/* Secondary / Candidate Routes */}
            {evacuationPlan.secondary_evacuation_route?.route_coordinates && (
              <Polyline
                positions={evacuationPlan.secondary_evacuation_route.route_coordinates}
                pathOptions={{
                  color: '#0284c7',
                  weight: 3,
                  opacity: 0.7,
                  dashArray: '4, 6'
                }}
              />
            )}
          </>
        )}

      </MapContainer>
    </div>
  );
}
