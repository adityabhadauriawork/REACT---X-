import React, { useState, useEffect } from 'react';
import { 
  FileText, Download, ShieldCheck, CheckCircle2, 
  AlertTriangle, Clock, RefreshCw, UserCheck, Shield, 
  Layers, Check, Sparkles, Sliders, ChevronDown, ChevronUp 
} from 'lucide-react';
import { api } from '../../services/api';

export default function PrePlanViewer({ 
  plantInfo, 
  simulationResult, 
  impactResult, 
  evacuationPlan, 
  resourcePlan, 
  onExportPDF, 
  isExporting 
}) {
  const [authRecord, setAuthRecord] = useState(null);
  const [loadingAuth, setLoadingAuth] = useState(false);
  const [submittingAuth, setSubmittingAuth] = useState(false);
  const [authError, setAuthError] = useState(null);
  const [authSuccess, setAuthSuccess] = useState(null);

  // 5-Point Human Review Checklist
  const [checklist, setChecklist] = useState({
    reviewed_hazard: false,
    reviewed_evacuation: false,
    reviewed_tactical_resources: false,
    reviewed_limitations: false,
    acknowledged_prototype_status: false
  });

  const [approverName, setApproverName] = useState('');
  const [approverRole, setApproverRole] = useState('');
  const [approvalNotes, setApprovalNotes] = useState('');
  const [showRejectBox, setShowRejectBox] = useState(false);
  const [rejectionReason, setRejectionReason] = useState('');

  // Collapsible sections in document preview
  const [showTraceability, setShowTraceability] = useState(false);
  const [showDisclaimers, setShowDisclaimers] = useState(false);

  // Compute a deterministic scenario hash
  const scenarioHash = simulationResult && resourcePlan
    ? `${simulationResult.source_asset_id}-${simulationResult.chemical_id}-${simulationResult.effective_release_rate_kg_s}-${simulationResult.wind_direction_deg}-${simulationResult.wind_speed_kmh}-${simulationResult.ambient_temp_c}`
    : 'DEFAULT-HASH';

  // Fetch or initialize authorization record
  const fetchAuthStatus = async () => {
    if (!resourcePlan?.incident_id) return;
    try {
      setLoadingAuth(true);
      setAuthError(null);
      const res = await api.getAuthorizationStatus(
        resourcePlan.incident_id,
        simulationResult?.source_asset_id || 'T-04',
        simulationResult?.chemical_id || 'CHEM-NH3',
        simulationResult?.chemical_name || 'Ammonia (Anhydrous)',
        scenarioHash
      );
      setAuthRecord(res);
    } catch (err) {
      console.error('Failed to load authorization record:', err);
    } finally {
      setLoadingAuth(false);
    }
  };

  useEffect(() => {
    fetchAuthStatus();
  }, [resourcePlan?.incident_id, scenarioHash]);

  const handleChecklistToggle = (key) => {
    setChecklist(prev => ({ ...prev, [key]: !prev[key] }));
  };

  const checkedCount = Object.values(checklist).filter(Boolean).length;
  const isChecklistComplete = checkedCount === 5;
  const canApprove = isChecklistComplete && approverName.trim().length > 0 && approverRole.trim().length > 0;

  const handleApprove = async () => {
    if (!canApprove) return;
    try {
      setSubmittingAuth(true);
      setAuthError(null);
      const res = await api.authorizePrePlan({
        incident_id: resourcePlan.incident_id,
        asset_id: simulationResult.source_asset_id,
        chemical_id: simulationResult.chemical_id,
        chemical_name: simulationResult.chemical_name,
        document_version: authRecord?.document_version || 'v0.1',
        approver_name: approverName.trim(),
        approver_role: approverRole.trim(),
        checklist: checklist,
        notes: approvalNotes.trim() || 'Verified for emergency drill demonstration.',
        scenario_hash: scenarioHash
      });
      setAuthRecord(res);
      setAuthSuccess('Pre-Plan officially authorized! PDF document status updated to AUTHORIZED (PROTOTYPE DEMO).');
      setTimeout(() => setAuthSuccess(null), 6000);
    } catch (err) {
      console.error('Approval failed:', err);
      setAuthError(err.response?.data?.detail || err.message || 'Authorization failed');
    } finally {
      setSubmittingAuth(false);
    }
  };

  const handleReject = async () => {
    if (!rejectionReason.trim()) {
      setAuthError('Please state a reason for rejecting this pre-plan.');
      return;
    }
    try {
      setSubmittingAuth(true);
      setAuthError(null);
      const res = await api.rejectPrePlan({
        incident_id: resourcePlan.incident_id,
        reviewer_name: approverName.trim() || 'Duty HSE Controller',
        rejection_reason: rejectionReason.trim(),
        document_version: authRecord?.document_version || 'v0.1'
      });
      setAuthRecord(res);
      setShowRejectBox(false);
      setAuthSuccess('Pre-Plan rejected. Revision required before operational authorization.');
      setTimeout(() => setAuthSuccess(null), 6000);
    } catch (err) {
      console.error('Rejection failed:', err);
      setAuthError(err.response?.data?.detail || err.message || 'Rejection failed');
    } finally {
      setSubmittingAuth(false);
    }
  };

  if (!simulationResult || !impactResult || !evacuationPlan || !resourcePlan) {
    return (
      <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-8 text-center text-slate-500 font-mono text-xs">
        No active incident state. Run a hazard simulation to generate and authorize the official Fire Pre-Plan.
      </div>
    );
  }

  const { risk_assessment } = impactResult;
  const primRoute = evacuationPlan.primary_evacuation_route;
  const fw = resourcePlan.foam_water_requirements;
  const isAuthorized = authRecord?.status === 'AUTHORIZED';
  const isSuperseded = authRecord?.status === 'SUPERSEDED';

  return (
    <div className="space-y-4 font-mono text-xs text-slate-200">
      
      {/* 1. Level 1: Human Authorization Governance Control Card */}
      <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-4 shadow-xl space-y-4">
        
        {/* Header & Status Indicator */}
        <div className="flex flex-wrap items-center justify-between gap-2 pb-3 border-b border-slate-800">
          <div>
            <div className="flex items-center gap-2">
              <span className="text-[10px] uppercase tracking-wider text-slate-400">HUMAN-IN-THE-LOOP GOVERNANCE</span>
              <span className={`px-2 py-0.5 rounded text-[10px] font-bold flex items-center gap-1 border ${
                isAuthorized 
                  ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40' 
                  : isSuperseded
                  ? 'bg-rose-500/20 text-rose-300 border-rose-500/40'
                  : 'bg-amber-500/20 text-amber-300 border-amber-500/40'
              }`}>
                {isAuthorized ? <Check className="w-3 h-3" /> : <Clock className="w-3 h-3" />}
                {isAuthorized 
                  ? 'AUTHORIZED (PROTOTYPE DEMO)' 
                  : isSuperseded 
                  ? '⚠ SUPERSEDED (SCENARIO CHANGED)' 
                  : 'PENDING HUMAN AUTHORIZATION'}
              </span>
            </div>
            <h3 className="text-sm font-bold text-white flex items-center gap-2 mt-1">
              <ShieldCheck className="w-4 h-4 text-cyan-400" />
              Safety Controller Review & Pre-Plan Endorsement
            </h3>
          </div>

          <button
            type="button"
            onClick={onExportPDF}
            disabled={isExporting}
            className="flex items-center space-x-2 bg-gradient-to-r from-red-600 to-rose-600 hover:from-red-500 hover:to-rose-500 text-white font-bold text-xs px-5 py-2.5 rounded-lg border border-red-400/50 shadow-lg shadow-red-500/20 transition-all active:scale-95 disabled:opacity-50"
          >
            {isExporting ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Download className="w-4 h-4" />}
            <span>{isExporting ? 'Generating ReportLab PDF...' : (isAuthorized ? 'DOWNLOAD AUTHORIZED PDF (v1.0)' : 'DOWNLOAD DRAFT PDF (v0.1)')}</span>
          </button>
        </div>

        {/* Alerts */}
        {authSuccess && (
          <div className="bg-emerald-950/60 border border-emerald-500/80 p-3 rounded-lg text-emerald-200 text-xs flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
            <span>{authSuccess}</span>
          </div>
        )}
        {authError && (
          <div className="bg-rose-950/60 border border-rose-500/80 p-3 rounded-lg text-rose-200 text-xs flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-rose-400 shrink-0" />
            <span><b>Error:</b> {authError}</span>
          </div>
        )}

        {/* Governance Form / State Display */}
        {isAuthorized ? (
          /* Authorized Confirmation Banner */
          <div className="bg-emerald-950/20 border border-emerald-500/40 p-4 rounded-xl space-y-2 text-xs">
            <div className="flex items-center justify-between">
              <div className="font-bold text-emerald-300 flex items-center gap-2 text-sm">
                <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                <span>Document Authorized for Demonstration Drill</span>
              </div>
              <span className="text-[10px] text-emerald-400 font-mono">Record ID: {authRecord.id}</span>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-2 text-[11px] text-slate-300 pt-1">
              <div>Approver: <b className="text-white">{authRecord.approver_name}</b></div>
              <div>Role: <b className="text-white">{authRecord.approver_role}</b></div>
              <div>Timestamp: <span className="text-slate-400">{new Date(authRecord.approval_timestamp).toUTCString()}</span></div>
            </div>
            {authRecord.approval_notes && (
              <div className="text-[10px] text-slate-400 italic bg-slate-900/60 p-2 rounded border border-slate-800">
                Notes: {authRecord.approval_notes}
              </div>
            )}
          </div>
        ) : (
          /* Pending Review Form with 5-Point Checklist */
          <div className="space-y-3 bg-slate-950/60 p-3.5 rounded-xl border border-slate-800">
            <div className="flex justify-between items-center text-xs font-bold text-slate-300 border-b border-slate-800 pb-1.5">
              <span>Mandatory Safety Verification Checklist</span>
              <span className="text-cyan-400">{checkedCount} of 5 Completed</span>
            </div>

            {/* Checklist Items */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-2 text-[11px]">
              {[
                { id: 'reviewed_hazard', label: '1. Verified source release dynamics & Gaussian dispersion reaches' },
                { id: 'reviewed_evacuation', label: '2. Confirmed safe assembly muster points and obstacle-free egress' },
                { id: 'reviewed_tactical_resources', label: '3. Approved tactical vehicle staging and firewater demand' },
                { id: 'reviewed_limitations', label: '4. Reviewed flat-terrain screening assumptions and weather vectors' },
                { id: 'acknowledged_prototype_status', label: '5. Acknowledged prototype decision-support scope (Non-Certified)' }
              ].map(item => (
                <label 
                  key={item.id}
                  className={`flex items-start gap-2 p-2 rounded-lg border cursor-pointer transition-all ${
                    checklist[item.id]
                      ? 'bg-emerald-950/30 border-emerald-500/50 text-emerald-200'
                      : 'bg-slate-900 border-slate-800 text-slate-400 hover:border-slate-700'
                  }`}
                >
                  <input
                    type="checkbox"
                    checked={checklist[item.id]}
                    onChange={() => handleChecklistToggle(item.id)}
                    className="mt-0.5 rounded border-slate-700 text-emerald-500 focus:ring-0"
                  />
                  <span>{item.label}</span>
                </label>
              ))}
            </div>

            {/* Approver Name & Role Input */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-2.5 pt-1">
              <div>
                <label className="block text-[10px] text-slate-400 mb-1">DEMO APPROVER NAME *</label>
                <input
                  type="text"
                  value={approverName}
                  onChange={(e) => setApproverName(e.target.value)}
                  placeholder="e.g. Ramesh Thapa"
                  className="w-full bg-slate-900 border border-slate-700 rounded px-2.5 py-1.5 text-xs text-white placeholder-slate-600 focus:outline-none focus:border-cyan-500"
                />
              </div>

              <div>
                <label className="block text-[10px] text-slate-400 mb-1">DEMO ROLE / DESIGNATION *</label>
                <input
                  type="text"
                  value={approverRole}
                  onChange={(e) => setApproverRole(e.target.value)}
                  placeholder="e.g. Chief Safety Officer (HSE)"
                  className="w-full bg-slate-900 border border-slate-700 rounded px-2.5 py-1.5 text-xs text-white placeholder-slate-600 focus:outline-none focus:border-cyan-500"
                />
              </div>

              <div>
                <label className="block text-[10px] text-slate-400 mb-1">APPROVAL NOTES (OPTIONAL)</label>
                <input
                  type="text"
                  value={approvalNotes}
                  onChange={(e) => setApprovalNotes(e.target.value)}
                  placeholder="e.g. Verified for Shift Alpha Drill"
                  className="w-full bg-slate-900 border border-slate-700 rounded px-2.5 py-1.5 text-xs text-white placeholder-slate-600 focus:outline-none focus:border-cyan-500"
                />
              </div>
            </div>

            {/* Action Buttons */}
            <div className="flex flex-wrap items-center justify-between gap-2 pt-2 border-t border-slate-800">
              <button
                type="button"
                onClick={() => setShowRejectBox(!showRejectBox)}
                className="px-3 py-1.5 rounded bg-rose-500/20 text-rose-300 border border-rose-500/40 hover:bg-rose-500/30 text-xs font-bold transition-all"
              >
                REJECT / REQUEST REVISION
              </button>

              <button
                type="button"
                onClick={handleApprove}
                disabled={!canApprove || submittingAuth}
                className={`flex items-center gap-1.5 px-5 py-2 rounded-lg font-bold text-xs border transition-all ${
                  canApprove && !submittingAuth
                    ? 'bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white border-emerald-400/60 shadow-lg shadow-emerald-900/30 active:scale-95'
                    : 'bg-slate-800 text-slate-500 border-slate-700 cursor-not-allowed opacity-60'
                }`}
              >
                {submittingAuth ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <ShieldCheck className="w-4 h-4" />}
                <span>{submittingAuth ? 'RECORDING AUTHORIZATION...' : 'APPROVE & AUTHORIZE PRE-PLAN'}</span>
              </button>
            </div>

            {/* Rejection Prompt Box */}
            {showRejectBox && (
              <div className="bg-rose-950/40 border border-rose-500/60 p-3 rounded-lg space-y-2 mt-2">
                <div className="font-bold text-rose-300 text-xs">Specify Rejection Rationale:</div>
                <textarea
                  rows={2}
                  value={rejectionReason}
                  onChange={(e) => setRejectionReason(e.target.value)}
                  placeholder="e.g. Gate 2 is blocked by heavy tanker traffic; re-route to Gate 3."
                  className="w-full bg-slate-900 border border-slate-700 rounded p-2 text-xs text-white placeholder-slate-500"
                />
                <button
                  type="button"
                  onClick={handleReject}
                  disabled={submittingAuth}
                  className="bg-rose-600 hover:bg-rose-500 text-white text-xs px-3 py-1 rounded font-bold"
                >
                  CONFIRM REJECTION
                </button>
              </div>
            )}
          </div>
        )}

      </div>

      {/* 2. Level 2: Document Preview Paper */}
      <div className="bg-slate-950 border border-slate-700/80 rounded-xl p-6 shadow-2xl space-y-5 text-slate-300 max-w-5xl mx-auto">
        
        {/* Header */}
        <div className="border border-slate-700 bg-slate-900/90 p-4 rounded-lg flex flex-wrap justify-between items-center gap-2">
          <div>
            <div className="text-base font-extrabold text-white uppercase tracking-tight">
              {plantInfo?.name || 'PetroChem Complex Alpha'} — Emergency Pre-Plan
            </div>
            <div className="text-[11px] text-slate-400">
              Prototype Facility Ref: <span className="text-slate-300 font-bold">PCH-ALPHA-04</span> (Demo Facility — Non-Statutory Evaluation)
            </div>
          </div>
          <div className="text-right text-[11px]">
            <div className="font-bold text-cyan-400">INCIDENT ID: {resourcePlan.incident_id}</div>
            <div className="text-slate-400">Prepared by: REACT-X Autonomous Response Engine</div>
            <div className={`font-bold ${isAuthorized ? 'text-emerald-400' : 'text-amber-400'}`}>
              Status: {authRecord?.status || 'PENDING_HUMAN_AUTHORIZATION'} ({authRecord?.document_version || 'v0.1'})
            </div>
          </div>
        </div>

        {/* Threat Level Banner */}
        <div 
          className="p-2.5 rounded-lg text-center font-bold text-xs uppercase"
          style={{ backgroundColor: `${risk_assessment.color}25`, color: risk_assessment.color, border: `1px solid ${risk_assessment.color}60` }}
        >
          EMERGENCY LEVEL: {risk_assessment.risk_category} (SCORE: {risk_assessment.overall_score}/100) — {risk_assessment.summary_verdict}
        </div>

        {/* Section 1: Scenario & Weather Profile */}
        <div className="space-y-2">
          <div className="font-bold text-white uppercase border-b border-slate-800 pb-1 text-xs text-cyan-400">
            1. Incident Scenario & Meteorological Profile
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-[11px] bg-slate-900/60 p-3 rounded border border-slate-800">
            <div><span className="text-slate-500">Incident Type:</span> <span className="font-bold text-white">{simulationResult.incident_type}</span></div>
            <div><span className="text-slate-500">Source Asset:</span> <span className="font-bold text-white">{simulationResult.source_asset_id}</span></div>
            <div><span className="text-slate-500">Chemical:</span> <span className="font-bold text-rose-400">{simulationResult.chemical_name}</span></div>
            <div><span className="text-slate-500">Release Rate:</span> <span className="font-bold text-white">{simulationResult.effective_release_rate_kg_s} kg/s</span></div>
            <div><span className="text-slate-500">Wind Vector:</span> <span className="font-bold text-white">{simulationResult.wind_speed_kmh} km/h • <b>FROM:</b> {simulationResult.wind_direction_cardinal} ({simulationResult.wind_direction_deg}°)</span></div>
            <div><span className="text-slate-500">Plume Vector:</span> <span className="font-bold text-cyan-300"><b>TOWARD:</b> {((simulationResult.wind_direction_deg + 180) % 360).toFixed(0)}°</span></div>
            <div><span className="text-slate-500">Ambient Temp:</span> <span className="font-bold text-white">{simulationResult.ambient_temp_c !== undefined ? `${simulationResult.ambient_temp_c}°C` : '32°C'}</span></div>
            <div><span className="text-slate-500">Weather Mode:</span> <span className="font-bold text-white">{simulationResult.weather_mode} ({simulationResult.weather_source})</span></div>
          </div>
        </div>

        {/* Section 2: Threat Zones Table */}
        <div className="space-y-2">
          <div className="font-bold text-white uppercase border-b border-slate-800 pb-1 text-xs text-cyan-400">
            2. Hazard Threat Zones (Screening Dispersion Profile)
          </div>
          <table className="w-full text-left text-[11px] border border-slate-800">
            <thead>
              <tr className="bg-slate-900 text-slate-400">
                <th className="p-2 border-b border-slate-800">Zone Tier</th>
                <th className="p-2 border-b border-slate-800">Threshold Criteria</th>
                <th className="p-2 border-b border-slate-800">Max Downwind Reach</th>
                <th className="p-2 border-b border-slate-800">Max Crosswind Width</th>
                <th className="p-2 border-b border-slate-800">Envelope Area</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60">
              {simulationResult.summary_zones.map((z, idx) => (
                <tr key={idx} className="bg-slate-950/40">
                  <td className="p-2 font-bold" style={{ color: z.color }}>{z.name}</td>
                  <td className="p-2">{z.threshold_label}</td>
                  <td className="p-2 font-mono text-cyan-300">{z.max_downwind_distance_m}m</td>
                  <td className="p-2 font-mono">{z.max_crosswind_width_m}m</td>
                  <td className="p-2 font-mono">{z.area_sq_m.toLocaleString()} m²</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Section 3: Impact & Evacuation */}
        <div className="space-y-2">
          <div className="font-bold text-white uppercase border-b border-slate-800 pb-1 text-xs text-cyan-400">
            3. Personnel Impact & Evacuation Directives
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <div className="bg-slate-900/60 p-3 rounded border border-slate-800 space-y-1 text-[11px]">
              <div><b>Total Personnel on Site:</b> {impactResult.total_workers_at_site} workers</div>
              <div><b>Red Zone Exposure (Lethal):</b> <span className="text-red-400 font-bold">{impactResult.red_zone_workers_count} personnel</span></div>
              <div><b>Severe Zone Exposure (Orange):</b> {impactResult.orange_zone_workers_count} personnel</div>
              <div><b>Compromised Assets:</b> {impactResult.affected_assets_count} units</div>
              <div><b>Blocked Road Segments:</b> {impactResult.blocked_roads_count} roads</div>
              {impactResult.red_zone_workers_count === 0 && impactResult.orange_zone_workers_count === 0 && impactResult.yellow_zone_workers_count === 0 && (
                <div className="text-[10px] text-emerald-400 bg-emerald-950/30 p-1.5 rounded border border-emerald-500/30 mt-1">
                  <b>Exposure Assessment:</b> No active seeded worker coordinates intersected the calculated threat envelopes at simulation time.
                </div>
              )}
            </div>

            <div className="bg-emerald-950/20 p-3 rounded border border-emerald-500/40 space-y-1 text-[11px]">
              <div className="font-bold text-emerald-400">Designated Safe Assembly Point:</div>
              <div className="text-white font-bold">{primRoute.recommended_assembly_point_name}</div>
              <div><b>Exit Perimeter Gate:</b> {primRoute.recommended_gate_name}</div>
              <div><b>Total Evacuation Distance:</b> {primRoute.total_distance_m}m (~{primRoute.estimated_evac_time_min} min walk)</div>
              <div><b>Route Clearance:</b> <span className="text-emerald-300 font-bold">{primRoute.route_status}</span></div>
              {primRoute.estimated_evac_time_min >= 30.0 && (
                <div className="text-[10px] text-rose-300 font-bold bg-rose-950/40 p-1 rounded border border-rose-500/50 mt-1">
                  ⚠ LONG EGRESS — HUMAN REVIEW REQUIRED (Threshold: &ge; 30 min)
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Section 4: Resource Allocation & Suppression Demand */}
        <div className="space-y-2">
          <div className="font-bold text-white uppercase border-b border-slate-800 pb-1 text-xs text-cyan-400">
            4. Emergency Response Resources & Suppression Strategy
          </div>

          <div className="bg-amber-950/30 border border-amber-500/40 p-2 rounded text-[10px] text-amber-200">
            <b>DECISION-SUPPORT RECOMMENDATION — REQUIRES SITE/HSE VALIDATION:</b> All tactical quantities, PPE ensembles, and suppression demands are prototype computational recommendations.
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-2 bg-slate-900/40 p-2.5 rounded border border-slate-800 text-[11px]">
            <div><span className="text-slate-400">Upwind Standoff:</span> <span className="font-bold text-cyan-400">{resourcePlan.standoff_upwind_m}m</span></div>
            <div><span className="text-slate-400">Isolation Cordon:</span> <span className="font-bold text-amber-400">{resourcePlan.isolation_perimeter_m}m</span></div>
            <div><span className="text-slate-400">Firewater:</span> <span className="font-bold text-blue-400">{fw?.firewater_demand_lpm?.toLocaleString()} LPM</span></div>
            <div><span className="text-slate-400">Foam (AFFF):</span> <span className="font-bold text-rose-400">{fw?.foam_concentrate_demand_liters ? `${fw.foam_concentrate_demand_liters} L` : '0 L (Toxic)'}</span></div>
          </div>
        </div>

        {/* Section 5: Collapsible Data Traceability & Assumptions (Level 3) */}
        <div className="border-t border-slate-800 pt-3 space-y-2">
          <button
            type="button"
            onClick={() => setShowTraceability(!showTraceability)}
            className="w-full flex items-center justify-between text-xs font-bold text-slate-400 hover:text-white transition-colors"
          >
            <span>5. Data Traceability & Screening Assumptions</span>
            {showTraceability ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
          </button>

          {showTraceability && (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-[10px] text-slate-400 bg-slate-900/60 p-3 rounded border border-slate-800">
              <div>Dispersion Physics: <b className="text-slate-200">Screening Gaussian Plume (Pasquill D)</b></div>
              <div>Weather Telemetry: <b className="text-slate-200">{simulationResult.weather_mode} ({simulationResult.weather_source})</b></div>
              <div>Terrain Representation: <span className="text-slate-300">2D Flat GIS Mesh (z₀ = 0.5m)</span></div>
              <div>Road Obstacle Graph: <span className="text-slate-300">Dijkstra Dynamic Threat Avoidance</span></div>
            </div>
          )}
        </div>

        {/* Section 6: Authorization Governance Footer */}
        <div className="border-t border-slate-800 pt-4 flex flex-wrap justify-between items-end gap-3 text-[10px] text-slate-500">
          <div>
            Prepared autonomously by REACT-X Autonomous Response Engine.<br/>
            Human Authorization: <b className={isAuthorized ? 'text-emerald-400' : 'text-amber-400'}>{isAuthorized ? `GRANTED by ${authRecord.approver_name}` : 'REQUIRED (Status: PENDING)'}</b>
          </div>
          <div className="text-right border-t border-slate-600 pt-1 w-64">
            <span className="text-slate-300 font-bold">
              {isAuthorized ? `DEMO APPROVER: ${authRecord.approver_name}` : 'HSE INCIDENT CONTROLLER'}
            </span><br/>
            <span className="text-[9px] text-slate-400">{isAuthorized ? `Role: ${authRecord.approver_role}` : 'Human Review & Signature Required'}</span>
          </div>
        </div>

      </div>

    </div>
  );
}
