import React, { useState, useEffect } from 'react';
import Analytics from './Analytics';

const CURRENCY_MAP = { 1: 'USD', 2: 'INR', 3: 'EUR' };
const CURRENCY_SYMBOL = { 1: '$', 2: '₹', 3: '€', USD: '$', INR: '₹', EUR: '€' };
const CURRENCY_FLAG = { 1: '🇺🇸', 2: '🇮🇳', 3: '🇪🇺' };
const ALL_CURRENCIES = [{ id: 1, code: 'USD', flag: '🇺🇸', name: 'US Dollar' }, { id: 2, code: 'INR', flag: '🇮🇳', name: 'Indian Rupee' }, { id: 3, code: 'EUR', flag: '🇪🇺', name: 'Euro' }];

/* ── Inline Styles ──────────────────────────────────────────────────────────── */
const S = `
  @keyframes fadeInUp { from { opacity:0; transform:translateY(14px); } to { opacity:1; transform:translateY(0); } }
  @keyframes spin { to { transform: rotate(360deg); } }
  .wd-tab-active { background:rgba(99,102,241,.15)!important; color:#818cf8!important; border-color:rgba(99,102,241,.3)!important; }
  .wd-tab:hover:not(.wd-tab-active) { background:rgba(255,255,255,.04); color:#f1f5f9; }
  .wd-row:hover { background:rgba(255,255,255,.03); border-radius:10px; }
  .wd-card { background:rgba(255,255,255,.04); border:1px solid rgba(255,255,255,.08); border-radius:14px; padding:20px; transition:all .2s; }
  .wd-card:hover { border-color:rgba(99,102,241,.3); background:rgba(255,255,255,.06); }
  .wd-section { background:rgba(255,255,255,.025); border:1px solid rgba(255,255,255,.06); border-radius:16px; padding:24px; margin-bottom:20px; }
  .wd-input { width:100%; background:rgba(255,255,255,.04); border:1px solid rgba(255,255,255,.08); border-radius:10px; padding:12px 14px; color:#f1f5f9; font-size:14px; font-family:inherit; outline:none; transition:all .2s; box-sizing:border-box; }
  .wd-input:focus { border-color:#6366f1; box-shadow:0 0 0 3px rgba(99,102,241,.15); }
  .wd-input::placeholder { color:#475569; }
  .wd-btn { background:linear-gradient(135deg,#6366f1,#8b5cf6); color:#fff; border:none; border-radius:12px; padding:13px; font-size:15px; font-weight:700; cursor:pointer; width:100%; transition:all .2s; box-shadow:0 4px 24px rgba(99,102,241,.35); }
  .wd-btn:hover { transform:translateY(-1px); box-shadow:0 8px 32px rgba(99,102,241,.55); }
  .wd-btn:disabled { opacity:.5; cursor:not-allowed; transform:none; }
  .wd-btn-green { background:linear-gradient(135deg,#10b981,#06b6d4); box-shadow:0 4px 24px rgba(16,185,129,.3); }
  .wd-btn-green:hover { box-shadow:0 8px 32px rgba(16,185,129,.5); }
  .fx-rate-card { background:rgba(255,255,255,.03); border:1px solid rgba(255,255,255,.06); border-radius:12px; padding:14px 16px; display:flex; align-items:center; justify-content:space-between; transition:all .2s; }
  .fx-rate-card:hover { border-color:rgba(99,102,241,.25); background:rgba(99,102,241,.04); }
`;

const Spinner = ({ size = 16 }) => (
    <span style={{ width: size, height: size, border: '2px solid rgba(255,255,255,0.25)', borderTopColor: 'white', borderRadius: '50%', display: 'inline-block', animation: 'spin .7s linear infinite' }} />
);

