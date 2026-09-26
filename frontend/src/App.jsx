import React, { useState, useEffect } from 'react';
import { ThemeProvider, useTheme } from './context/ThemeContext';
import AuthLanding from './pages/AuthLanding';
import CommandDashboard from './pages/CommandDashboard';
import DemoCommandRoom from './pages/DemoCommandRoom';

const AUTH_STORAGE_KEY = 'reactx-auth-session';

function AppContent() {
  const { isDark } = useTheme();
  
  // Session initializes strictly from localStorage; unauthenticated visits start at null (login gate)
  const [currentUser, setCurrentUser] = useState(() => {
    if (typeof window !== 'undefined') {
      try {
        const saved = localStorage.getItem(AUTH_STORAGE_KEY);
        if (saved) {
          const parsed = JSON.parse(saved);
          if (parsed && (parsed.email || parsed.id)) return parsed;
        }
      } catch (e) {
        console.warn('Failed to parse saved auth session:', e);
      }
    }
    return null;
  });

  const [currentRole, setCurrentRole] = useState(() => {
    if (typeof window !== 'undefined') {
      try {
        const saved = localStorage.getItem(AUTH_STORAGE_KEY);
        if (saved) {
          const parsed = JSON.parse(saved);
          if (parsed && parsed.role) return parsed.role;
        }
      } catch (e) {}
    }
    return 'HSE_COMMANDER';
  });
  
  // Intended destination memory for unauthenticated deep links
  const [intendedPath, setIntendedPath] = useState(() => {
    if (typeof window !== 'undefined') {
      return window.location.pathname || '/';
    }
    return '/';
  });

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
    const sessionData = {
      ...userData,
      authenticatedAt: new Date().toISOString()
    };
    setCurrentUser(sessionData);
    if (userData.role) {
      setCurrentRole(userData.role);
    }
    try {
      localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(sessionData));
    } catch (e) {
      console.warn('Failed to persist auth session:', e);
    }

    // Preserve intended deep-link destination
    if (intendedPath === '/demo') {
      setActiveMode('DEMO_COMMAND_ROOM');
      if (window.history) window.history.pushState(null, '', '/demo');
    } else {
      setActiveMode('INDIA_OPERATIONS');
      if (window.history) window.history.pushState(null, '', '/command');
    }
  };

  const handleLogout = () => {
    setCurrentUser(null);
    try {
      localStorage.removeItem(AUTH_STORAGE_KEY);
    } catch (e) {}
    if (typeof window !== 'undefined' && window.history) {
      window.history.pushState(null, '', '/');
    }
  };

  // Route Gate: If unauthenticated, always render Login / Sign Up
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

