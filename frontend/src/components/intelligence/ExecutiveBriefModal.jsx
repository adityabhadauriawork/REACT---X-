import React, { useState, useEffect } from 'react';
import { createPortal } from 'react-dom';
import { 
  X, FileText, Copy, Download, CheckCircle2, ShieldAlert, 
  AlertTriangle, Users, Navigation, Siren, Clock, Check, RefreshCw,
  Sparkles, Flame, Activity, ShieldCheck, Database, Network, ArrowRight
} from 'lucide-react';
import { api } from '../../services/api';
import { useTheme } from '../../context/ThemeContext';

export default function ExecutiveBriefModal({
  isOpen,
  onClose,
  simulationResult,
  impactResult,
  evacuationPlan,
  resourcePlan,
  authorizationRecord,
  onExportPDF
}) {
  const { isDark } = useTheme();
  const [brief, setBrief] = useState(null);
  const [loading, setLoading] = useState(false);
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState(null);
  const [isExportingPDF, setIsExportingPDF] = useState(false);

  // Keyboard ESC listener
  useEffect(() => {
    if (!isOpen) return;
    const handleKeyDown = (e) => {
      if (e.key === 'Escape') onClose && onClose();
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  useEffect(() => {
    if (isOpen) {
      fetchBrief();
    }
  }, [isOpen, simulationResult, impactResult, evacuationPlan, resourcePlan, authorizationRecord]);

  const fetchBrief = async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await api.getExecutiveSituationBrief(
        simulationResult,
        impactResult,
        evacuationPlan,
        resourcePlan,
        authorizationRecord
      );
      setBrief(res);
    } catch (err) {
      console.warn('Failed to generate executive situation brief from server, using client synthesis:', err);
      // Fallback synthesis from simulationResult and active state
      if (simulationResult) {
        setBrief({
          incident_id: simulationResult.id || 'INC-DHJ-01',
          source_asset: simulationResult.source_asset_id || 'T-04',
          chemical: simulationResult.chemical_name || 'Ammonia (Anhydrous)',
          incident_type: simulationResult.incident_type || 'CRYOGENIC_HEADER_RUPTURE',
          facility_name: simulationResult.facility_name || 'Dahej Petrochemical Complex',
          location: 'Dahej PCPIR Corridor, Gujarat',
          sector: 'PETROCHEMICAL',
          severity_score: impactResult?.risk_assessment?.overall_score || 88,
          severity_category: impactResult?.risk_assessment?.risk_category || 'CRITICAL',
          escalation_trend: 'STABILIZING WITH UPWIND ISOLATION',
          max_red_reach_m: impactResult?.risk_assessment?.max_threat_radius_m || 280,
          max_orange_reach_m: (impactResult?.risk_assessment?.max_threat_radius_m || 280) * 1.8,
          exposed_workers_count: impactResult?.affected_workers_count || 14,
          casualty_triage_summary: `${impactResult?.red_zone_workers_count || 4} Lethal Red, ${impactResult?.orange_zone_workers_count || 10} Severe Exposure`,
          compromised_assets_count: impactResult?.affected_assets_count || 3,
          blocked_road_segments_count: impactResult?.blocked_roads_count || 1,
          site_accessibility_status: 'RESTRICTED — SOUTH ENTRY ONLY',
          containment_status: 'ACTIVE ISOLATION & WATER CURTAIN ENGAGED',
          primary_assembly_point: evacuationPlan?.primary_evacuation_route?.recommended_assembly_point_name || 'Assembly Point 3 (Upwind North)',
          primary_exit_gate: evacuationPlan?.primary_evacuation_route?.recommended_gate_name || 'Gate 2 (North)',
          evacuation_distance_m: evacuationPlan?.primary_evacuation_route?.total_distance_m || 320,
          estimated_walk_time_min: evacuationPlan?.primary_evacuation_route?.estimated_evac_time_min || 4,
          lead_tactical_unit: 'Dahej Industrial Hazmat Fire Team A',
          lead_unit_eta_min: 3,
          firewater_demand_lpm: 4500,
          mandatory_ppe: 'Level A Vapor-Tight SCBA Suit',
          human_authorization_status: authorizationRecord?.status || 'PENDING_AUTHORIZATION',
          approver_name: authorizationRecord?.approver_name || null,
          approver_role: authorizationRecord?.approver_role || null,
          authorization_timestamp: authorizationRecord?.approval_timestamp || null,
          wind_vector_summary: `${simulationResult.wind_speed_kmh || 12} km/h from ${simulationResult.wind_direction_cardinal || 'NE'} (45°)`,
          plume_bearing_summary: 'Downwind SW (225°) toward Secondary Tank Battery',
          pending_decisions: [
            'Authorize dynamic emergency evacuation pre-plan document',
            'Dispatch hazmat foam-water fog suppression curtain',
            'Issue regional alert notification to Bharuch District Control Center'
          ],
          prototype_disclaimer: 'REACT-X INDUSTRIAL THERMAL INTELLIGENCE & EMERGENCY PRE-PLAN'
        });
      } else {
        setError('No active accident scenario or thermal observation selected. Select a preset or run a simulation to compile a situation brief.');
      }
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  const handleCopyMarkdown = () => {
    if (brief?.formatted_brief_markdown) {
      navigator.clipboard.writeText(brief.formatted_brief_markdown);
      setCopied(true);
      setTimeout(() => setCopied(false), 2500);
    } else if (brief) {
      const summaryText = `# REACT-X EXECUTIVE SITUATION BRIEF\n\nIncident: ${brief.incident_id}\nFacility: ${brief.facility_name}\nSource: ${brief.source_asset} • ${brief.chemical}\nSeverity: ${brief.severity_score}/100 (${brief.severity_category})\nCasualties: ${brief.exposed_workers_count} exposed (${brief.casualty_triage_summary})\nEvacuation: ${brief.primary_assembly_point} via ${brief.primary_exit_gate}\nAuthorization: ${brief.human_authorization_status}`;
      navigator.clipboard.writeText(summaryText);
      setCopied(true);
      setTimeout(() => setCopied(false), 2500);
    }
  };

  const handleDownloadText = () => {
    if (!brief) return;
    const content = brief.formatted_brief_markdown || `# REACT-X EXECUTIVE SITUATION BRIEF\n\nIncident: ${brief.incident_id}\nFacility: ${brief.facility_name}\nSource: ${brief.source_asset} • ${brief.chemical}\nSeverity: ${brief.severity_score}/100 (${brief.severity_category})\nCasualties: ${brief.exposed_workers_count} exposed\nEvacuation: ${brief.primary_assembly_point} via ${brief.primary_exit_gate}\nAuthorization: ${brief.human_authorization_status}`;
    const blob = new Blob([content], { type: 'text/markdown;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `Executive_Situation_Brief_${brief.source_asset || 'INC'}_${new Date().toISOString().split('T')[0]}.md`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  };

  const handleTriggerPDF = async () => {
    if (onExportPDF) {
      onExportPDF();
      return;
    }
    setIsExportingPDF(true);
    try {
      await api.exportPrePlanPDF('FAC-IN-DAHEJ-001', brief?.source_asset || 'T-04', 'CHEM-NH3');
    } catch (e) {
      console.error('PDF export error:', e);
    } finally {
      setIsExportingPDF(false);
    }
  };

  const getRiskBadge = (category) => {
    switch (category) {
      case 'CRITICAL':
        return 'bg-red-100 dark:bg-red-950/60 text-red-800 dark:text-red-300 border-red-300 dark:border-red-800';
      case 'HIGH':
        return 'bg-orange-100 dark:bg-orange-950/60 text-orange-800 dark:text-orange-300 border-orange-300 dark:border-orange-800';
      case 'MODERATE':
        return 'bg-amber-100 dark:bg-amber-950/60 text-amber-800 dark:text-amber-300 border-amber-300 dark:border-amber-800';
      default:
        return 'bg-emerald-100 dark:bg-emerald-950/60 text-emerald-800 dark:text-emerald-300 border-emerald-300 dark:border-emerald-800';
    }
  };

  const modalContent = (
    <div 
      className="fixed inset-0 z-[10000] flex items-center justify-center p-3 sm:p-4 bg-black/80 backdrop-blur-sm animate-in fade-in duration-200 pointer-events-auto"
      onClick={onClose}
    >
      <div 
        className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl w-full max-w-4xl max-h-[92vh] flex flex-col shadow-2xl text-xs text-slate-800 dark:text-slate-200 overflow-hidden font-sans transition-colors"
        onClick={(e) => e.stopPropagation()}
      >
        
        {/* Modal Header */}
        <div className="p-4 bg-slate-50 dark:bg-slate-950 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between gap-3 shrink-0">
          <div className="flex items-center space-x-3">
            <div className="p-2 rounded-xl bg-blue-100 dark:bg-blue-950/60 border border-blue-200 dark:border-blue-800 text-blue-700 dark:text-blue-300">
              <FileText className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <span className="text-[10px] bg-blue-100 dark:bg-blue-950/60 text-blue-800 dark:text-blue-300 font-bold px-2 py-0.5 rounded-full border border-blue-200 dark:border-blue-800">
                  EXECUTIVE BRIEFING
                </span>
                <h2 className="text-base font-extrabold text-slate-900 dark:text-slate-100 tracking-tight">
                  Executive Situation Brief
                </h2>
              </div>
              <p className="text-[11px] text-slate-500 dark:text-slate-400">
                {brief?.facility_name || 'Dahej Petrochemical Complex'} • Multi-Engine Automated Operational Synthesis
              </p>
            </div>
          </div>

          <div className="flex items-center space-x-2">
            <button
              type="button"
              onClick={handleCopyMarkdown}
              className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-lg border font-bold text-xs transition-all cursor-pointer ${
                copied
                  ? 'bg-emerald-100 dark:bg-emerald-950/60 text-emerald-800 dark:text-emerald-300 border-emerald-300 dark:border-emerald-800'
                  : 'bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-200 border-slate-200 dark:border-slate-700'
              }`}
            >
              {copied ? <Check className="w-3.5 h-3.5 text-emerald-600 dark:text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
              <span>{copied ? 'COPIED' : 'COPY BRIEF'}</span>
            </button>

            <button
              type="button"
              onClick={handleDownloadText}
              className="flex items-center space-x-1.5 px-3 py-1.5 bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-200 rounded-lg border border-slate-200 dark:border-slate-700 font-bold text-xs transition-all cursor-pointer"
            >
              <Download className="w-3.5 h-3.5" />
              <span>EXPORT TXT</span>
            </button>

            <button
              type="button"
              onClick={onClose}
              className="p-1.5 rounded-lg text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors cursor-pointer"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Modal Scrollable Body */}
        <div className="flex-1 overflow-y-auto p-4 md:p-6 space-y-4">
          
          {loading && (
            <div className="p-12 text-center text-slate-400 space-y-3">
              <RefreshCw className="w-8 h-8 animate-spin text-blue-600 dark:text-blue-400 mx-auto" />
              <div className="font-bold text-slate-900 dark:text-slate-100 text-sm">Compiling Authoritative Executive Situation Brief...</div>
            </div>
          )}

          {error && (
            <div className="bg-amber-50 dark:bg-amber-950/50 border border-amber-300 dark:border-amber-800 p-4 rounded-xl text-amber-800 dark:text-amber-300 text-xs">
              <b>Notice:</b> {error}
            </div>
          )}

          {!loading && brief && (
            <div className="space-y-4">
              
              {/* Q1 & Q2: What Happened & How Serious Is It? */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                <div className="bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700 rounded-xl p-4 space-y-2">
                  <div className="text-[10px] font-bold text-blue-600 dark:text-blue-400 uppercase tracking-wider">1. WHAT HAPPENED?</div>
                  <div className="text-sm font-black text-slate-900 dark:text-slate-100">
                    {brief.source_asset} • {brief.chemical}
                  </div>
                  <div className="text-[11px] text-slate-600 dark:text-slate-300 space-y-1">
                    <div><b>Type:</b> {brief.incident_type?.replace(/_/g, ' ') || 'PIPELINE_LEAK'}</div>
                    <div><b>Sector:</b> {brief.sector || 'PETROCHEMICAL'}</div>
                    <div><b>Wind Vector:</b> {brief.wind_vector_summary || '12 km/h from NE (45°)'}</div>
                    <div><b>Plume Dispersion:</b> {brief.plume_bearing_summary || 'South-West downwind vector'}</div>
                  </div>
                </div>

                <div className="bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700 rounded-xl p-4 space-y-2">
                  <div className="text-[10px] font-bold text-red-600 dark:text-red-400 uppercase tracking-wider">2. HOW SERIOUS IS IT?</div>
                  <div className="flex items-center space-x-2">
                    <span className="text-2xl font-black text-slate-900 dark:text-slate-100">{brief.severity_score}/100</span>
                    <span className={`px-2.5 py-0.5 rounded-full text-xs font-black border ${getRiskBadge(brief.severity_category)}`}>
                      {brief.severity_category}
                    </span>
                  </div>
                  <div className="text-[11px] text-slate-600 dark:text-slate-300 space-y-1">
                    <div><b>Escalation Trend:</b> <span className="text-amber-700 dark:text-amber-300 font-bold">{brief.escalation_trend || 'MONITORED'}</span></div>
                    <div><b>Lethal Red Zone Reach:</b> {brief.max_red_reach_m ? Math.round(brief.max_red_reach_m) : 280} meters</div>
                    <div><b>Severe Orange Zone Reach:</b> {brief.max_orange_reach_m ? Math.round(brief.max_orange_reach_m) : 480} meters</div>
                  </div>
                </div>
              </div>

              {/* Q3 & Q4: Who & What Is Affected & Is It Under Control? */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                <div className="bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700 rounded-xl p-4 space-y-2">
                  <div className="text-[10px] font-bold text-amber-600 dark:text-amber-400 uppercase tracking-wider">3. WHO & WHAT IS AFFECTED?</div>
                  <div className="text-sm font-bold text-slate-900 dark:text-slate-100">
                    {brief.exposed_workers_count ?? 14} Workers Exposed • {brief.compromised_assets_count ?? 3} Units Compromised
                  </div>
                  <div className="text-[11px] text-slate-600 dark:text-slate-300 space-y-1">
                    <div><b>Casualty Triage:</b> {brief.casualty_triage_summary || '4 Lethal Red, 10 Severe Exposure'}</div>
                    <div><b>Severed Internal Roads:</b> {brief.blocked_road_segments_count ?? 1} segment</div>
                    <div><b>Site Accessibility:</b> {brief.site_accessibility_status || 'RESTRICTED ACCESS'}</div>
                  </div>
                </div>

                <div className="bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700 rounded-xl p-4 space-y-2">
                  <div className="text-[10px] font-bold text-emerald-600 dark:text-emerald-400 uppercase tracking-wider">4. TACTICAL RESPONSE & CONTAINMENT</div>
                  <div className="text-sm font-bold text-slate-900 dark:text-slate-100">
                    {brief.containment_status || 'ACTIVE SUPPRESSION'}
                  </div>
                  <div className="text-[11px] text-slate-600 dark:text-slate-300 space-y-1">
                    <div><b>Evacuation Directive:</b> Active to <b>{brief.primary_assembly_point}</b> via <b>{brief.primary_exit_gate}</b> ({brief.evacuation_distance_m}m, ~{brief.estimated_walk_time_min}m walk)</div>
                    <div><b>Lead Unit:</b> {brief.lead_tactical_unit || 'Dahej Industrial Hazmat Fire Team A'} (ETA: {brief.lead_unit_eta_min || 3} min)</div>
                    <div><b>Suppression Demand:</b> {brief.firewater_demand_lpm ? brief.firewater_demand_lpm.toLocaleString() : '4,500'} LPM Firewater • PPE: {brief.mandatory_ppe || 'Level A SCBA'}</div>
                  </div>
                </div>
              </div>

              {/* Q5: Operational Governance & Human Authorization */}
              <div className="bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700 rounded-xl p-4 space-y-3">
                <div className="flex items-center justify-between border-b border-slate-200 dark:border-slate-700 pb-2">
                  <span className="text-[10px] font-bold text-teal-700 dark:text-teal-400 uppercase tracking-wider">5. GOVERNANCE & PENDING ACTIONS</span>
                  <span className={`px-2.5 py-0.5 rounded-full text-[10px] font-bold border ${
                    brief.human_authorization_status === 'AUTHORIZED' 
                      ? 'bg-emerald-100 dark:bg-emerald-950/60 text-emerald-800 dark:text-emerald-300 border-emerald-300 dark:border-emerald-800' 
                      : 'bg-amber-100 dark:bg-amber-950/60 text-amber-800 dark:text-amber-300 border-amber-300 dark:border-amber-800'
                  }`}>
                    {brief.human_authorization_status || 'PENDING_HUMAN_AUTHORIZATION'}
                  </span>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-[11px]">
                  <div className="space-y-1.5">
                    <div className="font-bold text-slate-900 dark:text-slate-100">Key Tactical Directives:</div>
                    <ul className="space-y-1 text-slate-600 dark:text-slate-300">
                      {(brief.pending_decisions || [
                        'Authorize dynamic emergency evacuation pre-plan document',
                        'Deploy hazmat foam-water fog suppression curtain',
                        'Issue regional alert notification to Bharuch District Control Center'
                      ]).map((dec, i) => (
                        <li key={i} className="flex items-start gap-1.5">
                          <AlertTriangle className="w-3.5 h-3.5 text-amber-500 shrink-0 mt-0.5" />
                          <span>{dec}</span>
                        </li>
                      ))}
                    </ul>
                  </div>

                  <div className="bg-white dark:bg-slate-900 p-3 rounded-lg border border-slate-200 dark:border-slate-700 space-y-1">
                    <div className="font-bold text-slate-900 dark:text-slate-100">Human Authorization Audit:</div>
                    <div className="text-slate-500 dark:text-slate-400">
                      <b>Approver:</b> {brief.approver_name ? `${brief.approver_name} (${brief.approver_role})` : 'Awaiting Incident Commander / HSE Review'}
                    </div>
                    {brief.authorization_timestamp && (
                      <div className="text-slate-500 dark:text-slate-400">
                        <b>Timestamp:</b> {new Date(brief.authorization_timestamp).toUTCString()}
                      </div>
                    )}
                    <div className="pt-2">
                      <button
                        type="button"
                        onClick={handleTriggerPDF}
                        disabled={isExportingPDF}
                        className="w-full flex items-center justify-center gap-1.5 px-3 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-700 text-white font-bold text-xs transition cursor-pointer shadow-xs disabled:opacity-50"
                      >
                        {isExportingPDF ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Download className="w-3.5 h-3.5" />}
                        <span>Export Official ERDMP Pre-Plan PDF</span>
                      </button>
                    </div>
                  </div>
                </div>
              </div>

            </div>
          )}

        </div>

        {/* Modal Footer */}
        <div className="p-3 bg-slate-50 dark:bg-slate-950 border-t border-slate-200 dark:border-slate-800 flex items-center justify-between text-[11px] text-slate-500 dark:text-slate-400 shrink-0">
          <span>REACT-X INDUSTRIAL THERMAL INTELLIGENCE & EMERGENCY PRE-PLAN</span>
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-1.5 bg-slate-200 dark:bg-slate-800 hover:bg-slate-300 dark:hover:bg-slate-700 text-slate-800 dark:text-slate-100 rounded-lg font-bold cursor-pointer transition"
          >
            Close Briefing
          </button>
        </div>

      </div>
    </div>
  );

  if (typeof document !== 'undefined') {
    return createPortal(modalContent, document.body);
  }
  return modalContent;
}
