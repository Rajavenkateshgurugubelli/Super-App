import React, { useState, useEffect } from 'react';

const REGION_MAP = { 0: 'Unspecified', 1: 'India 🇮🇳', 2: 'Europe 🇪🇺', 3: 'USA 🇺🇸' };
const KYC_MAP = { 0: 'Unspecified', 1: 'Pending', 2: 'Verified ✓', 3: 'Failed ✗' };
const KYC_COLOR = { 0: '#475569', 1: '#f59e0b', 2: '#10b981', 3: '#ef4444' };

const S = `
  @keyframes fadeInUp { from{ opacity:0; transform:translateY(12px); } to{ opacity:1; transform:translateY(0); } }
  @keyframes spin { to { transform:rotate(360deg); } }
  .ap-row:hover { background:rgba(255,255,255,.04); }
  .ap-tab-active { background:rgba(99,102,241,.15)!important; color:#818cf8!important; border-color:rgba(99,102,241,.3)!important; }
  .ap-tab:hover:not(.ap-tab-active) { background:rgba(255,255,255,.04); color:#f1f5f9; }
`;

const Spinner = () => (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 12, padding: '48px 0', color: '#94a3b8', fontSize: 14 }}>
        <div style={{ width: 28, height: 28, borderRadius: '50%', border: '3px solid rgba(99,102,241,.2)', borderTopColor: '#6366f1', animation: 'spin .8s linear infinite' }} />
        Loading...
    </div>
);

