import { useState, useEffect, useRef, lazy, Suspense } from 'react'
import UserSignup from './components/UserSignup'
import Login from './components/Login'
import AdminPanel from './components/AdminPanel'
import './index.css'

const WalletDashboard = lazy(() => import('walletApp/WalletDashboard'))

/* ── WebSocket hook ─────────────────────────────────────────────────────────── */
function useNotifications(user, token, showToast) {
  const wsRef = useRef(null)
  const retryRef = useRef(null)

  const connect = () => {
    if (!user || !token) return
    if (wsRef.current?.readyState === WebSocket.OPEN) return

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const host = window.location.host
    const url = `${protocol}//${host}/ws/${user.user_id}?token=${token}`

    try {
      const ws = new WebSocket(url)
      wsRef.current = ws

      ws.onmessage = (e) => {
        try {
          const data = JSON.parse(e.data)
          if (data.event === 'transfer_received') {
            showToast(`💸 Received ${data.amount?.toFixed(2)} ${data.currency}! Check your balance.`, 'success')
          }
        } catch { }
      }

      ws.onerror = () => { }
      ws.onclose = () => {
        wsRef.current = null
        // Reconnect after 5s
        retryRef.current = setTimeout(connect, 5000)
      }
    } catch (e) {
      console.warn('WebSocket failed:', e)
    }
  }

  useEffect(() => {
    if (user && token) {
      setTimeout(connect, 500) // Small delay after login
    }
    return () => {
      clearTimeout(retryRef.current)
      wsRef.current?.close()
    }
  }, [user?.user_id, token])
}

/* ── Global toast state ─────────────────────────────────────────────────────── */
let _globalToast = null
const Toast = ({ toast }) => toast ? (
  <div style={{
    position: 'fixed', top: 80, right: 24, zIndex: 9999,
    padding: '12px 20px', borderRadius: 12, fontSize: 13, fontWeight: 600,
    background: toast.type === 'success' ? 'rgba(16,185,129,0.95)' : 'rgba(239,68,68,0.95)',
    color: 'white', backdropFilter: 'blur(12px)',
    boxShadow: '0 8px 32px rgba(0,0,0,0.45)',
    animation: 'fadeInRight .3s ease', maxWidth: 340, pointerEvents: 'none'
  }}
    style2={{ '@keyframes fadeInRight': 'from{opacity:0;transform:translateX(20px)} to{opacity:1;transform:translateX(0)}' }}>
    <style>{`@keyframes fadeInRight{from{opacity:0;transform:translateX(24px)}to{opacity:1;transform:translateX(0)}}`}</style>
    {toast.msg}
  </div>
) : null

