import React, { useState } from 'react';
import { 
  Cpu, GitCompare, BarChart2, Activity, Camera, Sparkles, 
  Clock, ShieldCheck, FileCheck, Flame, Sliders, Layers 
} from 'lucide-react';
import PreIncidentSafetyCenter from './PreIncidentSafetyCenter';
import WhatIfComparison from './WhatIfComparison';
import DominoRiskAnalysis from './DominoRiskAnalysis';
import IncidentTimeline from './IncidentTimeline';
import DecisionAuditTrail from './DecisionAuditTrail';
import HistoricalAnalytics from './HistoricalAnalytics';
import PredictiveMaintenance from './PredictiveMaintenance';
import VisionSurveillance from './VisionSurveillance';

export default function IntelligenceHub({
  assets = [],
  chemicals = [],
  currentSimulation,
  impactResult,
  evacuationPlan,
  resourcePlan,
  authorizationStatus,
  onSimulateAssetConsequence,
  onCreateIncidentFromVision,
  initialSubTab = 'whatif'
}) {
  const [activeSubTab, setActiveSubTab] = useState(initialSubTab);

  // Grouped Intelligence Clusters
  const intelligenceGroups = [
    {
      category: 'PREDICT',
      label: 'Predictive Intel',
      items: [
        { id: 'safety_center', label: 'Early Warnings & Prevention', icon: Sliders, badge: 'PREVENTIVE' },
        { id: 'predictive', label: 'Predictive Asset Health', icon: Activity }
      ]
    },
    {
      category: 'SIMULATE',
      label: 'Simulation & What-If',
      items: [
        { id: 'whatif', label: 'What-If Consequence Simulator', icon: GitCompare }
      ]
    },
    {
      category: 'UNDERSTAND',
      label: 'Risk & Forensics',
      items: [
        { id: 'domino', label: 'Domino & Cascade Risk', icon: Flame, badge: 'DOMINO' },
        { id: 'timeline', label: 'Incident Timeline & Replay', icon: Clock },
        { id: 'analytics', label: 'Historical Incident Analytics', icon: BarChart2 }
      ]
    },
    {
      category: 'GOVERN',
      label: 'Audit & Vision',
      items: [
        { id: 'audit', label: 'Decision Audit Trail', icon: FileCheck },
        { id: 'vision', label: 'Computer Vision Surveillance', icon: Camera }
      ]
    }
  ];

  return (
    <div className="space-y-3 font-mono text-xs text-slate-200">
      
      {/* Cluster Pill Navigation Bar */}
      <div className="bg-slate-950/80 border border-slate-800 rounded-xl p-2 shadow-sm space-y-2">
        <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-800/80 pb-1.5">
          <div className="flex items-center space-x-2">
            <Cpu className="w-4 h-4 text-cyan-400" />
            <span className="font-bold text-white uppercase text-xs">ADVANCED INDUSTRIAL INTELLIGENCE WORKSPACE</span>
          </div>
          <span className="text-[10px] text-slate-400">Select analytical module below</span>
        </div>

        {/* Grouped Tabs Strip */}
        <div className="flex flex-wrap items-center gap-2">
          {intelligenceGroups.map((group) => (
            <div key={group.category} className="flex items-center space-x-1 bg-slate-900/90 rounded-lg p-1 border border-slate-800/80">
              <span className="text-[9px] text-cyan-400 font-bold px-1.5 uppercase">{group.category}:</span>
              {group.items.map((tab) => {
                const Icon = tab.icon;
                const isActive = activeSubTab === tab.id;
                return (
                  <button
                    key={tab.id}
                    type="button"
                    onClick={() => setActiveSubTab(tab.id)}
                    className={`flex items-center space-x-1.5 px-2.5 py-1 rounded text-xs font-bold transition-all ${
                      isActive
                        ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/50 shadow-sm'
                        : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
                    }`}
                  >
                    <Icon className={`w-3 h-3 ${isActive ? 'text-cyan-400' : 'text-slate-500'}`} />
                    <span>{tab.label}</span>
                    {tab.badge && (
                      <span className={`text-[8px] px-1 py-0.1 rounded font-bold border ${
                        tab.badge === 'PREVENTIVE'
                          ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40'
                          : 'bg-indigo-500/20 text-indigo-300 border-indigo-500/30'
                      }`}>
                        {tab.badge}
                      </span>
                    )}
                  </button>
                );
              })}
            </div>
          ))}
        </div>
      </div>

      {/* Module Contents */}
      {activeSubTab === 'safety_center' && (
        <PreIncidentSafetyCenter
          onNavigateToSimulator={onSimulateAssetConsequence}
        />
      )}

      {activeSubTab === 'whatif' && (
        <WhatIfComparison
          assets={assets}
          chemicals={chemicals}
          currentSimulation={currentSimulation}
        />
      )}

      {activeSubTab === 'domino' && (
        <DominoRiskAnalysis
          simulationResult={currentSimulation}
          impactResult={impactResult}
        />
      )}

      {activeSubTab === 'timeline' && (
        <IncidentTimeline
          simulationResult={currentSimulation}
          impactResult={impactResult}
          evacuationPlan={evacuationPlan}
          resourcePlan={resourcePlan}
          authorizationStatus={authorizationStatus}
        />
      )}

      {activeSubTab === 'audit' && (
        <DecisionAuditTrail
          incidentId={currentSimulation?.id}
        />
      )}

      {activeSubTab === 'analytics' && (
        <HistoricalAnalytics />
      )}

      {activeSubTab === 'predictive' && (
        <PredictiveMaintenance
          onSimulateAssetConsequence={onSimulateAssetConsequence}
        />
      )}

      {activeSubTab === 'vision' && (
        <VisionSurveillance
          onCreateIncidentFromVision={onCreateIncidentFromVision}
        />
      )}

    </div>
  );
}
