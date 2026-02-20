import { useState, useEffect, lazy, Suspense } from 'react'
import UserSignup from './components/UserSignup'
import Login from './components/Login'

const WalletDashboard = lazy(() => import('walletApp/WalletDashboard'))

function App() {
  const [user, setUser] = useState(null)
  const [token, setToken] = useState(localStorage.getItem('token'))
  const [view, setView] = useState('login') // login, signup, dashboard

  useEffect(() => {
    // If we have a token but no user, ideally we fetch user profile
    // For MVP, we'll rely on Login response setting User
    // But if we refresh, we might lose user object but keep token.
    // In real app, /api/me endpoint ensures persistence.
    // For now, if no user but token exists, just logout or ask to login again
    if (token && !user) {
      // Simple hack: if token exists, assume valid for a bit or force login
      // Better: implement GET /api/me
      // For MVP: Log out if no user object (simplifies state sync)
      if (!user) {
        setToken(null);
        localStorage.removeItem('token');
      }
    }
  }, []);

  const handleLogin = (userData, authToken) => {
    setUser(userData);
    setToken(authToken);
    localStorage.setItem('token', authToken);
    setView('dashboard');

    // Patch global fetch to include token
    // A better way is using an interceptor or specialized client
    const originalFetch = window.fetch;
    window.fetch = async (...args) => {
      let [resource, config] = args;
      config = config || {};
      config.headers = config.headers || {};
      config.headers['Authorization'] = `Bearer ${authToken}`;
      return originalFetch(resource, config);
    };
  };

  const handleLogout = () => {
    setUser(null);
    setToken(null);
    localStorage.removeItem('token');
    setView('login');
    // Restore fetch? Or reload page
    window.location.reload();
  };

  const handleUserCreated = (createdUser) => {
    alert("Account created! Please log in.");
    setView('login');
  }

  // Inject token into requests if available (Simple Interceptor Pattern)
  useEffect(() => {
    if (token) {
      const originalFetch = window.fetch;
      window.fetch = async (...args) => {
        let [resource, config] = args;
        config = config || {};
        config.headers = config.headers || {};
        if (!config.headers['Authorization']) {
          config.headers['Authorization'] = `Bearer ${token}`;
        }
        return originalFetch(resource, config);
      };
    }
  }, [token]);


  return (
    <div className="min-h-screen bg-slate-100 flex flex-col items-center py-10 px-4">
      <header className="mb-10 text-center relative w-full max-w-4xl">
        <h1 className="text-4xl font-extrabold text-transparent bg-clip-text bg-gradient-to-r from-blue-600 to-indigo-600">
          Global Genesis Super App
        </h1>
        <p className="text-slate-500 mt-2">Next-Gen Financial Operating System</p>

        {user && (
          <button
            onClick={handleLogout}
            className="absolute top-0 right-0 text-sm text-red-600 hover:text-red-800 border border-red-200 px-3 py-1 rounded"
          >
            Logout
          </button>
        )}
      </header>

      <main className="w-full max-w-4xl flex flex-col items-center gap-6">
        {!token ? (
          view === 'signup' ? (
            <>
              <UserSignup onUserCreated={handleUserCreated} />
              <button onClick={() => setView('login')} className="mt-4 text-blue-600">
                Back to Login
              </button>
            </>
          ) : (
            <Login onLogin={handleLogin} onSwitchToSignup={() => setView('signup')} />
          )
        ) : (
          <Suspense fallback={<div className="text-xl font-bold animate-pulse">Loading Wallet MFE...</div>}>
            <WalletDashboard user={user} />
          </Suspense>
        )}
      </main>
    </div>
  )
}

export default App
