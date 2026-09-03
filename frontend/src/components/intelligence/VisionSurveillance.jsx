import React, { useState, useEffect, useRef } from 'react';
import { 
  Camera, Upload, ShieldAlert, Flame, Wind, 
  Users, CheckCircle2, AlertTriangle, RefreshCw, 
  ArrowRight, Video, Crosshair, Play, Activity,
  Radio, Gauge, ShieldCheck, Thermometer, Eye
} from 'lucide-react';
import { api } from '../../services/api';

export default function VisionSurveillance({ onCreateIncidentFromVision }) {
  const [presets, setPresets] = useState([]);
  const [selectedCameraId, setSelectedCameraId] = useState('CAM-01');
  const [analysisResult, setAnalysisResult] = useState(null);
  const [latestVisionData, setLatestVisionData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [activeScenario, setActiveScenario] = useState('NORMAL');
  const [uploadedImagePreview, setUploadedImagePreview] = useState(null);
  const fileInputRef = useRef(null);

  // Load camera presets & vision health
  useEffect(() => {
    api.getVisionCameraPresets().then(res => {
      setPresets(res);
    }).catch(err => console.error('Failed to load camera presets:', err));

    fetchLatestVision();
  }, []);

  const fetchLatestVision = async () => {
    try {
      const data = await api.getFacilityLatestVision('FAC-IN-DAHEJ-001');
      setLatestVisionData(data);
    } catch (err) {
      console.error('Failed to fetch latest facility vision:', err);
    }
  };

  // Run analysis on camera feed
  const runCameraAnalysis = async (camId, hazardType = null, file = null) => {
    try {
      setLoading(true);
      const formData = new FormData();
      formData.append('camera_id', camId);
      if (hazardType) formData.append('simulate_hazard_type', hazardType);
      if (file) formData.append('image_file', file);

      const res = await api.analyzeVisionFrame(formData);
      setAnalysisResult(res);
      await fetchLatestVision();
    } catch (err) {
      console.error('Vision analysis failed:', err);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  // Trigger when camera changes
  useEffect(() => {
    runCameraAnalysis(selectedCameraId);
  }, [selectedCameraId]);

  const handleFileUpload = (e) => {
    const file = e.target.files?.[0];
    if (file) {
      const reader = new FileReader();
      reader.onload = (event) => {
        setUploadedImagePreview(event.target.result);
      };
      reader.readAsDataURL(file);
      runCameraAnalysis(selectedCameraId, null, file);
    }
  };

  const handleScenarioChange = async (e) => {
    const newScn = e.target.value;
    setActiveScenario(newScn);
    setRefreshing(true);
    try {
      await api.setVisionSimulatorScenario(newScn);
      await api.triggerVisionSimulatorTick();
      await fetchLatestVision();
      await runCameraAnalysis(selectedCameraId, newScn.includes('FLAME') ? 'FIRE' : (newScn.includes('SMOKE') ? 'SMOKE' : null));
    } catch (err) {
      console.error('Failed to set vision scenario:', err);
    } finally {
      setRefreshing(false);
    }
  };

  const selectedCam = presets.find(p => p.camera_id === selectedCameraId) || presets[0];
  const isThermalCam = selectedCameraId === 'CAM-THERMAL-01' || selectedCameraId.includes('TH');
  
  // Extract thermal stats if available
  const activeThermalEvidence = latestVisionData?.thermal_cameras?.[0];
  const activeCCTVEvidence = latestVisionData?.cctv_cameras?.[0];

  return (
    <div className="space-y-4 font-mono text-xs text-slate-200">
      
      {/* 1. Header & Disclaimers */}
      <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-4 shadow-lg space-y-2">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div>
            <div className="flex items-center space-x-2">
              <h3 className="text-sm font-bold text-white flex items-center gap-2">
                <Camera className="w-4 h-4 text-cyan-400" />
                FACILITY THERMAL VISION & CCTV INTELLIGENCE
              </h3>
              <span className="px-2 py-0.5 rounded text-[10px] font-extrabold bg-amber-500/10 text-amber-400 border border-amber-500/30 tracking-wider">
                SIMULATED INDUSTRIAL VISION
              </span>
            </div>
            <p className="text-[11px] text-slate-400">
              Seconds-cadence radiometric thermal & optical CCTV structured visual evidence pipeline.
            </p>
          </div>

          <div className="flex items-center space-x-2">
            <select
              value={activeScenario}
              onChange={handleScenarioChange}
              className="bg-slate-950 border border-slate-700 text-[11px] text-slate-300 rounded px-2.5 py-1.5 focus:outline-none focus:border-cyan-500 font-bold"
            >
              <option value="NORMAL">Scenario: Normal Baseline</option>
              <option value="GRADUAL_HEATING">Scenario: Gradual Heat Rise (dT/dt)</option>
              <option value="LOCAL_HOTSPOT">Scenario: Local Flange Hotspot</option>
              <option value="RAPID_HEATING">Scenario: Acute Exothermic Thermal Spike</option>
              <option value="HOTSPOT_GROWTH">Scenario: Hotspot Spatial Expansion</option>
              <option value="MULTIPLE_HOTSPOTS">Scenario: Multiple Spatial Hotspots</option>
              <option value="SMOKE_LIKE_EVENT">Scenario: Optical Aerosol/Smoke Plume</option>
              <option value="FLAME_LIKE_EVENT">Scenario: Visible Flame Signature</option>
              <option value="CAMERA_FAILURE">Scenario: Camera Signal Fault</option>
            </select>

            <button
              onClick={() => { setRefreshing(true); runCameraAnalysis(selectedCameraId); }}
              disabled={refreshing}
              className="p-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded transition disabled:opacity-50"
              title="Poll Camera Ingestion"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${refreshing ? 'animate-spin text-cyan-400' : ''}`} />
            </button>
          </div>
        </div>

        {/* Conceptual Distinction Taxonomy Bar */}
        <div className="pt-2 border-t border-slate-800/80 grid grid-cols-2 sm:grid-cols-4 gap-2 text-[10px]">
          <div className="bg-slate-950/60 p-1.5 rounded border border-slate-800 text-center">
            <span className="text-cyan-400 font-bold block">1. THERMAL OBSERVATION</span>
            <span className="text-slate-400">Pixel Matrix Temperatures</span>
          </div>
          <div className="bg-slate-950/60 p-1.5 rounded border border-slate-800 text-center">
            <span className="text-purple-400 font-bold block">2. VISUAL EVIDENCE</span>
            <span className="text-slate-400">Hotspots, Plumes, dT/dt</span>
          </div>
          <div className="bg-slate-950/60 p-1.5 rounded border border-slate-800 text-center">
            <span className="text-amber-400 font-bold block">3. MODEL INFERENCE</span>
            <span className="text-slate-400">Classifiers & Confidences</span>
          </div>
          <div className="bg-slate-950/60 p-1.5 rounded border border-slate-800 text-center">
            <span className="text-rose-400 font-bold block">4. HAZARD ASSESSMENT</span>
            <span className="text-slate-400">Multimodal Process Fusion</span>
          </div>
        </div>
      </div>

      {/* 2. Camera Feeds & Analytics Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-3">
        
        {/* Left Column: Camera Feed Selector (4 cols) */}
        <div className="lg:col-span-4 bg-slate-900/90 border border-slate-800 rounded-xl p-3.5 space-y-3">
          <div className="font-bold text-white text-xs border-b border-slate-800 pb-1.5 flex items-center justify-between">
            <span>REGISTERED CAMERA STATIONS</span>
            <span className="text-[10px] text-emerald-400 flex items-center gap-1 font-bold">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping"></span>
              READ-ONLY FEED
            </span>
          </div>

          <div className="space-y-1.5">
            {presets.map(cam => {
              const isSelected = selectedCameraId === cam.camera_id;
              const isTh = cam.camera_id === 'CAM-THERMAL-01' || cam.camera_id.includes('TH');
              return (
                <button
                  key={cam.camera_id}
                  type="button"
                  onClick={() => {
                    setSelectedCameraId(cam.camera_id);
                    setUploadedImagePreview(null);
                  }}
                  className={`w-full p-2.5 rounded-lg border text-left transition-all ${
                    isSelected
                      ? 'bg-cyan-500/20 border-cyan-400 text-white shadow-sm'
                      : 'bg-slate-950/60 border-slate-800 text-slate-400 hover:text-white'
                  }`}
                >
                  <div className="font-bold text-xs flex justify-between items-center">
                    <span className="flex items-center gap-1.5">
                      {isTh ? <Thermometer className="w-3.5 h-3.5 text-amber-400" /> : <Eye className="w-3.5 h-3.5 text-cyan-400" />}
                      {cam.camera_id}
                    </span>
                    <span className="text-[10px] px-1.5 py-0.2 rounded bg-slate-900 border border-slate-700 text-slate-300">
                      {isTh ? 'RADIOMETRIC' : 'OPTICAL'}
                    </span>
                  </div>
                  <div className="text-[10px] text-slate-400 truncate mt-0.5">{cam.camera_name}</div>
                </button>
              );
            })}
          </div>

          {/* Upload Custom Image / CCTV Frame */}
          <div className="pt-2 border-t border-slate-800">
            <input
              type="file"
              ref={fileInputRef}
              onChange={handleFileUpload}
              accept="image/*"
              className="hidden"
            />
            <button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              className="w-full py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 flex items-center justify-center gap-1.5 text-xs font-bold transition"
            >
              <Upload className="w-3.5 h-3.5" />
              <span>UPLOAD LOCAL TEST FRAME</span>
            </button>
          </div>
        </div>

        {/* Right Column: Viewport & Structured Visual Evidence (8 cols) */}
        <div className="lg:col-span-8 bg-slate-900/90 border border-slate-800 rounded-xl p-4 space-y-3">
          
          <div className="flex justify-between items-center border-b border-slate-800 pb-2">
            <div>
              <span className="font-bold text-white text-xs flex items-center gap-2">
                <Video className="w-4 h-4 text-cyan-400" />
                {selectedCam?.camera_name || 'Active Surveillance Viewport'}
              </span>
              <span className="text-[10px] text-slate-400">Timestamp: {analysisResult?.timestamp || 'Streaming...'}</span>
            </div>

            <div className="flex items-center space-x-2">
              <span className="px-2 py-0.5 rounded text-[10px] font-bold border bg-emerald-500/10 text-emerald-400 border-emerald-500/30 flex items-center gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
                <span>LIVE (2.0 FPS)</span>
              </span>

              <span className={`px-2 py-0.5 rounded text-[10px] font-bold border ${
                analysisResult?.alert_level === 'CRITICAL'
                  ? 'bg-red-500/20 text-red-300 border-red-500/50 animate-pulse'
                  : analysisResult?.alert_level === 'WARNING'
                  ? 'bg-amber-500/20 text-amber-300 border-amber-500/50'
                  : 'bg-emerald-500/20 text-emerald-300 border-emerald-500/50'
              }`}>
                ALERT: {analysisResult?.alert_level || 'MONITORING'}
              </span>
            </div>
          </div>

          {/* Viewport Frame with Simulated CCTV Background & Bounding Boxes */}
          <div className="relative w-full h-72 rounded-lg overflow-hidden border border-slate-800 bg-[#060b13] flex items-center justify-center">
            
            {/* Background Feed (Uploaded image or synthetic grid) */}
            {uploadedImagePreview ? (
              <img 
                src={uploadedImagePreview} 
                alt="Camera Frame" 
                className="w-full h-full object-contain"
              />
            ) : (
              <div className="w-full h-full relative flex items-center justify-center opacity-70">
                {/* Synthetic Background with thermal or optical heatmap overlay */}
                <div className={`absolute inset-0 ${isThermalCam ? 'bg-gradient-to-tr from-indigo-950 via-purple-950/60 to-amber-950/40' : 'bg-gradient-to-t from-slate-950 via-slate-900/80 to-transparent'}`}></div>
                <div className="text-center space-y-2 z-0 text-slate-500">
                  <Crosshair className="w-14 h-14 mx-auto opacity-30 animate-spin" style={{ animationDuration: '30s' }} />
                  <div className="text-xs font-mono font-bold tracking-widest text-slate-300">
                    {selectedCam?.camera_id} • {isThermalCam ? 'RADIOMETRIC THERMOGRAM' : 'OPTICAL SURVEILLANCE FEED'}
                  </div>
                  <div className="text-[10px] text-slate-400">Target Asset: {selectedCam?.associated_asset_id} • Sector: {selectedCam?.sector}</div>
                </div>
              </div>
            )}

            {/* Bounding Box Overlays */}
            {analysisResult?.detections?.map(det => {
              const [x, y, w, h] = det.bbox_xywh;
              return (
                <div
                  key={det.id}
                  className="absolute border-2 transition-all duration-300 pointer-events-none"
                  style={{
                    left: `${x * 100}%`,
                    top: `${y * 100}%`,
                    width: `${w * 100}%`,
                    height: `${h * 100}%`,
                    borderColor: det.color_hex,
                    backgroundColor: `${det.color_hex}20`
                  }}
                >
                  <span 
                    className="absolute -top-5 left-0 px-1.5 py-0.2 text-[9.5px] font-bold rounded text-white"
                    style={{ backgroundColor: det.color_hex }}
                  >
                    {det.label} ({det.confidence_pct}%)
                  </span>
                </div>
              );
            })}

            {/* Corner HUD overlay */}
            <div className="absolute bottom-2 left-2 bg-slate-950/90 px-2.5 py-1 rounded text-[10px] text-slate-300 border border-slate-800 flex items-center gap-2">
              <span className="text-cyan-400 font-bold">FPS: 2.0</span>
              <span>•</span>
              <span>Res: 640x480</span>
              <span>•</span>
              <span className="text-amber-400">Model: RadiometricContour-v1</span>
            </div>
          </div>

          {/* Structured Radiometric & Optical Metrics Bar */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs">
            <div className="bg-slate-950/80 p-2.5 rounded-lg border border-slate-800">
              <span className="text-[10px] text-slate-500 font-bold block uppercase">Peak Temperature</span>
              <div className="text-base font-extrabold font-mono text-amber-400">
                {activeThermalEvidence ? `+${activeThermalEvidence.max_temperature.toFixed(1)} °C` : '+88.4 °C'}
              </div>
              <span className="text-[10px] text-slate-400">Zone Base: +25.0 °C</span>
            </div>

            <div className="bg-slate-950/80 p-2.5 rounded-lg border border-slate-800">
              <span className="text-[10px] text-slate-500 font-bold block uppercase">Rate of Rise (dT/dt)</span>
              <div className="text-base font-extrabold font-mono text-rose-400">
                {activeThermalEvidence?.hotspot_regions?.[0]?.rate_of_rise_c_min ? `+${activeThermalEvidence.hotspot_regions[0].rate_of_rise_c_min.toFixed(1)} °C/min` : '+8.2 °C/min'}
              </div>
              <span className="text-[10px] text-slate-400">Rolling Slope</span>
            </div>

            <div className="bg-slate-950/80 p-2.5 rounded-lg border border-slate-800">
              <span className="text-[10px] text-slate-500 font-bold block uppercase">Spatial Hotspots</span>
              <div className="text-base font-extrabold font-mono text-cyan-400">
                {activeThermalEvidence ? `${activeThermalEvidence.hotspot_count} Active` : '1 Active'}
              </div>
              <span className="text-[10px] text-slate-400">Tracked Multi-Frame</span>
            </div>

            <div className="bg-slate-950/80 p-2.5 rounded-lg border border-slate-800">
              <span className="text-[10px] text-slate-500 font-bold block uppercase">CCTV Optical Status</span>
              <div className="text-sm font-extrabold text-slate-200 truncate mt-0.5">
                {activeCCTVEvidence ? activeCCTVEvidence.scene_status : (analysisResult?.alert_level === 'CRITICAL' ? 'FLAME SIGNATURE' : 'CLEAR')}
              </div>
              <span className="text-[10px] text-slate-400">Optical Classifier</span>
            </div>
          </div>

          {/* Detections Summary & Actions */}
          {analysisResult && (
            <div className="space-y-2">
              <div className="bg-slate-950/70 p-3 rounded-lg border border-slate-800 text-[11px] leading-relaxed">
                {analysisResult.suggestion_summary}
              </div>

              {analysisResult.incident_suggested && (
                <div className="bg-gradient-to-r from-red-950/50 to-amber-950/50 border border-red-500/60 p-3 rounded-xl flex flex-wrap items-center justify-between gap-2 shadow-lg">
                  <div>
                    <span className="font-bold text-white text-xs flex items-center gap-1.5">
                      <Flame className="w-4 h-4 text-red-400" />
                      Visual Evidence Confirmed — Candidate Incident Trigger
                    </span>
                    <div className="text-[10px] text-slate-300 mt-0.5">
                      Target Equipment: <b className="text-white">{analysisResult.suggested_asset_id}</b> • Chemical: <b className="text-rose-400">{analysisResult.suggested_chemical_id}</b> • Rate: <b className="text-amber-300">{analysisResult.suggested_release_rate_kg_s} kg/s</b>
                    </div>
                  </div>

                  <button
                    type="button"
                    onClick={() => onCreateIncidentFromVision && onCreateIncidentFromVision({
                      asset_id: analysisResult.suggested_asset_id,
                      chemical_id: analysisResult.suggested_chemical_id,
                      incident_type: analysisResult.suggested_incident_type,
                      release_rate_kg_s: analysisResult.suggested_release_rate_kg_s
                    })}
                    className="px-4 py-2 rounded-lg bg-gradient-to-r from-red-600 to-rose-600 hover:from-red-500 hover:to-rose-500 text-white font-bold text-xs flex items-center gap-1.5 shadow-md transition-all active:scale-95"
                  >
                    <span>CREATE INCIDENT FROM EVIDENCE</span>
                    <ArrowRight className="w-3.5 h-3.5" />
                  </button>
                </div>
              )}
            </div>
          )}

          {/* Footer Info */}
          <div className="pt-2 border-t border-slate-800/80 flex items-center justify-between text-[10px] text-slate-500">
            <div className="flex items-center space-x-1 text-slate-400">
              <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
              <span>Read-Only Boundary Enforced (No PTZ / Actuator Write Access)</span>
            </div>
            <div>
              <span>Linked to Phase 12 Telemetry Stream</span>
            </div>
          </div>

        </div>

      </div>

    </div>
  );
}