/* ── Profile mini-view (shown as a sheet) ─────────────────────────────────── */
const REGION_NAMES = { 0: 'Unspecified', 1: 'India 🇮🇳', 2: 'Europe 🇪🇺', 3: 'USA 🇺🇸' }
const KYC_COLORS = { 0: '#475569', 1: '#f59e0b', 2: '#10b981', 3: '#ef4444' }
const KYC_NAMES = { 0: 'Unspecified', 1: 'Pending', 2: 'Verified', 3: 'Failed' }

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

  const kycIdx = user.kyc_status || 0
  const kycColor = KYC_COLORS[kycIdx] || '#475569'
  const kycName = KYC_NAMES[kycIdx] || 'Unspecified'

  return (
    <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.65)', backdropFilter: 'blur(8px)', zIndex: 1000, display: 'flex', alignItems: 'center', justifyContent: 'center' }} onClick={onClose}>
      <div onClick={e => e.stopPropagation()} style={{ background: 'rgba(15,20,40,0.98)', border: '1px solid rgba(255,255,255,.1)', borderRadius: 20, padding: '28px 28px', width: '100%', maxWidth: 420, animation: 'fadeInUp .25s ease' }}>
        <style>{`@keyframes fadeInUp{from{opacity:0;transform:translateY(16px)}to{opacity:1;transform:translateY(0)}}`}</style>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 22 }}>
          <h2 style={{ fontSize: 18, fontWeight: 800 }}>Your Profile</h2>
          <button onClick={onClose} style={{ background: 'none', border: 'none', color: '#64748b', fontSize: 20, cursor: 'pointer' }}>✕</button>
        </div>
        {/* Avatar */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 14, marginBottom: 24 }}>
          <div style={{ width: 56, height: 56, borderRadius: '50%', background: 'linear-gradient(135deg,#6366f1,#06b6d4)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 22, fontWeight: 800 }}>
            {user.name?.charAt(0).toUpperCase()}
          </div>
          <div>
            <div style={{ fontWeight: 700, fontSize: 16 }}>{user.name}</div>
            <div style={{ fontSize: 12, color: '#64748b' }}>{user.email}</div>
          </div>
        </div>
        {/* Info rows */}
        {[
          { label: 'Phone', value: user.phone_number || 'Not set' },
          { label: 'Region', value: REGION_NAMES[user.region] || 'Unspecified' },
        ].map(r => (
          <div key={r.label} style={{ display: 'flex', justifyContent: 'space-between', padding: '10px 0', borderBottom: '1px solid rgba(255,255,255,.06)', fontSize: 13 }}>
            <span style={{ color: '#64748b' }}>{r.label}</span>
            <span style={{ fontWeight: 600, color: '#f1f5f9' }}>{r.value}</span>
          </div>
        ))}
        <div style={{ display: 'flex', justifyContent: 'space-between', padding: '10px 0', borderBottom: '1px solid rgba(255,255,255,.06)', fontSize: 13 }}>
          <span style={{ color: '#64748b' }}>KYC Status</span>
          <span style={{ fontWeight: 700, padding: '2px 8px', borderRadius: 20, background: `${kycColor}22`, color: kycColor }}>{kycName}</span>
        </div>
        {user.is_admin && (
          <div style={{ display: 'flex', justifyContent: 'space-between', padding: '10px 0', borderBottom: '1px solid rgba(255,255,255,.06)', fontSize: 13 }}>
            <span style={{ color: '#64748b' }}>Role</span>
            <span style={{ background: 'rgba(239,68,68,.12)', color: '#f87171', fontWeight: 700, padding: '2px 8px', borderRadius: 20, fontSize: 11 }}>🔐 Admin</span>
          </div>
        )}
        {/* Edit name */}
        <div style={{ marginTop: 20 }}>
          <label style={{ fontSize: 11, fontWeight: 700, color: '#94a3b8', display: 'block', marginBottom: 6, textTransform: 'uppercase', letterSpacing: '0.5px' }}>Display Name</label>
          <div style={{ display: 'flex', gap: 8 }}>
            <input value={name} onChange={e => setName(e.target.value)} style={{ flex: 1, background: 'rgba(255,255,255,.04)', border: '1px solid rgba(255,255,255,.08)', borderRadius: 10, padding: '10px 14px', color: '#f1f5f9', fontSize: 13, fontFamily: 'inherit', outline: 'none' }} />
            <button onClick={save} disabled={saving || name === user.name} style={{ background: 'linear-gradient(135deg,#6366f1,#8b5cf6)', color: 'white', border: 'none', borderRadius: 10, padding: '10px 16px', fontSize: 13, fontWeight: 700, cursor: saving ? 'not-allowed' : 'pointer', opacity: saving || name === user.name ? 0.5 : 1 }}>
              {saving ? '…' : 'Save'}
            </button>
          </div>
          {msg && <div style={{ fontSize: 12, marginTop: 8, color: msg.type === 'ok' ? '#10b981' : '#ef4444' }}>{msg.text}</div>}
        </div>
      </div>
    </div>
  )
}

