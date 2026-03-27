import { useState, useEffect, useRef, lazy, Suspense } from 'react'
import UserSignup from './components/UserSignup'
import Login from './components/Login'
import AdminPanel from './components/AdminPanel'
import PasskeyButton from './components/PasskeyButton'
import './index.css'

/* ── WebSocket hook ─────────────────────────────────────────────────────────── */
function useNotifications(user, token, showToast) {
  const wsRef = useRef(null)
  const retryRef = useRef(null)

  const connect = () => {
    if (!user || !token) return
    if (wsRef.current?.readyState === WebSocket.OPEN) return

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const gatewayHost = 'localhost:8000'
    const url = `${protocol}//${gatewayHost}/ws/${user.user_id}?token=${token}`

    try {
      const ws = new WebSocket(url)
      wsRef.current = ws

      ws.onmessage = (e) => {
        try {
          const data = JSON.parse(e.data)
          if (data.event === 'transfer_received') {
            showToast(`Received ${data.amount?.toFixed(2)} ${data.currency}!`, 'success')
          }
        } catch { }
      }

      ws.onerror = () => { }
      ws.onclose = () => {
        wsRef.current = null
        retryRef.current = setTimeout(connect, 5000)
      }
    } catch (e) {
      console.warn('WebSocket failed:', e)
    }
  }

  useEffect(() => {
    if (user && token) {
      setTimeout(connect, 500)
    }
    return () => {
      clearTimeout(retryRef.current)
      wsRef.current?.close()
    }
  }, [user?.user_id, token])
}

/* ── Global toast state ─────────────────────────────────────────────────────── */
const Toast = ({ toast }) => toast ? (
  <div className={`fixed top-24 right-6 z-[9999] px-6 py-4 rounded-2xl text-sm font-bold text-white shadow-2xl backdrop-blur-xl animate-premium-in ${toast.type === 'success' ? 'bg-emerald-500/90' : 'bg-rose-500/90'}`}>
    {toast.msg}
  </div>
) : null

/* ── Profile mini-view ─────────────────────────────────── */
const REGION_NAMES = { 0: 'Unspecified', 1: 'India 🇮🇳', 2: 'Europe 🇪🇺', 3: 'USA 🇺🇸' }
const KYC_STATUS = { 0: { color: 'text-slate-500 bg-slate-500/10', label: 'Unspecified' }, 1: { color: 'text-amber-500 bg-amber-500/10', label: 'Pending' }, 2: { color: 'text-emerald-500 bg-emerald-500/10', label: 'Verified' }, 3: { color: 'text-rose-500 bg-rose-500/10', label: 'Failed' } }

const ProfileModal = ({ user, onClose, onUpdated }) => {
  const [name, setName] = useState(user.name)
  const [saving, setSaving] = useState(false)
  const [msg, setMsg] = useState(null)

  const save = async () => {
    setSaving(true)
    try {
      const r = await fetch('/api/me', { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ name }) })
      if (r.ok) { const d = await r.json(); onUpdated(d.name); setMsg({ type: 'ok', text: 'Profile updated!' }) }
      else setMsg({ type: 'err', text: 'Update failed' })
    } catch { setMsg({ type: 'err', text: 'Network error' }) }
    finally { setSaving(false) }
  }

  const kyc = KYC_STATUS[user.kyc_status || 0]

  return (
    <div className="fixed inset-0 bg-black/80 backdrop-blur-md z-[1000] flex items-center justify-center p-6 animate-premium-in" onClick={onClose}>
      <div onClick={e => e.stopPropagation()} className="premium-glass p-8 w-full max-w-md animate-premium-in">
        <div className="flex items-center justify-between mb-8">
          <h2 className="text-2xl font-black text-premium-gradient">User Identity</h2>
          <button onClick={onClose} className="text-slate-500 hover:text-white transition-colors">✕</button>
        </div>

        <div className="flex items-center gap-6 mb-8 p-4 bg-white/5 rounded-2xl">
          <div className="w-16 h-16 rounded-full bg-gradient-to-br from-indigo-500 to-violet-500 flex items-center justify-center text-2xl font-black shadow-xl">
            {user.name?.charAt(0).toUpperCase()}
          </div>
          <div>
            <div className="font-bold text-lg">{user.name}</div>
            <div className="text-sm text-slate-500 font-medium">{user.email}</div>
          </div>
        </div>

        <div className="space-y-4 mb-8">
          {[
            { label: 'Cloud Node', value: REGION_NAMES[user.region] || 'Unspecified' },
            { label: 'KYC Security', value: kyc.label, customStyle: kyc.color },
            ...(user.is_admin ? [{ label: 'Access Level', value: '🔐 Admin Shell', customStyle: 'text-rose-400 bg-rose-400/10' }] : [])
          ].map(r => (
            <div key={r.label} className="flex justify-between items-center text-sm py-1">
              <span className="text-slate-500 font-bold uppercase tracking-widest text-[10px]">{r.label}</span>
              <span className={`font-black px-3 py-1 rounded-full text-xs ${r.customStyle || 'text-slate-200'}`}>{r.value}</span>
            </div>
          ))}
        </div>

        <div className="space-y-3">
          <label className="text-[10px] font-black text-slate-500 uppercase tracking-widest px-1">Display Identity</label>
          <div className="flex gap-2">
            <input value={name} onChange={e => setName(e.target.value)} className="premium-input flex-1 h-12" />
            <button onClick={save} disabled={saving || name === user.name} className="premium-btn px-6 disabled:opacity-30">
              {saving ? '...' : 'Save'}
            </button>
          </div>
          {msg && <div className={`text-xs px-1 ${msg.type === 'ok' ? 'text-emerald-400' : 'text-rose-400'}`}>{msg.text}</div>}
        </div>

        <div className="mt-8 pt-8 border-t border-white/5">
          <div className="text-[10px] font-black text-slate-500 uppercase tracking-widest mb-4 px-1 text-center">Biometric Authentication</div>
          <PasskeyButton
            mode="register"
            token={localStorage.getItem('token')}
            onSuccess={() => setMsg({ type: 'ok', text: '🔑 Passkey registered!' })}
            onError={(e) => setMsg({ type: 'err', text: e })}
          />
        </div>
      </div>
    </div>
  )
}