const Toast = ({ toast }) => toast ? (
    <div style={{
        position: 'fixed', top: 80, right: 24, zIndex: 999,
        padding: '12px 20px', borderRadius: 12, fontSize: 13, fontWeight: 600,
        background: toast.type === 'success' ? 'rgba(16,185,129,0.95)' : 'rgba(239,68,68,0.95)',
        color: 'white', backdropFilter: 'blur(12px)',
        boxShadow: '0 8px 32px rgba(0,0,0,0.4)',
        animation: 'fadeInUp .3s ease', maxWidth: 320
    }}>{toast.msg}</div>
) : null;

/* ── Main Component ─────────────────────────────────────────────────────────── */
const WalletDashboard = ({ user }) => {
    const [wallet, setWallet] = useState(null);
    const [balance, setBalance] = useState(0);
    const [transactions, setTransactions] = useState([]);
    const [fxRates, setFxRates] = useState(null);
    const [activeTab, setActiveTab] = useState('overview');
    const [loading, setLoading] = useState(false);
    const [toast, setToast] = useState(null);

    // Transfer form
    const [transferType, setTransferType] = useState('phone');
    const [transferData, setTransferData] = useState({ to_phone_number: '', to_wallet_id: '', amount: '' });

    // Convert form
    const [convertData, setConvertData] = useState({ to_currency: 2, amount: '' });
    const [convertResult, setConvertResult] = useState(null);
    const [convertLoading, setConvertLoading] = useState(false);

    const showToast = (msg, type = 'success') => {
        setToast({ msg, type });
        setTimeout(() => setToast(null), 3800);
    };

    // Load wallet
    useEffect(() => {
        if (!user) return;
        fetch('/api/wallets')
            .then(r => r.ok ? r.json() : null)
            .then(data => {
                if (data?.wallets?.length > 0) {
                    setWallet(data.wallets[0]);
                    setBalance(data.wallets[0].balance);
                }
            }).catch(console.error);
    }, [user]);

    // Load FX rates
    useEffect(() => {
        fetch('/api/fx/rates')
            .then(r => r.json())
            .then(data => setFxRates(data.rates))
            .catch(() => { });
    }, []);

    // Load transactions
    const fetchTxns = () => {
        if (!wallet) return;
        fetch(`/api/wallets/${wallet.wallet_id}/transactions`)
            .then(r => r.json())
            .then(d => setTransactions(d.transactions || []))
            .catch(console.error);
    };

    const refreshBalance = () => {
        if (!wallet) return;
        fetch(`/api/wallets/${wallet.wallet_id}/balance`)
            .then(r => r.json())
            .then(d => setBalance(d.balance))
            .catch(console.error);
        fetchTxns();
    };

    useEffect(() => {
        if (wallet) {
            fetchTxns();
            const iv = setInterval(fetchTxns, 10000);
            return () => clearInterval(iv);
        }
    }, [wallet]);

    // Transfer
    const handleTransfer = async (e) => {
        e.preventDefault();
        if (!wallet) return;
        setLoading(true);
        try {
            const payload = {
                from_wallet_id: wallet.wallet_id,
                amount: parseFloat(transferData.amount),
                ...(transferType === 'phone' ? { to_phone_number: transferData.to_phone_number } : { to_wallet_id: transferData.to_wallet_id })
            };
            const res = await fetch('/api/transfer', {
                method: 'POST', headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            const result = await res.json();
            if (result.success) {
                showToast(`✓ Sent! Ref: ···${result.transaction_id?.slice(-8)}`);
                refreshBalance();
                setTransferData({ to_phone_number: '', to_wallet_id: '', amount: '' });
            } else {
                showToast(result.detail || 'Transfer failed', 'error');
            }
        } catch { showToast('Transfer failed. Try again.', 'error'); }
        finally { setLoading(false); }
    };

    // Convert
    const handleConvert = async (e) => {
        e.preventDefault();
        if (!wallet || !convertData.amount) return;
        setConvertLoading(true);
        setConvertResult(null);
        try {
            const res = await fetch('/api/convert', {
                method: 'POST', headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    wallet_id: wallet.wallet_id,
                    to_currency: convertData.to_currency,
                    amount: parseFloat(convertData.amount)
                })
            });
            const data = await res.json();
            if (res.ok) setConvertResult(data);
            else showToast(data.detail || 'Conversion failed', 'error');
        } catch { showToast('Conversion failed', 'error'); }
        finally { setConvertLoading(false); }
    };

    const currencyCode = wallet ? (CURRENCY_MAP[wallet.currency] || 'USD') : 'USD';
    const currencySymbol = wallet ? (CURRENCY_SYMBOL[wallet.currency] || '$') : '$';

    if (!user) return null;
    if (!wallet) return (
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 14, marginTop: 80 }}>
            <style>{S}</style>
            <div style={{ width: 44, height: 44, borderRadius: '50%', border: '3px solid rgba(99,102,241,.2)', borderTopColor: '#6366f1', animation: 'spin .8s linear infinite' }} />
            <p style={{ color: '#94a3b8', fontSize: 14 }}>Loading your wallet...</p>
        </div>
    );

    const tabs = [
        { id: 'overview', icon: '◻', label: 'Overview' },
        { id: 'send', icon: '↑', label: 'Send' },
        { id: 'convert', icon: '⇄', label: 'Convert' },
        { id: 'history', icon: '≡', label: 'History' },
        { id: 'analytics', icon: '∿', label: 'Analytics' },
    ];

    const sentTotal = transactions.filter(t => t.from_wallet_id === wallet.wallet_id).reduce((a, t) => a + t.amount, 0);
    const recvTotal = transactions.filter(t => t.to_wallet_id === wallet.wallet_id).reduce((a, t) => a + t.amount, 0);

    return (
        <div style={{ width: '100%', maxWidth: 880, animation: 'fadeInUp .4s ease' }}>
            <style>{S}</style>
            <Toast toast={toast} />

            {/* ── Hero Balance Card ─────────────────────────────────────────────── */}
            <div style={{
                background: 'linear-gradient(135deg, rgba(99,102,241,.22) 0%, rgba(139,92,246,.16) 50%, rgba(6,182,212,.12) 100%)',
                border: '1px solid rgba(99,102,241,.3)', borderRadius: 22, padding: '28px 32px',
                marginBottom: 20, position: 'relative', overflow: 'hidden'
            }}>
                <div style={{ position: 'absolute', top: -50, right: -50, width: 200, height: 200, borderRadius: '50%', background: 'radial-gradient(circle, rgba(99,102,241,.25), transparent)', pointerEvents: 'none' }} />
                <div style={{ position: 'absolute', bottom: -30, left: -20, width: 120, height: 120, borderRadius: '50%', background: 'radial-gradient(circle, rgba(6,182,212,.15), transparent)', pointerEvents: 'none' }} />

                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: 20 }}>
                    <div>
                        <div style={{ fontSize: 11, fontWeight: 700, color: 'rgba(255,255,255,.45)', letterSpacing: '1.5px', textTransform: 'uppercase', marginBottom: 10 }}>
                            {CURRENCY_FLAG[wallet.currency]} Total Balance
                        </div>
                        <div style={{ fontSize: 48, fontWeight: 900, letterSpacing: '-2.5px', color: 'white', lineHeight: 1 }}>
                            {currencySymbol}{balance.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                        </div>
                        <div style={{ marginTop: 10, fontSize: 12, color: 'rgba(255,255,255,.45)', display: 'flex', alignItems: 'center', gap: 8 }}>
                            <span>{currencyCode} Wallet</span>
                            <span style={{ opacity: .4 }}>·</span>
                            <span style={{ fontFamily: 'monospace', fontSize: 11 }}>···{wallet.wallet_id.slice(-10)}</span>
                        </div>
                    </div>

                    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 10 }}>
                        <div style={{ fontSize: 12, color: 'rgba(255,255,255,.5)', fontWeight: 600 }}>👋 {user?.name}</div>
                        <button onClick={refreshBalance} style={{
                            background: 'rgba(255,255,255,.1)', border: '1px solid rgba(255,255,255,.2)',
                            borderRadius: 8, padding: '7px 16px', color: 'white', fontSize: 12, fontWeight: 600,
                            cursor: 'pointer', transition: 'all .2s'
                        }}
                            onMouseEnter={e => e.target.style.background = 'rgba(255,255,255,.18)'}
                            onMouseLeave={e => e.target.style.background = 'rgba(255,255,255,.1)'}>
                            ↻ Refresh
                        </button>
                        <div style={{ display: 'flex', gap: 6 }}>
                            <span style={{ background: 'rgba(16,185,129,.15)', border: '1px solid rgba(16,185,129,.3)', borderRadius: 8, padding: '4px 10px', fontSize: 10, fontWeight: 700, color: '#10b981' }}>● Live</span>
                            <span style={{ background: 'rgba(99,102,241,.15)', border: '1px solid rgba(99,102,241,.3)', borderRadius: 8, padding: '4px 10px', fontSize: 10, fontWeight: 700, color: '#818cf8' }}>✓ KYC</span>
                        </div>
                    </div>
                </div>
            </div>

            {/* ── Quick Stats ──────────────────────────────────────────────────── */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3,1fr)', gap: 14, marginBottom: 20 }}>
                {[
                    { label: 'Transactions', value: transactions.length, icon: '⇄', color: '#818cf8', bg: 'rgba(129,140,248,.12)' },
                    { label: 'Total Sent', value: `${currencySymbol}${sentTotal.toFixed(0)}`, icon: '↑', color: '#ef4444', bg: 'rgba(239,68,68,.12)' },
                    { label: 'Total Received', value: `${currencySymbol}${recvTotal.toFixed(0)}`, icon: '↓', color: '#10b981', bg: 'rgba(16,185,129,.12)' },
                ].map(s => (
                    <div key={s.label} className="wd-card" style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
                        <div style={{ width: 40, height: 40, borderRadius: 10, background: s.bg, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 18, color: s.color, flexShrink: 0 }}>{s.icon}</div>
                        <div>
                            <div style={{ fontSize: 10, color: '#64748b', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.5px' }}>{s.label}</div>
                            <div style={{ fontSize: 20, fontWeight: 900, color: '#f1f5f9', marginTop: 1 }}>{s.value}</div>
                        </div>
                    </div>
                ))}
            </div>

            {/* ── Tabs ─────────────────────────────────────────────────────────── */}
            <div style={{ display: 'flex', gap: 8, marginBottom: 20, overflowX: 'auto', paddingBottom: 2 }}>
                {tabs.map(t => (
                    <button key={t.id}
                        className={`wd-tab ${activeTab === t.id ? 'wd-tab-active' : ''}`}
                        onClick={() => setActiveTab(t.id)}
                        style={{ background: 'transparent', border: '1px solid rgba(255,255,255,.07)', borderRadius: 10, padding: '9px 18px', color: '#94a3b8', fontSize: 13, fontWeight: 600, cursor: 'pointer', transition: 'all .2s', whiteSpace: 'nowrap' }}>
                        {t.icon} {t.label}
                    </button>
                ))}
            </div>

            {/* ── Tab Content ──────────────────────────────────────────────────── */}
            <div key={activeTab} style={{ animation: 'fadeInUp .25s ease' }}>

                {/* OVERVIEW */}
                {activeTab === 'overview' && (
                    <div>
                        <div className="wd-section">
                            <h3 style={{ fontSize: 15, fontWeight: 700, marginBottom: 16, color: '#f1f5f9' }}>Recent Activity</h3>
                            {transactions.length === 0 ? (
                                <div style={{ textAlign: 'center', padding: '32px 0', color: '#475569', fontSize: 14 }}>
                                    <div style={{ fontSize: 36, marginBottom: 8 }}>📭</div>No transactions yet
                                </div>
                            ) : transactions.slice(0, 5).map(txn => {
                                const isSent = txn.from_wallet_id === wallet.wallet_id;
                                return (
                                    <div key={txn.transaction_id} className="wd-row" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '12px 8px', borderBottom: '1px solid rgba(255,255,255,.04)' }}>
                                        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                                            <div style={{ width: 36, height: 36, borderRadius: 10, background: isSent ? 'rgba(239,68,68,.12)' : 'rgba(16,185,129,.12)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 16 }}>{isSent ? '↑' : '↓'}</div>
                                            <div>
                                                <div style={{ fontSize: 13, fontWeight: 600, color: '#f1f5f9' }}>{isSent ? 'Sent' : 'Received'}</div>
                                                <div style={{ fontSize: 11, color: '#475569', fontFamily: 'monospace' }}>···{(isSent ? txn.to_wallet_id : txn.from_wallet_id)?.slice(-8)}</div>
                                            </div>
                                        </div>
                                        <div style={{ textAlign: 'right' }}>
                                            <div style={{ fontSize: 15, fontWeight: 800, color: isSent ? '#ef4444' : '#10b981' }}>{isSent ? '-' : '+'}{currencySymbol}{txn.amount?.toFixed(2)}</div>
                                            <div style={{ fontSize: 10, color: '#475569' }}>{txn.status}</div>
                                        </div>
                                    </div>
                                );
                            })}
                            {transactions.length > 5 && (
                                <button onClick={() => setActiveTab('history')} style={{ background: 'none', border: 'none', color: '#6366f1', cursor: 'pointer', fontSize: 13, fontWeight: 600, width: '100%', textAlign: 'center', paddingTop: 12 }}>
                                    View all {transactions.length} →
                                </button>
                            )}
                        </div>

                        {/* FX Rates Widget */}
                        {fxRates && (
                            <div className="wd-section">
                                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 14 }}>
                                    <h3 style={{ fontSize: 15, fontWeight: 700, color: '#f1f5f9' }}>Live FX Rates</h3>
                                    <span style={{ fontSize: 11, color: '#475569', background: 'rgba(255,255,255,.04)', padding: '3px 8px', borderRadius: 20 }}>USD Base</span>
                                </div>
                                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
                                    {[['INR', '🇮🇳'], ['EUR', '🇪🇺']].map(([code, flag]) => (
                                        <div key={code} className="fx-rate-card">
                                            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                                                <span style={{ fontSize: 20 }}>{flag}</span>
                                                <div>
                                                    <div style={{ fontSize: 11, color: '#64748b', fontWeight: 600 }}>1 USD</div>
                                                    <div style={{ fontSize: 12, fontWeight: 700, color: '#f1f5f9' }}>{fxRates['USD']?.[code]?.toFixed(4)} {code}</div>
                                                </div>
                                            </div>
                                            <div style={{ fontSize: 11, color: '#475569' }}>
                                                1 {code} = {(1 / fxRates['USD']?.[code]).toFixed(4)} USD
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        )}
                    </div>
                )}

                {/* SEND */}
                {activeTab === 'send' && (
                    <div className="wd-section">
                        <h3 style={{ fontSize: 15, fontWeight: 700, marginBottom: 20, color: '#f1f5f9' }}>Send Money</h3>
                        {/* Toggle */}
                        <div style={{ display: 'flex', gap: 6, marginBottom: 22, background: 'rgba(255,255,255,.03)', padding: 4, borderRadius: 12, border: '1px solid rgba(255,255,255,.06)' }}>
                            {['phone', 'wallet'].map(type => (
                                <button key={type} onClick={() => setTransferType(type)} style={{
                                    flex: 1, padding: '10px', borderRadius: 9, border: 'none', cursor: 'pointer',
                                    fontSize: 13, fontWeight: 600, transition: 'all .2s',
                                    background: transferType === type ? 'rgba(99,102,241,.2)' : 'transparent',
                                    color: transferType === type ? '#818cf8' : '#94a3b8'
                                }}>{type === 'phone' ? '📱 By Phone' : '🔑 By Wallet ID'}</button>
                            ))}
                        </div>
                        <form onSubmit={handleTransfer} style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
                            <div>
                                <label style={{ fontSize: 11, fontWeight: 700, color: '#94a3b8', display: 'block', marginBottom: 6, textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                                    {transferType === 'phone' ? 'Recipient Phone' : 'Recipient Wallet ID'}
                                </label>
                                {transferType === 'phone' ? (
                                    <input className="wd-input" type="tel" placeholder="+1 555 000 0000"
                                        value={transferData.to_phone_number}
                                        onChange={e => setTransferData(d => ({ ...d, to_phone_number: e.target.value }))} required />
                                ) : (
                                    <input className="wd-input" type="text" placeholder="wallet-xxxxxxxx"
                                        value={transferData.to_wallet_id}
                                        onChange={e => setTransferData(d => ({ ...d, to_wallet_id: e.target.value }))} required />
                                )}
                            </div>
                            <div>
                                <label style={{ fontSize: 11, fontWeight: 700, color: '#94a3b8', display: 'block', marginBottom: 6, textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                                    Amount ({currencyCode})
                                </label>
                                <div style={{ position: 'relative' }}>
                                    <span style={{ position: 'absolute', left: 14, top: '50%', transform: 'translateY(-50%)', color: '#475569', fontSize: 16, fontWeight: 700 }}>{currencySymbol}</span>
                                    <input className="wd-input" type="number" placeholder="0.00" step="0.01" min="0.01" style={{ paddingLeft: 30 }}
                                        value={transferData.amount} onChange={e => setTransferData(d => ({ ...d, amount: e.target.value }))} required />
                                </div>
                                <div style={{ fontSize: 11, color: '#475569', marginTop: 6 }}>Available: {currencySymbol}{balance.toFixed(2)}</div>
                            </div>
                            <button type="submit" className="wd-btn" disabled={loading}>
                                {loading ? <span style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8 }}><Spinner />Processing...</span>
                                    : `↑ Send ${transferData.amount ? currencySymbol + parseFloat(transferData.amount || 0).toFixed(2) : 'Money'}`}
                            </button>
                        </form>
                    </div>
                )}

                {/* CONVERT — P-B */}
                {activeTab === 'convert' && (
                    <div>
                        <div className="wd-section">
                            <h3 style={{ fontSize: 15, fontWeight: 700, marginBottom: 20, color: '#f1f5f9' }}>Currency Conversion</h3>

                            <form onSubmit={handleConvert} style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
                                {/* From (read-only — current wallet) */}
                                <div style={{ display: 'grid', gridTemplateColumns: '1fr auto 1fr', alignItems: 'flex-end', gap: 12 }}>
                                    <div>
                                        <label style={{ fontSize: 11, fontWeight: 700, color: '#94a3b8', display: 'block', marginBottom: 6, textTransform: 'uppercase', letterSpacing: '0.5px' }}>From</label>
                                        <div style={{ background: 'rgba(255,255,255,.03)', border: '1px solid rgba(255,255,255,.06)', borderRadius: 10, padding: '12px 14px', display: 'flex', alignItems: 'center', gap: 8 }}>
                                            <span>{CURRENCY_FLAG[wallet.currency]}</span>
                                            <span style={{ fontWeight: 700, color: '#f1f5f9' }}>{currencyCode}</span>
                                            <span style={{ color: '#475569', fontSize: 12, marginLeft: 'auto' }}>your wallet</span>
                                        </div>
                                    </div>
                                    <div style={{ fontSize: 22, textAlign: 'center', paddingBottom: 10, color: '#6366f1' }}>⇄</div>
                                    <div>
                                        <label style={{ fontSize: 11, fontWeight: 700, color: '#94a3b8', display: 'block', marginBottom: 6, textTransform: 'uppercase', letterSpacing: '0.5px' }}>To</label>
                                        <select className="wd-input" value={convertData.to_currency} onChange={e => { setConvertData(d => ({ ...d, to_currency: parseInt(e.target.value) })); setConvertResult(null); }}>
                                            {ALL_CURRENCIES.filter(c => c.id !== wallet.currency).map(c => (
                                                <option key={c.id} value={c.id}>{c.flag} {c.code} — {c.name}</option>
                                            ))}
                                        </select>
                                    </div>
                                </div>

                                <div>
                                    <label style={{ fontSize: 11, fontWeight: 700, color: '#94a3b8', display: 'block', marginBottom: 6, textTransform: 'uppercase', letterSpacing: '0.5px' }}>Amount to Convert</label>
                                    <div style={{ position: 'relative' }}>
                                        <span style={{ position: 'absolute', left: 14, top: '50%', transform: 'translateY(-50%)', color: '#475569', fontSize: 16, fontWeight: 700 }}>{currencySymbol}</span>
                                        <input className="wd-input" type="number" placeholder="0.00" step="0.01" min="0.01" style={{ paddingLeft: 30 }}
                                            value={convertData.amount} onChange={e => { setConvertData(d => ({ ...d, amount: e.target.value })); setConvertResult(null); }} required />
                                    </div>
                                </div>

                                <button type="submit" className="wd-btn wd-btn-green" disabled={convertLoading}>
                                    {convertLoading ? <span style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8 }}><Spinner />Calculating...</span> : '⇄ Get Quote'}
                                </button>
                            </form>

                            {/* Result */}
                            {convertResult && (
                                <div style={{ marginTop: 20, background: 'rgba(16,185,129,.08)', border: '1px solid rgba(16,185,129,.2)', borderRadius: 14, padding: '20px 22px', animation: 'fadeInUp .3s ease' }}>
                                    <div style={{ fontSize: 12, color: '#94a3b8', fontWeight: 600, marginBottom: 12, textTransform: 'uppercase', letterSpacing: '0.5px' }}>Conversion Quote</div>
                                    <div style={{ display: 'flex', alignItems: 'center', gap: 16, flexWrap: 'wrap' }}>
                                        <div>
                                            <div style={{ fontSize: 11, color: '#64748b' }}>You Send</div>
                                            <div style={{ fontSize: 24, fontWeight: 900, color: '#f1f5f9' }}>{currencySymbol}{convertResult.amount_original.toFixed(2)}</div>
                                            <div style={{ fontSize: 11, color: '#64748b' }}>{convertResult.from_currency}</div>
                                        </div>
                                        <div style={{ fontSize: 28, color: '#10b981' }}>→</div>
                                        <div>
                                            <div style={{ fontSize: 11, color: '#64748b' }}>You Receive</div>
                                            <div style={{ fontSize: 28, fontWeight: 900, color: '#10b981' }}>
                                                {CURRENCY_SYMBOL[convertResult.to_currency] || ''}{convertResult.amount_converted.toFixed(4)}
                                            </div>
                                            <div style={{ fontSize: 11, color: '#64748b' }}>{convertResult.to_currency}</div>
                                        </div>
                                    </div>
                                    <div style={{ marginTop: 14, paddingTop: 14, borderTop: '1px solid rgba(255,255,255,.05)', display: 'flex', justifyContent: 'space-between', fontSize: 12, color: '#64748b' }}>
                                        <span>Exchange Rate: 1 {convertResult.from_currency} = {convertResult.rate.toFixed(6)} {convertResult.to_currency}</span>
                                        <span style={{ color: '#475569' }}>Quote only · No funds moved</span>
                                    </div>
                                </div>
                            )}
                        </div>

                        {/* FX Rate Table */}
                        {fxRates && (
                            <div className="wd-section">
                                <h3 style={{ fontSize: 15, fontWeight: 700, marginBottom: 16, color: '#f1f5f9' }}>All Exchange Rates</h3>
                                <div style={{ overflowX: 'auto' }}>
                                    <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
                                        <thead>
                                            <tr style={{ borderBottom: '1px solid rgba(255,255,255,.06)' }}>
                                                <th style={{ textAlign: 'left', padding: '8px 0', color: '#64748b', fontWeight: 600, fontSize: 11, textTransform: 'uppercase' }}>From / To</th>
                                                {Object.keys(fxRates).map(c => <th key={c} style={{ textAlign: 'right', padding: '8px 12px', color: '#64748b', fontWeight: 600, fontSize: 11, textTransform: 'uppercase' }}>{c}</th>)}
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {Object.entries(fxRates).map(([fromC, toMap]) => (
                                                <tr key={fromC} style={{ borderBottom: '1px solid rgba(255,255,255,.04)' }}>
                                                    <td style={{ padding: '10px 0', fontWeight: 700, color: '#f1f5f9' }}>{fromC}</td>
                                                    {Object.entries(toMap).map(([toC, rate]) => (
                                                        <td key={toC} style={{ textAlign: 'right', padding: '10px 12px', color: fromC === toC ? '#475569' : '#94a3b8', fontFamily: 'monospace', fontSize: 12 }}>
                                                            {fromC === toC ? '—' : rate.toFixed(6)}
                                                        </td>
                                                    ))}
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                </div>
                            </div>
                        )}
                    </div>
                )}

                {/* HISTORY */}
                {activeTab === 'history' && (
                    <div className="wd-section">
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
                            <h3 style={{ fontSize: 15, fontWeight: 700, color: '#f1f5f9' }}>Transaction History</h3>
                            <span style={{ fontSize: 12, color: '#475569', background: 'rgba(255,255,255,.05)', padding: '3px 10px', borderRadius: 20 }}>{transactions.length} total</span>
                        </div>
                        {transactions.length === 0 ? (
                            <div style={{ textAlign: 'center', padding: '40px 0', color: '#475569', fontSize: 14 }}>
                                <div style={{ fontSize: 36, marginBottom: 10 }}>📭</div>No transactions yet
                            </div>
                        ) : transactions.map(txn => {
                            const isSent = txn.from_wallet_id === wallet.wallet_id;
                            return (
                                <div key={txn.transaction_id} className="wd-row" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '12px 8px', borderBottom: '1px solid rgba(255,255,255,.04)' }}>
                                    <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                                        <div style={{ width: 38, height: 38, borderRadius: 10, background: isSent ? 'rgba(239,68,68,.12)' : 'rgba(16,185,129,.12)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 16, flexShrink: 0 }}>{isSent ? '↑' : '↓'}</div>
                                        <div>
                                            <div style={{ fontSize: 13, fontWeight: 600, color: '#f1f5f9' }}>{isSent ? 'Sent to' : 'Received from'}</div>
                                            <div style={{ fontSize: 11, color: '#475569', fontFamily: 'monospace' }}>···{(isSent ? txn.to_wallet_id : txn.from_wallet_id)?.slice(-10)}</div>
                                        </div>
                                    </div>
                                    <div style={{ textAlign: 'right' }}>
                                        <div style={{ fontWeight: 800, fontSize: 15, color: isSent ? '#ef4444' : '#10b981' }}>
                                            {isSent ? '-' : '+'}{currencySymbol}{txn.amount?.toFixed(2)}
                                        </div>
                                        <div style={{ fontSize: 10, fontWeight: 700, padding: '2px 7px', borderRadius: 20, display: 'inline-block', marginTop: 2, background: txn.status === 'COMPLETED' ? 'rgba(16,185,129,.12)' : 'rgba(99,102,241,.12)', color: txn.status === 'COMPLETED' ? '#10b981' : '#818cf8' }}>
                                            {txn.status}
                                        </div>
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                )}

                {/* ANALYTICS */}
                {activeTab === 'analytics' && (
                    <div className="wd-section">
                        <h3 style={{ fontSize: 15, fontWeight: 700, marginBottom: 16, color: '#f1f5f9' }}>Analytics</h3>
                        <Analytics transactions={transactions} walletId={wallet.wallet_id} />
                    </div>
                )}
            </div>
        </div>
    );
};

export default WalletDashboard;
