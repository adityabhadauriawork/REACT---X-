import React, { useState } from 'react';
import AuthLanding from './pages/AuthLanding';
import CommandDashboard from './pages/CommandDashboard';

function App() {
  const [currentUser, setCurrentUser] = useState(null);
  const [currentRole, setCurrentRole] = useState('HSE_COMMANDER');

  const handleLoginSuccess = (userData) => {
    setCurrentUser(userData);
    if (userData.role) {
      setCurrentRole(userData.role);
    }
  };

  const handleLogout = () => {
    setCurrentUser(null);
  };

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 antialiased font-sans">
      {!currentUser ? (
        <AuthLanding onLoginSuccess={handleLoginSuccess} />
      ) : (
        <CommandDashboard
          user={currentUser}
          currentRole={currentRole}
          onRoleChange={setCurrentRole}
          onLogout={handleLogout}
        />
      )}
    </div>
  );
}

export default App;

