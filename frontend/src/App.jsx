import React, { useState, useEffect } from 'react';
import { ThemeProvider, useTheme } from './context/ThemeContext';
import AuthLanding from './pages/AuthLanding';
import CommandDashboard from './pages/CommandDashboard';
import DemoCommandRoom from './pages/DemoCommandRoom';

function AppContent() {
  const { isDark } = useTheme();
  const [currentUser, setCurrentUser] = useState({
    id: 'USR-OP-01',
    name: 'Chief Safety Controller',
    role: 'HSE_COMMANDER',
    isDemo: false
  });
  const [currentRole, setCurrentRole] = useState('HSE_COMMANDER');
  
  // Experience Mode: 'INDIA_OPERATIONS' (default) vs 'DEMO_COMMAND_ROOM'
  const [activeMode, setActiveMode] = useState(() => {
    if (typeof window !== 'undefined' && window.location.pathname === '/demo') {
      return 'DEMO_COMMAND_ROOM';
    }
    return 'INDIA_OPERATIONS';
  });

  useEffect(() => {
    const handlePopState = () => {
      if (window.location.pathname === '/demo') {
        setActiveMode('DEMO_COMMAND_ROOM');
      } else {
        setActiveMode('INDIA_OPERATIONS');
      }
    };
    window.addEventListener('popstate', handlePopState);
    return () => window.removeEventListener('popstate', handlePopState);
  }, []);

  const switchMode = (mode) => {
    setActiveMode(mode);
    if (typeof window !== 'undefined' && window.history) {
      const path = mode === 'DEMO_COMMAND_ROOM' ? '/demo' : '/command';
      window.history.pushState(null, '', path);
    }
  };

  const handleLoginSuccess = (userData) => {
    setCurrentUser(userData);
    if (userData.role) {
      setCurrentRole(userData.role);
    }
  };

  const handleLogout = () => {
    setCurrentUser(null);
  };

  if (!currentUser) {
    return (
      <div className="min-h-screen bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-slate-100 antialiased font-sans transition-colors">
        <AuthLanding onLoginSuccess={handleLoginSuccess} />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-slate-100 antialiased font-sans transition-colors">
      {activeMode === 'DEMO_COMMAND_ROOM' ? (
        <DemoCommandRoom
          user={currentUser}
          onSwitchToIndiaOps={() => switchMode('INDIA_OPERATIONS')}
          onLogout={handleLogout}
        />
      ) : (
        <CommandDashboard
          user={currentUser}
          currentRole={currentRole}
          onRoleChange={setCurrentRole}
          onLogout={handleLogout}
          onSwitchToDemo={() => switchMode('DEMO_COMMAND_ROOM')}
        />
      )}
    </div>
  );
}

export default function App() {
  return (
    <ThemeProvider>
      <AppContent />
    </ThemeProvider>
  );
}