/* ── Mini-App Bridge Container ───────────────────────────────────────────────── */
const MINI_APP_PERMISSIONS = {
  'wallet-mfe': ['payment.request', 'identity.get'],
  'marketplace': ['identity.get', 'payment.request'],
  'fitness-tracker': ['identity.get']
}

const MiniAppView = ({ appName, url, user, onPaymentRequest }) => {
  const iframeRef = useRef(null)

  useEffect(() => {
    const handleMessage = async (event) => {
      const { jsonrpc, id, method, params } = event.data || {}
      if (jsonrpc !== '2.0' || !id) return

      console.log(`[Bridge] Request from ${appName}: ${method}`, params)

      // Permission Check
      const allowedMethods = MINI_APP_PERMISSIONS[appName] || []
      if (!allowedMethods.includes(method)) {
        iframeRef.current?.contentWindow.postMessage({
          jsonrpc: '2.0', id, error: { code: -32601, message: 'Permission Denied: Method not allowed' }
        }, '*')
        return
      }

      let result = null
      let error = null

      try {
        switch (method) {
          case 'identity.get':
            result = { user_id: user.user_id, name: user.name, region: user.region, kyc_status: user.kyc_status }
            break
          case 'payment.request':
            // Logic to trigger confirmation modal in shell
            if (onPaymentRequest) {
              result = await onPaymentRequest(params)
            } else {
              error = { code: -32603, message: 'Payment handler not initialized' }
            }
            break
          default:
            error = { code: -32601, message: 'Method not found' }
        }
      } catch (e) {
        error = { code: -32603, message: e.message || 'Internal Bridge Error' }
      }

      iframeRef.current?.contentWindow.postMessage({ jsonrpc: '2.0', id, result, error }, '*')
    }

    window.addEventListener('message', handleMessage)
    return () => window.removeEventListener('message', handleMessage)
  }, [appName, user?.user_id])

  return (
    <div className="w-full max-w-5xl mx-auto premium-glass overflow-hidden shadow-2xl border-white/5 animate-premium-in">
      <div className="bg-white/5 px-6 py-3 border-b border-white/5 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
          <span className="text-[10px] font-black uppercase text-slate-400 tracking-[0.2em]">{appName}</span>
        </div>
        <div className="flex items-center gap-4">
          <div className="text-[9px] text-slate-600 font-bold bg-black/20 px-2 py-1 rounded border border-white/5 uppercase">Secure Sandbox</div>
          <button className="text-slate-500 hover:text-white transition-colors">✕</button>
        </div>
      </div>
      <div className="aspect-video w-full bg-slate-950 relative">
        <iframe 
          ref={iframeRef}
          src={url} 
          className="w-full h-full border-none"
          title={appName}
          sandbox="allow-scripts allow-forms allow-popups allow-same-origin"
        />
      </div>
    </div>
  )
}

