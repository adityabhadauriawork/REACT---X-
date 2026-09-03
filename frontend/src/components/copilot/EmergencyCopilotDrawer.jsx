import React, { useState, useRef, useEffect } from 'react';
import { 
  Bot, Sparkles, Send, X, RefreshCw, 
  MessageSquare, ShieldCheck, Zap, HelpCircle 
} from 'lucide-react';
import { api } from '../../services/api';

export default function EmergencyCopilotDrawer({
  simulationResult,
  impactResult,
  evacuationPlan,
  resourcePlan,
  userRole = 'HSE_COMMANDER',
  onNavigateTab
}) {
  const [isOpen, setIsOpen] = useState(false);
  const [query, setQuery] = useState('');
  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      content: '👋 **REACT-X AI Operations Assistant Ready.**\nI can analyze satellite thermal hotspots, evaluate industrial facility baselines, explain dispersion physics, and assist with evacuation corridors.',
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    }
  ]);
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    if (isOpen) scrollToBottom();
  }, [messages, isOpen]);

  const handleSend = async (textToSend = null) => {
    const q = textToSend || query;
    if (!q.trim() || loading) return;

    const userMsg = {
      role: 'user',
      content: q.trim(),
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    };

    setMessages(prev => [...prev, userMsg]);
    setQuery('');
    setLoading(true);

    try {
      const res = await api.chatWithCopilot({
        query: q.trim(),
        user_role: userRole,
        history: messages.slice(-6),
        simulation_result: simulationResult,
        impact_result: impactResult,
        evacuation_plan: evacuationPlan,
        resource_plan: resourcePlan
      });

      const botMsg = {
        role: 'assistant',
        content: res.reply,
        intent: res.intent_detected,
        metrics: res.grounded_metrics,
        followups: res.suggested_followups,
        action: res.action_recommended,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      };
      setMessages(prev => [...prev, botMsg]);
    } catch (err) {
      console.error('Copilot error:', err);
      setMessages(prev => [
        ...prev,
        {
          role: 'assistant',
          content: '⚠ Failed to process emergency copilot query. Please verify backend connection.',
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        }
      ]);
    } finally {
      setLoading(false);
    }
  };

  const quickPrompts = userRole === 'FIELD_RESPONDER' ? [
    'What should I do right now?',
    'Where is my safe route?',
    'What PPE is required?',
    'What is the wind standoff?'
  ] : userRole === 'EXECUTIVE_AUTHORITY' ? [
    'What is the current status?',
    'Who approved this plan?',
    'How many workers are affected?',
    'Generate executive brief'
  ] : [
    'What is happening right now?',
    'Why was AP-3 selected?',
    'How many workers are affected?',
    'What if release rate doubles?',
    'Who approved this plan?'
  ];

  return (
    <>
      {/* 1. DEFAULT STATE: High z-index circular floating launcher (~54px) */}
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        title={isOpen ? "Close AI Copilot" : "Open AI Emergency Copilot"}
        aria-label="Toggle AI Emergency Copilot"
        className={`fixed bottom-5 right-5 z-[9999] flex items-center justify-center w-13 h-13 sm:w-14 sm:h-14 rounded-full shadow-2xl transition-all duration-300 border font-mono ${
          isOpen
            ? 'bg-slate-800 text-slate-300 border-slate-600 hover:bg-slate-700 rotate-90'
            : 'bg-gradient-to-tr from-cyan-600 via-teal-600 to-indigo-600 hover:from-cyan-500 hover:to-indigo-500 text-white border-cyan-400/60 hover:scale-105 active:scale-95 shadow-cyan-500/30'
        }`}
        style={{ width: '54px', height: '54px' }}
      >
        {isOpen ? (
          <X className="w-5 h-5" />
        ) : (
          <div className="relative flex items-center justify-center">
            <Bot className="w-6 h-6" />
            <span className="absolute -top-1 -right-1 w-2.5 h-2.5 bg-emerald-400 rounded-full animate-ping"></span>
            <span className="absolute -top-1 -right-1 w-2.5 h-2.5 bg-emerald-400 rounded-full"></span>
          </div>
        )}
      </button>

      {/* 2. OPEN STATE: Compact Bounded Slide-Over Drawer Panel */}
      {isOpen && (
        <div 
          className="fixed bottom-22 right-5 z-[9999] w-[calc(100vw-2.5rem)] sm:w-[360px] md:w-[380px] lg:w-[400px] h-[480px] max-h-[calc(100vh-120px)] bg-slate-950/95 border border-slate-700/90 rounded-2xl shadow-2xl flex flex-col font-mono text-xs overflow-hidden backdrop-blur-md transition-all duration-200 animate-in fade-in slide-in-from-bottom-4"
        >
          {/* Top Header */}
          <div className="bg-slate-900/90 px-3.5 py-2.5 border-b border-slate-800 flex items-center justify-between shrink-0">
            <div className="flex items-center gap-2">
              <div className="w-6 h-6 rounded-lg bg-gradient-to-tr from-cyan-600 to-indigo-600 flex items-center justify-center text-white shadow-sm">
                <Bot className="w-3.5 h-3.5" />
              </div>
              <div>
                <div className="font-bold text-white text-xs flex items-center gap-1.5 leading-none">
                  <span>AI Emergency Copilot</span>
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
                </div>
                <span className="text-[9.5px] text-slate-400 leading-none">Grounded in Active Telemetry</span>
              </div>
            </div>

            <button
              type="button"
              onClick={() => setIsOpen(false)}
              className="p-1 rounded text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
              title="Close Copilot"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          {/* Quick Prompt Chips */}
          <div className="bg-slate-900/50 px-2 py-1.5 border-b border-slate-800/80 flex gap-1.5 overflow-x-auto shrink-0 scrollbar-thin">
            {quickPrompts.map((p, idx) => (
              <button
                key={idx}
                type="button"
                onClick={() => handleSend(p)}
                className="px-2 py-0.5 rounded-full bg-slate-800 hover:bg-slate-700 text-slate-300 text-[9.5px] whitespace-nowrap border border-slate-700 transition-colors shrink-0"
              >
                {p}
              </button>
            ))}
          </div>

          {/* Message Thread (Internal Independent Scroll) */}
          <div className="flex-1 p-3 space-y-2.5 overflow-y-auto min-h-0">
            {messages.map((m, idx) => {
              const isBot = m.role === 'assistant';
              return (
                <div key={idx} className={`flex flex-col ${isBot ? 'items-start' : 'items-end'}`}>
                  <div className={`max-w-[92%] p-2.5 rounded-xl text-[11px] leading-relaxed shadow-sm ${
                    isBot 
                      ? 'bg-slate-900 text-slate-200 border border-slate-800 rounded-tl-sm' 
                      : 'bg-gradient-to-r from-cyan-600 to-teal-600 text-white rounded-tr-sm'
                  }`}>
                    {/* Message content */}
                    <div className="whitespace-pre-wrap">
                      {m.content}
                    </div>

                    {/* Follow-up action buttons */}
                    {m.followups && m.followups.length > 0 && (
                      <div className="mt-2 pt-1.5 border-t border-slate-800/80 space-y-1">
                        <span className="text-[9px] text-slate-400 font-bold block">SUGGESTED ACTIONS:</span>
                        <div className="flex flex-wrap gap-1">
                          {m.followups.map((f, fIdx) => (
                            <button
                              key={fIdx}
                              type="button"
                              onClick={() => {
                                if (f.includes('What-If') || f.includes('doubles')) {
                                  onNavigateTab && onNavigateTab('intelligence');
                                }
                                handleSend(f);
                              }}
                              className="text-[9px] bg-slate-950 px-2 py-0.5 rounded text-cyan-300 border border-slate-800 hover:border-cyan-500 transition-colors"
                            >
                              → {f}
                            </button>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                  <span className="text-[8px] text-slate-500 mt-0.5 px-1">{m.timestamp}</span>
                </div>
              );
            })}
            
            {loading && (
              <div className="flex items-center gap-2 text-slate-400 text-[11px] bg-slate-900 p-2 rounded-lg border border-slate-800 w-fit">
                <RefreshCw className="w-3 h-3 animate-spin text-cyan-400" />
                <span>Analyzing Gaussian plume physics & routing topology...</span>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Input Bar */}
          <div className="p-2.5 bg-slate-900/90 border-t border-slate-800 flex items-center gap-1.5 shrink-0">
            <input
              type="text"
              placeholder="Ask Copilot (e.g. 'Why is AP-1 unsafe?')..."
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter') handleSend(); }}
              className="flex-1 bg-slate-950 border border-slate-700 rounded-lg px-2.5 py-1.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-cyan-500"
            />
            <button
              type="button"
              onClick={() => handleSend()}
              disabled={!query.trim() || loading}
              className="p-1.5 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-white disabled:opacity-40 transition-all active:scale-95 shrink-0"
            >
              <Send className="w-3.5 h-3.5" />
            </button>
          </div>

        </div>
      )}
    </>
  );
}
