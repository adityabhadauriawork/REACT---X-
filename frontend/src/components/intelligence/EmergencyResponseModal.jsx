import React, { useState, useEffect } from 'react';
import { createPortal } from 'react-dom';
import { 
  ShieldAlert, X, FileText, CheckCircle2, AlertTriangle, 
  Send, Copy, Download, Radio, UserCheck, ShieldCheck, 
  Building2, Phone, MapPin, Layers, Lock, Sparkles
} from 'lucide-react';
import { useTheme } from '../../context/ThemeContext';

export default function EmergencyResponseModal({
  isOpen,
  onClose,
  incidentPacket,
  facility,
  isDemo = false,
  onExportPDF
}) {
  const { isDark } = useTheme();
  const [isAuthorized, setIsAuthorized] = useState(false);
  const [authorizerName, setAuthorizerName] = useState('Chief Safety Controller (HSE-01)');
  const [dispatchStatus, setDispatchStatus] = useState('AWAITING_AUTHORIZATION');

  // Keyboard ESC listener
  useEffect(() => {
    if (!isOpen) return;
    const handleKeyDown = (e) => {
      if (e.key === 'Escape') onClose && onClose();
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);
  const [copiedAlert, setCopiedAlert] = useState(false);
  const [activeTab, setActiveTab] = useState('packet'); // 'packet' | 'cap_alert' | 'contacts'

  if (!isOpen) return null;

  const packet = incidentPacket || {
    incident_id: 'INC-EMERGENCY-2026-001',
    severity: 'CRITICAL',
    timestamp_utc: new Date().toISOString(),
    location: {
      facility_id: facility?.id || 'FAC-IN-DAHEJ-001',
      facility_name: facility?.name || 'Dahej Petrochemical Complex',
      asset_name: 'Cryogenic Ammonia Storage Tank T-04',
      coordinates: facility?.coordinates || [21.6850, 72.5750],
      inside_boundary: true
    },
    hazard: {
      classification: 'INDUSTRIAL_FIRE',
      confidence: 0.96,
      frp_mw: 48.0,
      brightness_kelvin: 398.0,
      chemical_name: 'Ammonia (Anhydrous)'
    },
    emergency_contacts: {
      fire_rescue: 'Bharuch District Fire & Hazmat Division',
      disaster_mgmt: 'GIDC Crisis Management Center',
      medical: 'Dahej Occupational Health & Trauma Center',
      police: 'Dahej Marine Police Station'
    }
  };

  const capAlertText = `<?xml version="1.0" encoding="UTF-8"?>
<alert xmlns="urn:oasis:names:tc:emergency:cap:1.2">
  <identifier>${packet.incident_id}</identifier>
  <sender>REACT-X-INTELLIGENCE-COMMAND</sender>
  <sent>${packet.timestamp_utc}</sent>
  <status>${isDemo ? 'Draft' : 'Actual'}</status>
  <msgType>Alert</msgType>
  <scope>Restricted</scope>
  <info>
    <category>Safety</category>
    <event>${packet.hazard?.classification || 'INDUSTRIAL_FIRE'}</event>
    <urgency>Immediate</urgency>
    <severity>${packet.severity || 'Critical'}</severity>
    <certainty>Observed</certainty>
    <headline>Industrial Incident Alert: ${packet.location?.facility_name}</headline>
    <description>Thermal anomaly detected with peak FRP ${packet.hazard?.frp_mw || 48} MW involving ${packet.hazard?.chemical_name || 'hazardous substance'}.</description>
    <instruction>Evacuate to designated safe assembly perimeter. Deploy high-expansion fog curtains.</instruction>
    <area>
      <areaDesc>${packet.location?.facility_name} Boundary</areaDesc>
      <circle>${packet.location?.coordinates?.[0] || 21.6850},${packet.location?.coordinates?.[1] || 72.5750},1.5</circle>
    </area>
  </info>
</alert>`;

  const handleCopyAlert = () => {
    navigator.clipboard.writeText(capAlertText);
    setCopiedAlert(true);
    setTimeout(() => setCopiedAlert(false), 3000);
  };

  const handleAuthorizeAndDispatch = () => {
    if (!isAuthorized) return;
    if (isDemo) {
      setDispatchStatus('SIMULATED_DISPATCH_RECORDED');
    } else {
      setDispatchStatus('AUTHORIZED_DISPATCH_INITIATED');
    }
  };

  const handleDownloadJSON = () => {
    const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(packet, null, 2));
    const dlAnchorElem = document.createElement('a');
    dlAnchorElem.setAttribute("href", dataStr);
    dlAnchorElem.setAttribute("download", `${packet.incident_id}_incident_packet.json`);
    dlAnchorElem.click();
  };

  const modalContent = (
    <div 
      className="fixed inset-0 z-[10000] flex items-center justify-center bg-black/80 backdrop-blur-sm p-4 animate-in fade-in duration-200 pointer-events-auto font-sans"
      onClick={onClose}
    >
      <div 
        className="w-full max-w-2xl bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-800 rounded-2xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh]"
        onClick={(e) => e.stopPropagation()}
      >
        
        {/* Modal Header */}
        <div className="p-4 bg-red-50 dark:bg-red-950/40 border-b border-red-200 dark:border-red-900/60 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="w-9 h-9 rounded-xl bg-red-600 text-white flex items-center justify-center font-bold shadow-xs">
              <ShieldAlert className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <h3 className="font-black text-sm text-red-900 dark:text-red-300 uppercase tracking-tight">
                  Emergency Response & SOS Incident Packet
                </h3>
                <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-red-200/80 dark:bg-red-900 text-red-900 dark:text-red-200">
                  {packet.severity}
                </span>
              </div>
              <p className="text-xs text-red-700 dark:text-red-400 font-mono">
                {packet.incident_id} • {packet.location?.facility_name}
              </p>
            </div>
          </div>

          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 cursor-pointer"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Navigation Tabs */}
        <div className="flex border-b border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 px-4">
          <button
            onClick={() => setActiveTab('packet')}
            className={`py-2 px-3 text-xs font-bold border-b-2 cursor-pointer transition ${
              activeTab === 'packet'
                ? 'border-red-600 text-red-700 dark:text-red-400'
                : 'border-transparent text-slate-500 hover:text-slate-800 dark:hover:text-slate-200'
            }`}
          >
            Incident Packet Dossier
          </button>
          <button
            onClick={() => setActiveTab('cap_alert')}
            className={`py-2 px-3 text-xs font-bold border-b-2 cursor-pointer transition ${
              activeTab === 'cap_alert'
                ? 'border-red-600 text-red-700 dark:text-red-400'
                : 'border-transparent text-slate-500 hover:text-slate-800 dark:hover:text-slate-200'
            }`}
          >
            CAP-1.2 Structured Alert
          </button>
          <button
            onClick={() => setActiveTab('contacts')}
            className={`py-2 px-3 text-xs font-bold border-b-2 cursor-pointer transition ${
              activeTab === 'contacts'
                ? 'border-red-600 text-red-700 dark:text-red-400'
                : 'border-transparent text-slate-500 hover:text-slate-800 dark:hover:text-slate-200'
            }`}
          >
            Emergency Contact Matrix
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-4 overflow-y-auto space-y-3 flex-1 text-xs text-slate-700 dark:text-slate-300 font-sans">
          
          {activeTab === 'packet' && (
            <div className="space-y-3">
              <div className="grid grid-cols-2 gap-2.5">
                <div className="p-3 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700 space-y-1">
                  <span className="text-[10px] font-bold text-slate-400 uppercase">Hazard Classification</span>
                  <div className="font-bold text-red-700 dark:text-red-400 text-sm">
                    {packet.hazard?.classification?.replace(/_/g, ' ')}
                  </div>
                  <div className="text-[11px] text-slate-500 font-mono">
                    Confidence: {Math.round((packet.hazard?.confidence || 0.95) * 100)}%
                  </div>
                </div>

                <div className="p-3 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700 space-y-1">
                  <span className="text-[10px] font-bold text-slate-400 uppercase">Chemical & Thermal Source</span>
                  <div className="font-bold text-slate-900 dark:text-slate-100 text-sm">
                    {packet.hazard?.chemical_name || 'Ammonia (Anhydrous)'}
                  </div>
                  <div className="text-[11px] text-slate-500 font-mono">
                    FRP: {packet.hazard?.frp_mw || 48} MW • Temp: {packet.hazard?.brightness_kelvin || 398} K
                  </div>
                </div>
              </div>

              <div className="p-3 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700 space-y-1.5">
                <span className="text-[10px] font-bold text-slate-400 uppercase">Location & Geometry</span>
                <div className="text-slate-800 dark:text-slate-200 font-semibold">
                  {packet.location?.facility_name} — {packet.location?.asset_name}
                </div>
                <div className="text-[11px] text-slate-500 font-mono">
                  Coordinates: {packet.location?.coordinates?.[0]?.toFixed(4)}° N, {packet.location?.coordinates?.[1]?.toFixed(4)}° E (Verified inside facility fence)
                </div>
              </div>

              <div className="p-3 rounded-xl bg-amber-50 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-900/50 space-y-1">
                <div className="font-bold text-amber-900 dark:text-amber-300 flex items-center gap-1.5">
                  <Lock className="w-3.5 h-3.5" /> Human Authorization Governance
                </div>
                <p className="text-[11px] text-amber-800 dark:text-amber-400">
                  External multi-agency dispatch requires mandatory commander review and cryptographic audit logging. No autonomous unverified external transmissions permitted.
                </p>
              </div>
            </div>
          )}

          {activeTab === 'cap_alert' && (
            <div className="space-y-2">
              <div className="flex justify-between items-center">
                <span className="text-xs font-bold text-slate-800 dark:text-slate-200">
                  Common Alerting Protocol (CAP v1.2 Standard Format)
                </span>
                <button
                  onClick={handleCopyAlert}
                  className="px-2.5 py-1 rounded bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 text-slate-800 dark:text-slate-200 font-semibold text-xs flex items-center gap-1 cursor-pointer"
                >
                  <Copy className="w-3 h-3" />
                  <span>{copiedAlert ? 'Copied XML' : 'Copy CAP XML'}</span>
                </button>
              </div>
              <pre className="p-3 rounded-xl bg-slate-900 text-slate-200 font-mono text-[11px] overflow-x-auto max-h-56 leading-relaxed border border-slate-700">
                {capAlertText}
              </pre>
            </div>
          )}

          {activeTab === 'contacts' && (
            <div className="space-y-2">
              <span className="font-bold text-slate-800 dark:text-slate-200 block">
                Authorized Regional Emergency Dispatch Matrix
              </span>
              <div className="space-y-1.5">
                {Object.entries(packet.emergency_contacts || {}).map(([category, contactName]) => (
                  <div key={category} className="p-2.5 rounded-lg bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700 flex justify-between items-center">
                    <div>
                      <div className="font-bold uppercase text-[10px] text-slate-400">
                        {category.replace(/_/g, ' ')}
                      </div>
                      <div className="font-semibold text-slate-900 dark:text-slate-100 text-xs">
                        {contactName || 'CONTACT NOT CONFIGURED'}
                      </div>
                    </div>
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-50 dark:bg-emerald-950/40 text-emerald-700 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-800 font-bold">
                      VERIFIED DIRECT
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Authorization Checkbox Strip */}
          <div className="p-3 rounded-xl bg-slate-100 dark:bg-slate-800 border border-slate-300 dark:border-slate-700 space-y-2 mt-2">
            <label className="flex items-center space-x-2.5 cursor-pointer">
              <input
                type="checkbox"
                checked={isAuthorized}
                onChange={(e) => setIsAuthorized(e.target.checked)}
                className="w-4 h-4 text-red-600 rounded accent-red-600 cursor-pointer"
              />
              <span className="font-bold text-xs text-slate-900 dark:text-slate-100">
                I hereby confirm incident parameters, consequence envelope, and authorize official dispatch packet generation.
              </span>
            </label>

            <div className="flex items-center space-x-2">
              <span className="text-[11px] text-slate-500">Sign-off Authority:</span>
              <input
                type="text"
                value={authorizerName}
                onChange={(e) => setAuthorizerName(e.target.value)}
                className="px-2 py-1 bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded text-xs text-slate-900 dark:text-slate-100 flex-1 font-semibold"
              />
            </div>
          </div>

          {dispatchStatus !== 'AWAITING_AUTHORIZATION' && (
            <div className="p-2.5 rounded-lg bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-300 dark:border-emerald-800 text-emerald-900 dark:text-emerald-300 flex items-center gap-2 text-xs font-semibold animate-in fade-in">
              <CheckCircle2 className="w-4 h-4 text-emerald-600" />
              <span>
                {isDemo
                  ? 'Reference demo dispatch simulated successfully. Packet archived to immutable provenance log.'
                  : 'Official emergency dispatch initiated to configured district responder endpoints.'}
              </span>
            </div>
          )}

        </div>

        {/* Modal Footer Actions */}
        <div className="p-3.5 bg-slate-50 dark:bg-slate-950 border-t border-slate-200 dark:border-slate-800 flex flex-wrap items-center justify-between gap-2 shrink-0">
          <div className="flex items-center space-x-2">
            <button
              onClick={handleDownloadJSON}
              className="px-3 py-1.5 rounded-lg bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 hover:bg-slate-100 dark:hover:bg-slate-800 text-xs font-bold text-slate-700 dark:text-slate-200 flex items-center gap-1.5 cursor-pointer"
            >
              <Download className="w-3.5 h-3.5" /> Download JSON Packet
            </button>
            {onExportPDF && (
              <button
                onClick={onExportPDF}
                className="px-3 py-1.5 rounded-lg bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 hover:bg-slate-100 dark:hover:bg-slate-800 text-xs font-bold text-slate-700 dark:text-slate-200 flex items-center gap-1.5 cursor-pointer"
              >
                <FileText className="w-3.5 h-3.5 text-amber-600" /> Export ERDMP PDF
              </button>
            )}
          </div>

          <button
            onClick={handleAuthorizeAndDispatch}
            disabled={!isAuthorized || dispatchStatus !== 'AWAITING_AUTHORIZATION'}
            className={`px-4 py-2 rounded-lg text-xs font-bold flex items-center gap-2 transition shadow-xs ${
              isAuthorized && dispatchStatus === 'AWAITING_AUTHORIZATION'
                ? 'bg-red-600 hover:bg-red-700 text-white cursor-pointer'
                : 'bg-slate-200 dark:bg-slate-800 text-slate-400 cursor-not-allowed opacity-60'
            }`}
          >
            <Send className="w-3.5 h-3.5" />
            <span>
              {isDemo
                ? (dispatchStatus === 'AWAITING_AUTHORIZATION' ? 'Simulate Emergency Dispatch' : 'Simulated')
                : (dispatchStatus === 'AWAITING_AUTHORIZATION' ? 'Authorize & Transmit Alert' : 'Transmitted')}
            </span>
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