/* ── Payment Consent Modal ────────────────────────────────────────────────── */
const PaymentConsentModal = ({ request, onConfirm, onCancel }) => {
  const [processing, setProcessing] = useState(false)
  
  const handleConfirm = async () => {
    setProcessing(true)
    await onConfirm()
    setProcessing(false)
  }

  return (
    <div className="fixed inset-0 bg-black/90 backdrop-blur-xl z-[2000] flex items-center justify-center p-6 animate-premium-in">
      <div className="premium-glass p-10 w-full max-w-lg border-white/5 shadow-[0_0_100px_rgba(79,70,229,0.2)]">
        <div className="text-center mb-10">
          <div className="w-16 h-16 bg-indigo-500/20 rounded-2xl flex items-center justify-center mx-auto mb-6">
            <svg width="32" height="32" fill="none" viewBox="0 0 24 24" stroke="white" strokeWidth="2.5"><path d="M12 1v22m11-18H1m22 14H1" /></svg>
          </div>
          <h2 className="text-3xl font-black text-white mb-2 uppercase tracking-tighter">Authorize Payment</h2>
          <p className="text-slate-500 font-bold uppercase tracking-widest text-[10px]">Requested by <span className="text-indigo-400">{request.appName}</span></p>
        </div>

        <div className="bg-white/5 rounded-3xl p-8 mb-10 border border-white/5">
          <div className="flex justify-between items-baseline mb-2">
            <span className="text-[10px] font-black text-slate-500 uppercase tracking-widest">Transaction Amount</span>
            <span className="text-4xl font-black text-white">{request.amount} <span className="text-xl text-indigo-400">{request.currency}</span></span>
          </div>
          <div className="h-[1px] bg-white/5 my-6" />
          <div className="flex justify-between items-center text-sm">
            <span className="text-slate-400 font-bold">Memo / Description</span>
            <span className="text-white font-medium">{request.memo || 'Mini-App Purchase'}</span>
          </div>
        </div>

        <div className="flex flex-col gap-4">
          <button 
            onClick={handleConfirm}
            disabled={processing}
            className="premium-btn h-16 text-lg font-black bg-indigo-600 hover:bg-indigo-500 shadow-2xl shadow-indigo-500/30"
          >
            {processing ? 'Processing Decentralized Settlement...' : 'Establish Settlement'}
          </button>
          <button 
            onClick={onCancel}
            disabled={processing}
            className="h-14 font-black text-sm text-slate-500 hover:text-white transition-colors uppercase tracking-widest"
          >
            Abort Transaction
          </button>
        </div>
        
        <div className="mt-8 flex items-center justify-center gap-2">
           <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
           <span className="text-[9px] font-black text-slate-600 uppercase tracking-widest">Zero-Knowledge Proof Verified</span>
        </div>
      </div>
    </div>
  )
}