const StatCard = ({ icon, label, value, sub, color = '#818cf8', bg = 'rgba(99,102,241,.12)' }) => (
    <div style={{ background: 'rgba(255,255,255,.04)', border: '1px solid rgba(255,255,255,.08)', borderRadius: 14, padding: '20px', transition: 'all .2s', cursor: 'default' }}
        onMouseEnter={e => { e.currentTarget.style.borderColor = 'rgba(99,102,241,.3)'; e.currentTarget.style.background = 'rgba(255,255,255,.06)'; }}
        onMouseLeave={e => { e.currentTarget.style.borderColor = 'rgba(255,255,255,.08)'; e.currentTarget.style.background = 'rgba(255,255,255,.04)'; }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 12 }}>
            <div style={{ width: 40, height: 40, borderRadius: 10, background: bg, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 18, color }}>{icon}</div>
            <div style={{ fontSize: 11, fontWeight: 700, color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.5px' }}>{label}</div>
        </div>
        <div style={{ fontSize: 32, fontWeight: 900, color: '#f1f5f9', letterSpacing: '-1px' }}>{value}</div>
        {sub && <div style={{ fontSize: 12, color: '#64748b', marginTop: 4 }}>{sub}</div>}
    </div>
);

const AdminPanel = ({ user }) => {
    const [tab, setTab] = useState('overview');
    const [stats, setStats] = useState(null);
    const [users, setUsers] = useState([]);
    const [transactions, setTransactions] = useState([]);
    const [loading, setLoading] = useState(false);

    const load = async (endpoint) => {
        setLoading(true);
        try {
            const r = await fetch(endpoint);
            return r.ok ? r.json() : null;
        } catch { return null; }
        finally { setLoading(false); }
    };

    useEffect(() => {
        if (tab === 'overview') {
            load('/api/admin/stats').then(d => d && setStats(d));
        } else if (tab === 'users') {
            load('/api/admin/users?limit=100').then(d => d && setUsers(d.users || []));
        } else if (tab === 'transactions') {
            load('/api/admin/transactions?limit=100').then(d => d && setTransactions(d.transactions || []));
        }
    }, [tab]);

    const tabs = [
        { id: 'overview', icon: '◻', label: 'Overview' },
        { id: 'users', icon: '👤', label: 'Users' },
        { id: 'transactions', icon: '⇄', label: 'Transactions' },
    ];

    return (
        <div style={{ width: '100%', maxWidth: 1000, animation: 'fadeInUp .4s ease' }}>
            <style>{S}</style>

            {/* Header */}
            <div style={{
                background: 'linear-gradient(135deg, rgba(239,68,68,.18) 0%, rgba(245,158,11,.12) 100%)',
                border: '1px solid rgba(239,68,68,.25)', borderRadius: 20, padding: '24px 28px',
                marginBottom: 20, display: 'flex', alignItems: 'center', justifyContent: 'space-between'
            }}>
                <div>
                    <div style={{ fontSize: 11, fontWeight: 700, color: 'rgba(255,255,255,.4)', letterSpacing: '1.5px', textTransform: 'uppercase', marginBottom: 6 }}>🔐 Admin Console</div>
                    <div style={{ fontSize: 26, fontWeight: 900, color: 'white', letterSpacing: '-0.5px' }}>Control Center</div>
                    <div style={{ fontSize: 12, color: 'rgba(255,255,255,.45)', marginTop: 4 }}>Signed in as {user.name} · Full system access</div>
                </div>
                <div style={{ display: 'flex', gap: 8 }}>
                    <span style={{ background: 'rgba(239,68,68,.15)', border: '1px solid rgba(239,68,68,.3)', borderRadius: 8, padding: '5px 12px', fontSize: 10, fontWeight: 700, color: '#f87171' }}>⚠ Admin</span>
                    {stats && <span style={{ background: 'rgba(16,185,129,.1)', border: '1px solid rgba(16,185,129,.2)', borderRadius: 8, padding: '5px 12px', fontSize: 10, fontWeight: 700, color: '#10b981' }}>● Live</span>}
                </div>
            </div>

            {/* Tabs */}
            <div style={{ display: 'flex', gap: 8, marginBottom: 20 }}>
                {tabs.map(t => (
                    <button key={t.id} className={`ap-tab ${tab === t.id ? 'ap-tab-active' : ''}`}
                        onClick={() => setTab(t.id)}
                        style={{ background: 'transparent', border: '1px solid rgba(255,255,255,.07)', borderRadius: 10, padding: '9px 20px', color: '#94a3b8', fontSize: 13, fontWeight: 600, cursor: 'pointer', transition: 'all .2s' }}>
                        {t.icon} {t.label}
                    </button>
                ))}
                <button onClick={() => { load('/api/admin/stats').then(d => d && setStats(d)); load(tab === 'users' ? '/api/admin/users?limit=100' : '/api/admin/transactions?limit=100').then(d => { if (d) { if (tab === 'users') setUsers(d.users || []); else setTransactions(d.transactions || []); } }); }}
                    style={{ marginLeft: 'auto', background: 'rgba(255,255,255,.04)', border: '1px solid rgba(255,255,255,.07)', borderRadius: 10, padding: '9px 16px', color: '#94a3b8', fontSize: 13, fontWeight: 600, cursor: 'pointer', transition: 'all .2s' }}>
                    ↻ Refresh
                </button>
            </div>

            {/* OVERVIEW */}
            {tab === 'overview' && (
                loading ? <Spinner /> : stats ? (
                    <div key="overview" style={{ animation: 'fadeInUp .3s ease' }}>
                        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3,1fr)', gap: 14, marginBottom: 20 }}>
                            <StatCard icon="👤" label="Total Users" value={stats.total_users} color="#818cf8" bg="rgba(99,102,241,.12)" />
                            <StatCard icon="💳" label="Total Wallets" value={stats.total_wallets} color="#06b6d4" bg="rgba(6,182,212,.12)" />
                            <StatCard icon="⇄" label="Transactions" value={stats.total_transactions} sub={`${stats.completed_transactions} completed · ${stats.pending_transactions} pending`} color="#10b981" bg="rgba(16,185,129,.12)" />
                        </div>
                        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14 }}>
                            <StatCard icon="💰" label="Total Volume" value={`$${stats.total_volume_usd.toLocaleString('en-US', { minimumFractionDigits: 2 })}`} sub="USD equivalent" color="#f59e0b" bg="rgba(245,158,11,.12)" />
                            <StatCard icon="✓" label="Success Rate" value={stats.total_transactions > 0 ? `${Math.round(stats.completed_transactions / stats.total_transactions * 100)}%` : '—'} sub="of all transactions" color="#10b981" bg="rgba(16,185,129,.12)" />
                        </div>
                    </div>
                ) : <div style={{ textAlign: 'center', padding: '48px', color: '#475569' }}>Could not load stats</div>
            )}

            {/* USERS */}
            {tab === 'users' && (
                <div key="users" style={{ animation: 'fadeInUp .3s ease', background: 'rgba(255,255,255,.025)', border: '1px solid rgba(255,255,255,.06)', borderRadius: 16, padding: 24 }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
                        <h3 style={{ fontSize: 15, fontWeight: 700, color: '#f1f5f9' }}>All Users</h3>
                        <span style={{ fontSize: 12, color: '#475569', background: 'rgba(255,255,255,.05)', padding: '3px 10px', borderRadius: 20 }}>{users.length} users</span>
                    </div>
                    {loading ? <Spinner /> : (
                        <div style={{ overflowX: 'auto' }}>
                            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
                                <thead>
                                    <tr style={{ borderBottom: '1px solid rgba(255,255,255,.06)' }}>
                                        {['Name', 'Email', 'Phone', 'Region', 'KYC', 'Wallets', 'Balance', 'Role'].map(h => (
                                            <th key={h} style={{ textAlign: 'left', padding: '8px 10px', color: '#64748b', fontWeight: 700, fontSize: 10, textTransform: 'uppercase', letterSpacing: '0.5px', whiteSpace: 'nowrap' }}>{h}</th>
                                        ))}
                                    </tr>
                                </thead>
                                <tbody>
                                    {users.map(u => (
                                        <tr key={u.user_id} className="ap-row" style={{ borderBottom: '1px solid rgba(255,255,255,.04)', transition: 'all .15s' }}>
                                            <td style={{ padding: '12px 10px', fontWeight: 600, color: '#f1f5f9', whiteSpace: 'nowrap' }}>
                                                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                                                    <div style={{ width: 28, height: 28, borderRadius: '50%', background: 'linear-gradient(135deg,#6366f1,#8b5cf6)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 12, fontWeight: 700, flexShrink: 0 }}>
                                                        {u.name?.charAt(0).toUpperCase()}
                                                    </div>
                                                    {u.name}
                                                </div>
                                            </td>
                                            <td style={{ padding: '12px 10px', color: '#94a3b8', fontSize: 12 }}>{u.email}</td>
                                            <td style={{ padding: '12px 10px', color: '#94a3b8', fontSize: 12, fontFamily: 'monospace' }}>{u.phone_number || '—'}</td>
                                            <td style={{ padding: '12px 10px', color: '#94a3b8', fontSize: 12 }}>{u.region}</td>
                                            <td style={{ padding: '12px 10px' }}>
                                                <span style={{ fontSize: 11, fontWeight: 700, padding: '3px 8px', borderRadius: 20, background: `${KYC_COLOR[Object.keys(KYC_MAP).find(k => KYC_MAP[k] === u.kyc_status) || 0]}22`, color: KYC_COLOR[Object.keys(KYC_MAP).find(k => KYC_MAP[k] === u.kyc_status) || 0] || '#475569' }}>
                                                    {u.kyc_status}
                                                </span>
                                            </td>
                                            <td style={{ padding: '12px 10px', color: '#94a3b8', textAlign: 'center' }}>{u.wallet_count}</td>
                                            <td style={{ padding: '12px 10px', fontWeight: 700, color: '#10b981' }}>${u.total_balance_usd.toFixed(2)}</td>
                                            <td style={{ padding: '12px 10px' }}>
                                                {u.is_admin ? <span style={{ fontSize: 11, fontWeight: 700, padding: '3px 8px', borderRadius: 20, background: 'rgba(239,68,68,.12)', color: '#f87171' }}>Admin</span>
                                                    : <span style={{ fontSize: 11, color: '#475569' }}>User</span>}
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    )}
                </div>
            )}

            {/* TRANSACTIONS */}
            {tab === 'transactions' && (
                <div key="txns" style={{ animation: 'fadeInUp .3s ease', background: 'rgba(255,255,255,.025)', border: '1px solid rgba(255,255,255,.06)', borderRadius: 16, padding: 24 }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
                        <h3 style={{ fontSize: 15, fontWeight: 700, color: '#f1f5f9' }}>All Transactions</h3>
                        <span style={{ fontSize: 12, color: '#475569', background: 'rgba(255,255,255,.05)', padding: '3px 10px', borderRadius: 20 }}>{transactions.length} records</span>
                    </div>
                    {loading ? <Spinner /> : (
                        <div>
                            {transactions.map(txn => (
                                <div key={txn.transaction_id} className="ap-row" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '12px 8px', borderBottom: '1px solid rgba(255,255,255,.04)', borderRadius: 8, transition: 'all .15s' }}>
                                    <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                                        <div style={{ width: 36, height: 36, borderRadius: 10, background: 'rgba(99,102,241,.12)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 14, color: '#818cf8' }}>⇄</div>
                                        <div>
                                            <div style={{ fontSize: 12, fontFamily: 'monospace', color: '#94a3b8' }}>
                                                ···{txn.from_wallet_id?.slice(-8)} → ···{txn.to_wallet_id?.slice(-8)}
                                            </div>
                                            <div style={{ fontSize: 11, color: '#475569', marginTop: 1 }}>
                                                {txn.timestamp ? new Date(txn.timestamp * 1000).toLocaleString() : '—'}
                                            </div>
                                        </div>
                                    </div>
                                    <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                                        <div style={{ fontWeight: 800, fontSize: 15, color: '#f1f5f9' }}>${txn.amount?.toFixed(2)}</div>
                                        <div style={{ fontSize: 10, fontWeight: 700, padding: '3px 8px', borderRadius: 20, background: txn.status === 'SUCCESS' ? 'rgba(16,185,129,.12)' : 'rgba(245,158,11,.12)', color: txn.status === 'SUCCESS' ? '#10b981' : '#f59e0b' }}>
                                            {txn.status}
                                        </div>
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            )}
        </div>
    );
};

export default AdminPanel;