/* ── Main App Shell ─────────────────────────────────────────────────────────── */
function App() {
  const [user, setUser] = useState(null)
  const [token, setToken] = useState(() => localStorage.getItem('token'))
  const [view, setView] = useState('login')     // login | signup | dashboard | admin
  const [bootstrapping, setBootstrapping] = useState(true)
  const [toast, setToast] = useState(null)
  const [showProfile, setShowProfile] = useState(false)
  const [navOpen, setNavOpen] = useState(false)

  const showToast = (msg, type = 'success') => {
    setToast({ msg, type })
    setTimeout(() => setToast(null), 4000)
  }

  // P-E: WebSocket real-time notifications
  useNotifications(user, token, showToast)

  // Session restore on mount
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

  if (bootstrapping) return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 16 }}>
      <div style={{ width: 44, height: 44, borderRadius: '50%', border: '3px solid rgba(99,102,241,0.2)', borderTopColor: '#6366f1', animation: 'spin 0.8s linear infinite' }} />
      <style>{`@keyframes spin{to{transform:rotate(360deg)}} @keyframes fadeInUp{from{opacity:0;transform:translateY(14px)}to{opacity:1;transform:translateY(0)}}`}</style>
      <p style={{ color: '#64748b', fontSize: 14 }}>Restoring session…</p>
    </div>
  )

  const isLoggedIn = !!token && !!user

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      <style>{`@keyframes spin{to{transform:rotate(360deg)}} @keyframes fadeInUp{from{opacity:0;transform:translateY(14px)}to{opacity:1;transform:translateY(0)}}`}</style>
      <Toast toast={toast} />
      {showProfile && <ProfileModal user={user} onClose={() => setShowProfile(false)} onUpdated={(name) => { setUser(u => ({ ...u, name })); showToast('Name updated!') }} />}

      {/* ── Nav ─────────────────────────────────────────────────────────── */}
      <nav style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '14px 28px', borderBottom: '1px solid rgba(255,255,255,0.06)', background: 'rgba(10,15,30,0.88)', backdropFilter: 'blur(20px)', position: 'sticky', top: 0, zIndex: 100 }}>
        {/* Logo */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <div style={{ width: 34, height: 34, borderRadius: 9, background: 'linear-gradient(135deg,#6366f1,#8b5cf6)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 17 }}>⚡</div>
          <div>
            <div style={{ fontWeight: 800, fontSize: 14, letterSpacing: '-0.3px' }}>Global Genesis</div>
            <div style={{ fontSize: 11, color: '#475569', marginTop: -1 }}>Financial OS v3.0</div>
          </div>
        </div>

        {/* Nav links (when logged in) */}
        {isLoggedIn && (
          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            {[
              { id: 'dashboard', label: '◻ Wallet' },
              ...(user.is_admin ? [{ id: 'admin', label: '🔐 Admin' }] : []),
            ].map(nav => (
              <button key={nav.id} onClick={() => setView(nav.id)}
                style={{ background: view === nav.id ? 'rgba(99,102,241,.15)' : 'transparent', border: `1px solid ${view === nav.id ? 'rgba(99,102,241,.3)' : 'rgba(255,255,255,.07)'}`, borderRadius: 9, padding: '7px 14px', color: view === nav.id ? '#818cf8' : '#94a3b8', fontSize: 12, fontWeight: 600, cursor: 'pointer', transition: 'all .2s' }}>
                {nav.label}
              </button>
            ))}
          </div>
        )}

        {/* User chip + logout */}
        {isLoggedIn && (
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <button onClick={() => setShowProfile(true)} style={{ display: 'flex', alignItems: 'center', gap: 8, background: 'rgba(255,255,255,.04)', border: '1px solid rgba(255,255,255,.08)', borderRadius: 30, padding: '5px 12px', cursor: 'pointer', transition: 'all .2s' }}
              onMouseEnter={e => e.currentTarget.style.background = 'rgba(255,255,255,.08)'}
              onMouseLeave={e => e.currentTarget.style.background = 'rgba(255,255,255,.04)'}>
              <div style={{ width: 26, height: 26, borderRadius: '50%', background: 'linear-gradient(135deg,#6366f1,#06b6d4)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 11, fontWeight: 800 }}>
                {user.name?.charAt(0).toUpperCase()}
              </div>
              <div>
                <div style={{ fontSize: 12, fontWeight: 600, color: '#f1f5f9', textAlign: 'left' }}>{user.name}</div>
                <div style={{ fontSize: 10, color: '#475569', marginTop: -1 }}>{user.is_admin ? '🔐 Admin' : user.email?.split('@')[0]}</div>
              </div>
            </button>
            <button onClick={handleLogout} style={{ background: 'rgba(239,68,68,.1)', border: '1px solid rgba(239,68,68,.2)', borderRadius: 8, padding: '6px 12px', color: '#f87171', fontSize: 12, fontWeight: 600, cursor: 'pointer', transition: 'all .2s' }}
              onMouseEnter={e => e.currentTarget.style.background = 'rgba(239,68,68,.2)'}
              onMouseLeave={e => e.currentTarget.style.background = 'rgba(239,68,68,.1)'}>
              Sign Out
            </button>
          </div>
        )}
      </nav>

      {/* ── Main ─────────────────────────────────────────────────────────── */}
      <main style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: !isLoggedIn ? 'center' : 'flex-start', padding: !isLoggedIn ? '40px 16px' : '28px 16px' }}>
        {!isLoggedIn ? (
          view === 'signup' ? (
            <div className="animate-in" style={{ width: '100%', maxWidth: 460 }}>
              <UserSignup onUserCreated={() => setView('login')} />
              <div style={{ textAlign: 'center', marginTop: 16 }}>
                <button onClick={() => setView('login')} style={{ background: 'none', border: 'none', color: '#6366f1', cursor: 'pointer', fontSize: 13 }}>← Back to Sign In</button>
              </div>
            </div>
          ) : (
            <div style={{ width: '100%', maxWidth: 420 }}>
              <Login onLogin={handleLogin} onSwitchToSignup={() => setView('signup')} />
            </div>
          )
        ) : view === 'admin' ? (
          <AdminPanel user={user} />
        ) : (
          <Suspense fallback={
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 14, marginTop: 80 }}>
              <div style={{ width: 44, height: 44, borderRadius: '50%', border: '3px solid rgba(99,102,241,.2)', borderTopColor: '#6366f1', animation: 'spin .8s linear infinite' }} />
              <p style={{ color: '#64748b', fontSize: 14 }}>Loading Wallet…</p>
            </div>
          }>
            <WalletDashboard user={user} />
          </Suspense>
        )}
      </main>
    </div>
  )
}

export default App