/* ── Main App Shell ─────────────────────────────────────────────────────────── */
function App() {
  const [user, setUser] = useState(null)
  const [token, setToken] = useState(() => localStorage.getItem('token'))
  const [view, setView] = useState('login')
  const [bootstrapping, setBootstrapping] = useState(true)
  const [toast, setToast] = useState(null)
  const [showProfile, setShowProfile] = useState(false)
  const [activePaymentRequest, setActivePaymentRequest] = useState(null)

  const showToast = (msg, type = 'success') => {
    setToast({ msg, type })
    setTimeout(() => setToast(null), 4000)
  }

  useNotifications(user, token, showToast)

  useEffect(() => {
    const storedToken = localStorage.getItem('token')
    if (!storedToken) { setBootstrapping(false); return }
    fetch('/api/me', { headers: { Authorization: `Bearer ${storedToken}` } })
      .then(r => r.ok ? r.json() : null)
      .then(userData => {
        if (userData?.user_id) {
          setUser(userData)
          setToken(storedToken)
          setView('dashboard')
          patchFetch(storedToken)
        } else {
          localStorage.removeItem('token')
          setToken(null)
        }
      })
      .catch(() => { localStorage.removeItem('token'); setToken(null) })
      .finally(() => setBootstrapping(false))
  }, [])

  const patchFetch = (authToken) => {
    const originalFetch = window.__originalFetch || window.fetch
    window.__originalFetch = originalFetch
    window.fetch = async (...args) => {
      let [resource, config] = args
      config = config || {}
      config.headers = config.headers || {}
      if (!config.headers['Authorization']) config.headers['Authorization'] = `Bearer ${authToken}`
      return originalFetch(resource, config)
    }
  }

  const handleLogin = (userData, authToken) => {
    setUser(userData)
    setToken(authToken)
    localStorage.setItem('token', authToken)
    setView('dashboard')
    patchFetch(authToken)
  }

  const handleLogout = () => {
    setUser(null); setToken(null)
    localStorage.removeItem('token')
    if (window.__originalFetch) window.fetch = window.__originalFetch
    window.location.reload()
  }

  const handlePaymentRequest = (appName, params) => {
    return new Promise((resolve) => {
      setActivePaymentRequest({ ...params, appName, resolve })
    })
  }

  const confirmPayment = async () => {
    if (!activePaymentRequest) return
    const { amount, currency, memo, resolve } = activePaymentRequest
    
    try {
      // ── Physical Settlement Call ──
      const r = await fetch('/api/transfer', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
              from_wallet_id: 'default_wallet', // Shell resolves this for the app
              amount,
              memo: `App: ${activePaymentRequest.appName} - ${memo}`
          })
      })
      
      const d = await r.json()
      if (r.ok) {
          showToast(`Paid ${amount} ${currency} to ${activePaymentRequest.appName}`, 'success')
          resolve({ status: 'SUCCESS', transaction_id: d.transaction_id })
      } else {
          showToast(d.detail || 'Payment Failed', 'error')
          resolve({ status: 'FAILED', message: d.detail })
      }
    } catch (e) {
      showToast('Distributed rail unavailable', 'error')
      resolve({ status: 'ERROR', message: e.message })
    } finally {
      setActivePaymentRequest(null)
    }
  }

  if (bootstrapping) return (
    <div className="min-h-screen flex flex-col items-center justify-center gap-6 bg-slate-950">
      <div className="w-12 h-12 rounded-full border-4 border-indigo-500/20 border-t-indigo-500 animate-spin" />
      <p className="text-slate-500 font-black text-xs uppercase tracking-[0.3em]">Synching Quantum State...</p>
    </div>
  )

  const isLoggedIn = !!token && !!user

  return (
    <div className="min-h-screen flex flex-col selection:bg-indigo-500/30">
      <Toast toast={toast} />
      {showProfile && <ProfileModal user={user} onClose={() => setShowProfile(false)} onUpdated={(name) => { setUser(u => ({ ...u, name })); showToast('Identity Updated') }} />}
      {activePaymentRequest && <PaymentConsentModal request={activePaymentRequest} onConfirm={confirmPayment} onCancel={() => { activePaymentRequest.resolve({ status: 'CANCELLED' }); setActivePaymentRequest(null) }} />}

      {/* ── Modern Navigation ─────────────────────────────────────────────────────────── */}
      <nav className="fixed top-0 left-0 right-0 z-[100] px-6 py-4">
        <div className="max-w-7xl mx-auto premium-glass px-6 py-3 flex items-center justify-between border-white/5 shadow-2xl">
          <div className="flex items-center gap-4 group cursor-pointer" onClick={() => setView('dashboard')}>
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-indigo-500 to-violet-600 flex items-center justify-center text-xl shadow-lg shadow-indigo-500/20 group-hover:scale-105 transition-transform">⚡</div>
            <div className="hidden sm:block">
              <div className="font-black text-sm tracking-tight text-premium-gradient">Global Genesis</div>
              <div className="text-[10px] text-slate-500 font-black uppercase tracking-widest -mt-0.5">Financial OS v3</div>
            </div>
          </div>

          <div className="flex items-center gap-3">
            {isLoggedIn && (
              <div className="flex items-center gap-1 bg-white/5 p-1 rounded-xl border border-white/5 mr-2">
                {[
                  { id: 'dashboard', label: 'Wallet' },
                  { id: 'apps', label: 'Ecosystem' },
                  ...(user.is_admin ? [{ id: 'admin', label: 'Admin Shell' }] : []),
                ].map(nav => (
                  <button key={nav.id} onClick={() => setView(nav.id)}
                    className={`px-4 py-2 rounded-lg text-[11px] font-black uppercase tracking-wider transition-all ${view === nav.id ? 'bg-indigo-500 text-white shadow-xl shadow-indigo-500/20' : 'text-slate-500 hover:text-white'}`}>
                    {nav.label}
                  </button>
                ))}
              </div>
            )}

            {isLoggedIn ? (
              <div className="flex items-center gap-4">
                <button onClick={() => setShowProfile(true)} className="flex items-center gap-3 group">
                  <div className="w-9 h-9 rounded-full bg-gradient-to-br from-indigo-500 to-cyan-500 flex items-center justify-center text-xs font-black shadow-lg shadow-indigo-500/10 border-2 border-white/10 group-hover:border-indigo-400 transition-all">
                    {user.name?.charAt(0).toUpperCase()}
                  </div>
                  <div className="hidden md:block text-left">
                    <div className="text-xs font-black text-slate-200">{user.name}</div>
                    <div className="text-[9px] text-slate-500 font-black uppercase tracking-tighter">Verified Node</div>
                  </div>
                </button>
                <div className="h-6 w-[1px] bg-white/10" />
                <button onClick={handleLogout} className="text-slate-500 hover:text-rose-400 transition-colors p-2">
                  <svg width="18" height="18" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2.5"><path strokeLinecap="round" strokeLinejoin="round" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" /></svg>
                </button>
              </div>
            ) : (
              <div className="text-[10px] font-black uppercase tracking-widest text-slate-500">Secure Gateway Shell</div>
            )}
          </div>
        </div>
      </nav>

      {/* ── Main Content Area ─────────────────────────────────────────────────────────── */}
      <main className={`flex-1 flex flex-col items-center w-full max-w-7xl mx-auto pt-32 pb-24 px-6 ${!isLoggedIn ? 'justify-center' : ''}`}>
        {!isLoggedIn ? (
          view === 'signup' ? (
            <div className="w-full max-w-lg space-y-6">
              <div className="text-center mb-10">
                <h1 className="text-5xl font-black text-premium-gradient tracking-tighter mb-4">Create Identity</h1>
                <p className="text-slate-500 font-bold uppercase tracking-widest text-xs">Join the Global Genesis Ecosystem</p>
              </div>
              <div className="premium-glass p-10 border-white/5 shadow-2xl">
                <UserSignup onUserCreated={() => setView('login')} />
                <button onClick={() => setView('login')} className="w-full mt-6 text-indigo-400 font-black text-xs uppercase tracking-widest hover:text-indigo-300 transition-colors">← Establish Secure Sign In</button>
              </div>
            </div>
          ) : (
            <div className="w-full max-w-lg space-y-8">
              <div className="text-center mb-10">
                <h1 className="text-6xl font-black text-premium-gradient tracking-tight mb-4">Secure Shell</h1>
                <p className="text-slate-500 font-bold uppercase tracking-widest text-[10px]">Accessing Genesis Mainframe v3.0</p>
              </div>
              <div className="premium-glass p-10 border-white/5 shadow-2xl relative overflow-hidden">
                <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-indigo-500 via-violet-500 to-indigo-500" />
                <Login onLogin={handleLogin} onSwitchToSignup={() => setView('signup')} />
                <div className="my-10 flex items-center gap-6">
                  <div className="flex-1 h-[1px] bg-white/5" />
                  <span className="text-[10px] font-black text-slate-600 uppercase tracking-[0.3em]">Quantum Auth</span>
                  <div className="flex-1 h-[1px] bg-white/5" />
                </div>
                <PasskeyButton
                  mode="authenticate"
                  email=""
                  onSuccess={({ token: t, user: u }) => handleLogin(u, t)}
                  onError={(e) => console.warn('Passkey failed:', e)}
                />
              </div>
            </div>
          )
        ) : view === 'apps' ? (
          <div className="w-full space-y-12">
            <div className="text-center">
              <h1 className="text-4xl font-black text-premium-gradient tracking-tight mb-2">Mini-App Ecosystem</h1>
              <p className="text-slate-500 font-bold uppercase tracking-widest text-[10px]">Secure sandboxed micro-frontends</p>
            </div>
            <MiniAppView 
              appName="wallet-mfe" 
              url="http://localhost:5001" 
              user={user} 
              onPaymentRequest={(p) => handlePaymentRequest('wallet-mfe', p)}
            />
          </div>
        ) : view === 'admin' ? (
          <div className="w-full animate-premium-in">
            <AdminPanel user={user} />
          </div>
        ) : (
          <div className="w-full animate-premium-in">
            <WalletDashboard user={user} />
          </div>
        )}
      </main>
    </div>
  )
}

export default App
