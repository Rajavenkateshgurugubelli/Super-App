import React, { useState, useEffect, useMemo } from 'react';
import Analytics from './Analytics';
import { motion, AnimatePresence } from 'framer-motion';
import {
    Wallet,
    Send,
    RefreshCcw,
    TrendingUp,
    History,
    PieChart as PieChartIcon,
    Globe,
    ShieldCheck,
    ArrowUpRight,
    ArrowDownLeft,
    ChevronRight,
    Search
} from 'lucide-react';
import {
    CURRENCIES,
    CURRENCY_BY_ID,
    ALL_CURRENCIES,
    formatMoney,
} from '../payments/config/currencies.js';

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
    const [wallets, setWallets] = useState([]);
    const [activeWalletIdx, setActiveWalletIdx] = useState(0);
    const [transactions, setTransactions] = useState([]);
    const [fxRates, setFxRates] = useState(null);
    const [activeTab, setActiveTab] = useState('overview');
    const [loading, setLoading] = useState(false);
    const [toast, setToast] = useState(null);

    // Dynamic selection
    const wallet = wallets[activeWalletIdx] || null;
    const balance = wallet ? wallet.balance : 0;

    // Multi-regional aggregation
    const globalNetWorth = useMemo(() => {
        if (!wallets.length || !fxRates) return 0;
        return wallets.reduce((total, w) => {
            const code = CURRENCY_BY_ID[w.currency]?.code || 'USD';
            const rateToUSD = fxRates[code]?.['USD'] || 1;
            return total + (w.balance * rateToUSD);
        }, 0);
    }, [wallets, fxRates]);

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

    // Load wallets
    useEffect(() => {
        if (!user) return;
        fetch('/api/wallets')
            .then(r => r.ok ? r.json() : null)
            .then(data => {
                if (data?.wallets?.length > 0) {
                    setWallets(data.wallets);
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

    const refreshBalance = async () => {
        if (!user) return;
        setLoading(true);
        try {
            const r = await fetch('/api/wallets');
            if (r.ok) {
                const data = await r.json();
                if (data?.wallets?.length > 0) {
                    setWallets(data.wallets);
                    showToast('Balances updated across all regions!', 'success');
                }
            }
        } catch (e) {
            console.error(e);
        } finally {
            setLoading(false);
            fetchTxns();
        }
    };

    useEffect(() => {
        if (wallet) {
            fetchTxns();
        }
    }, [wallet?.wallet_id]);

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

    const currencyConfig = wallet
        ? CURRENCY_BY_ID[wallet.currency] || CURRENCIES.USD
        : CURRENCIES.USD;
    const currencyCode = currencyConfig.code;
    const currencySymbol = currencyConfig.symbol;

    if (!user) return null;
    if (wallets.length === 0) return (
        <div className="flex flex-col items-center justify-center min-h-[60vh] gap-6 animate-in">
            <div className="w-16 h-16 rounded-full border-4 border-indigo-500/20 border-t-indigo-500 animate-spin" />
            <div className="text-center">
                <h3 className="text-xl font-bold glow-text">Initializing Financial Command Center</h3>
                <p className="text-slate-400 mt-2">Aggregating your global footprint...</p>
            </div>
        </div>
    );

    const tabs = [
        { id: 'overview', icon: <Globe size={18} />, label: 'Overview' },
        { id: 'send', icon: <Send size={18} />, label: 'Transfer' },
        { id: 'convert', icon: <RefreshCcw size={18} />, label: 'Convert' },
        { id: 'history', icon: <History size={18} />, label: 'History' },
        { id: 'analytics', icon: <TrendingUp size={18} />, label: 'Insights' },
    ];

    return (
        <div className="w-full max-w-6xl mx-auto space-y-8 pb-20">
            <Toast toast={toast} />

            {/* ── Global Header ─────────────────────────────────────────────────── */}
            <div className="flex flex-col md:flex-row md:items-end justify-between gap-6 px-1">
                <motion.div
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                >
                    <h1 className="text-3xl font-black tracking-tight text-white mb-1">
                        Global <span className="glow-text">Command Center</span>
                    </h1>
                    <p className="text-slate-400 font-medium flex items-center gap-2">
                        <ShieldCheck size={16} className="text-indigo-400" />
                        Cross-Border Sharded Residency: <span className="text-slate-200">Verified</span>
                    </p>
                </motion.div>

                <motion.div
                    initial={{ opacity: 0, x: 20 }}
                    animate={{ opacity: 1, x: 0 }}
                    className="flex items-center gap-3"
                >
                    <button
                        onClick={refreshBalance}
                        className="glass px-4 py-2 text-sm font-semibold text-slate-200 flex items-center gap-2 hover:bg-white/10 transition-colors"
                    >
                        {loading ? <RefreshCcw size={16} className="animate-spin" /> : <RefreshCcw size={16} />}
                        Sync Regions
                    </button>
                    <div className="h-8 w-[1px] bg-white/10 mx-2 hidden md:block" />
                    <div className="flex -space-x-2">
                        {wallets.map((w, idx) => (
                            <div key={w.wallet_id} className={`w-8 h-8 rounded-full border-2 border-slate-900 bg-slate-800 flex items-center justify-center text-xs shadow-lg z-${10 - idx}`}>
                                {CURRENCY_BY_ID[w.currency]?.flag}
                            </div>
                        ))}
                    </div>
                </motion.div>
            </div>

            {/* ── Top Grid: Net Worth + Quick Actions ─────────────────────────── */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                {/* Global Net Worth Card */}
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="lg:col-span-2 glass p-8 relative overflow-hidden group border-indigo-500/20"
                >
                    <div className="absolute -top-24 -right-24 w-64 h-64 bg-indigo-500/10 rounded-full blur-3xl group-hover:bg-indigo-500/20 transition-colors duration-700" />
                    <div className="relative z-10">
                        <div className="flex justify-between items-start mb-8">
                            <div>
                                <p className="text-sm font-bold text-indigo-400 uppercase tracking-widest mb-1">Global Net Worth</p>
                                <h2 className="text-6xl font-black text-white tracking-tighter">
                                    {formatMoney(globalNetWorth, 'USD')}
                                </h2>
                            </div>
                            <div className="bg-emerald-500/10 text-emerald-400 px-3 py-1 rounded-full text-xs font-bold border border-emerald-500/20 flex items-center gap-1">
                                <TrendingUp size={12} /> +2.4%
                            </div>
                        </div>

                        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-12">
                            {wallets.map((w, idx) => (
                                <button
                                    key={w.wallet_id}
                                    onClick={() => setActiveWalletIdx(idx)}
                                    className={`p-4 rounded-xl transition-all duration-300 border-2 text-left ${activeWalletIdx === idx ? 'bg-white/10 border-indigo-500/50 shadow-lg shadow-indigo-500/10' : 'bg-white/5 border-transparent hover:border-white/20'}`}
                                >
                                    <div className="flex items-center justify-between mb-2">
                                        <span className="text-2xl">{CURRENCY_BY_ID[w.currency]?.flag}</span>
                                        {activeWalletIdx === idx && <div className="w-2 h-2 rounded-full bg-indigo-400 animate-pulse" />}
                                    </div>
                                    <p className="text-xs font-bold text-slate-400 truncate">{CURRENCY_BY_ID[w.currency]?.code}</p>
                                    <p className="text-lg font-black text-white">{formatMoney(w.balance, CURRENCY_BY_ID[w.currency]?.code)}</p>
                                </button>
                            ))}
                        </div>
                    </div>
                </motion.div>

                {/* Regional Shard Status */}
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.1 }}
                    className="glass p-8 flex flex-col justify-between"
                >
                    <div>
                        <h3 className="text-lg font-bold text-white mb-6 flex items-center gap-2">
                            <Globe size={20} className="text-indigo-400" /> Regional Shards
                        </h3>
                        <div className="space-y-4">
                            {[1, 2, 3].map(regionId => {
                                const hasData = wallets.some(w => w.region === regionId);
                                return (
                                    <div key={regionId} className="flex items-center justify-between p-3 rounded-lg bg-white/5 border border-white/5">
                                        <div className="flex items-center gap-3">
                                            <div className={`w-2 h-2 rounded-full ${hasData ? 'bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.6)]' : 'bg-slate-600'}`} />
                                            <span className="text-sm font-semibold text-slate-300">
                                                {regionId === 1 ? 'India (IN-SH01)' : regionId === 2 ? 'Europe (EU-SH02)' : 'US East (US-SH03)'}
                                            </span>
                                        </div>
                                        <span className="text-[10px] font-bold text-slate-500 uppercase">
                                            {hasData ? 'Active' : 'Offline'}
                                        </span>
                                    </div>
                                );
                            })}
                        </div>
                    </div>
                    <div className="mt-8 pt-6 border-t border-white/5">
                        <div className="flex items-center justify-between text-xs font-bold text-slate-500 mb-2 uppercase">
                            <span>Security Score</span>
                            <span>98/100</span>
                        </div>
                        <div className="h-2 w-full bg-slate-800 rounded-full overflow-hidden">
                            <motion.div
                                initial={{ width: 0 }}
                                animate={{ width: '98%' }}
                                className="h-full bg-gradient-to-r from-indigo-500 to-purple-500 shadow-[0_0_12px_rgba(99,102,241,0.4)]"
                            />
                        </div>
                    </div>
                </motion.div>
            </div>

            {/* ── Premium Tabbed Navigation ─────────────────────────────────────── */}
            <div className="flex flex-wrap items-center gap-2 p-1 bg-slate-900/50 rounded-2xl border border-white/5">
                {tabs.map(t => (
                    <button
                        key={t.id}
                        onClick={() => setActiveTab(t.id)}
                        className={`flex items-center gap-2 px-6 py-3 rounded-xl transition-all duration-300 font-bold text-sm ${activeTab === t.id ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-600/20 scale-105' : 'text-slate-400 hover:text-slate-200 hover:bg-white/5'}`}
                    >
                        {t.icon}
                        {t.label}
                    </button>
                ))}
            </div>

            {/* ── Content Area ──────────────────────────────────────────────────── */}
            <AnimatePresence mode="wait">
                <motion.div
                    key={activeTab}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -10 }}
                    transition={{ duration: 0.2 }}
                >

                    {/* OVERVIEW */}
                    {activeTab === 'overview' && (
                        <div className="space-y-6">
                            <div className="glass p-6">
                                <h3 className="text-xl font-bold text-white mb-6 flex items-center gap-2">
                                    <History size={20} className="text-indigo-400" /> Recent Transactions
                                </h3>
                                {transactions.length === 0 ? (
                                    <div className="text-center py-12 text-slate-500">
                                        <div className="text-4xl mb-4 opacity-50">📭</div>
                                        <p className="font-semibold">No activity recorded for this wallet</p>
                                    </div>
                                ) : (
                                    <div className="space-y-2">
                                        {transactions.slice(0, 5).map(txn => {
                                            const isSent = txn.from_wallet_id === wallet.wallet_id;
                                            return (
                                                <div key={txn.transaction_id} className="flex items-center justify-between p-4 rounded-xl hover:bg-white/5 transition-colors border border-transparent hover:border-white/5 group">
                                                    <div className="flex items-center gap-4">
                                                        <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${isSent ? 'bg-red-500/10 text-red-400' : 'bg-emerald-500/10 text-emerald-400'}`}>
                                                            {isSent ? <ArrowUpRight size={20} /> : <ArrowDownLeft size={20} />}
                                                        </div>
                                                        <div>
                                                            <p className="font-bold text-white">{isSent ? 'Transfer Sent' : 'Payment Received'}</p>
                                                            <p className="text-xs font-mono text-slate-500">REF: {txn.transaction_id.slice(-12).toUpperCase()}</p>
                                                        </div>
                                                    </div>
                                                    <div className="text-right">
                                                        <p className={`text-lg font-black ${isSent ? 'text-red-400' : 'text-emerald-400'}`}>
                                                            {isSent ? '-' : '+'}{formatMoney(txn.amount, currencyCode)}
                                                        </p>
                                                        <p className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">{txn.status}</p>
                                                    </div>
                                                </div>
                                            );
                                        })}
                                        <button
                                            onClick={() => setActiveTab('history')}
                                            className="w-full mt-4 py-3 text-sm font-bold text-indigo-400 hover:text-indigo-300 transition-colors flex items-center justify-center gap-2"
                                        >
                                            View Complete History <ChevronRight size={16} />
                                        </button>
                                    </div>
                                )}
                            </div>

                            {/* Quick Insights Row */}
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                                <div className="glass p-6 border-emerald-500/10">
                                    <h4 className="text-sm font-bold text-slate-400 uppercase tracking-widest mb-4">Inflow Analytics</h4>
                                    <div className="flex items-end gap-3">
                                        <span className="text-3xl font-black text-white">{formatMoney(transactions.filter(t => t.to_wallet_id === wallet.wallet_id).reduce((a, t) => a + t.amount, 0), currencyCode)}</span>
                                        <span className="text-emerald-400 text-xs font-bold mb-1 flex items-center gap-0.5"><TrendingUp size={12} /> Positive</span>
                                    </div>
                                </div>
                                <div className="glass p-6 border-red-500/10">
                                    <h4 className="text-sm font-bold text-slate-400 uppercase tracking-widest mb-4">Outflow Analytics</h4>
                                    <div className="flex items-end gap-3">
                                        <span className="text-3xl font-black text-white">{formatMoney(transactions.filter(t => t.from_wallet_id === wallet.wallet_id).reduce((a, t) => a + t.amount, 0), currencyCode)}</span>
                                        <span className="text-red-400 text-xs font-bold mb-1 flex items-center gap-0.5">Stable</span>
                                    </div>
                                </div>
                            </div>
                        </div>
                    )}

                    {/* SEND */}
                    {activeTab === 'send' && (
                        <div className="glass p-8 max-w-2xl mx-auto">
                            <h3 className="text-2xl font-black text-white mb-8">Execute Global Transfer</h3>

                            <div className="flex gap-2 p-1 bg-slate-800/50 rounded-xl border border-white/5 mb-8">
                                {['phone', 'wallet'].map(type => (
                                    <button key={type} onClick={() => setTransferType(type)} className={`flex-1 py-3 rounded-lg font-bold text-xs transition-all ${transferType === type ? 'bg-indigo-500 text-white shadow-lg shadow-indigo-500/20' : 'text-slate-500 hover:text-slate-300'}`}>
                                        {type === 'phone' ? '📱 Mobile Number' : '🔑 Wallet Address'}
                                    </button>
                                ))}
                            </div>

                            <form onSubmit={handleTransfer} className="space-y-6">
                                <div className="space-y-2">
                                    <label className="text-xs font-bold text-slate-400 uppercase tracking-widest ml-1">Recipient Identity</label>
                                    <div className="relative group">
                                        <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none text-slate-500 group-focus-within:text-indigo-400 transition-colors">
                                            {transferType === 'phone' ? <Globe size={18} /> : <Search size={18} />}
                                        </div>
                                        <input
                                            className="w-full bg-slate-900/50 border border-white/10 rounded-xl py-4 pl-12 pr-4 text-white font-medium focus:border-indigo-500 focus:ring-4 focus:ring-indigo-500/10 transition-all outline-none"
                                            type={transferType === 'phone' ? 'tel' : 'text'}
                                            placeholder={transferType === 'phone' ? '+1 (555) 000-0000' : 'wallet-address-here'}
                                            value={transferType === 'phone' ? transferData.to_phone_number : transferData.to_wallet_id}
                                            onChange={e => setTransferData(d => ({ ...d, [transferType === 'phone' ? 'to_phone_number' : 'to_wallet_id']: e.target.value }))}
                                            required
                                        />
                                    </div>
                                </div>

                                <div className="space-y-2">
                                    <label className="text-xs font-bold text-slate-400 uppercase tracking-widest ml-1">Amount to Sending ({currencyCode})</label>
                                    <div className="relative group">
                                        <div className="absolute inset-y-0 left-0 pl-5 flex items-center text-2xl font-black text-slate-400 group-focus-within:text-indigo-400 transition-colors">
                                            {currencySymbol}
                                        </div>
                                        <input
                                            className="w-full bg-slate-900/50 border border-white/10 rounded-xl py-6 pl-12 pr-4 text-3xl font-black text-white focus:border-indigo-500 focus:ring-4 focus:ring-indigo-500/10 transition-all outline-none"
                                            type="number" placeholder="0.00" step="0.01" min="0.01"
                                            value={transferData.amount} onChange={e => setTransferData(d => ({ ...d, amount: e.target.value }))}
                                            required
                                        />
                                    </div>
                                    <p className="text-[10px] font-bold text-slate-500 pl-1">
                                        AVAILABLE LIQUIDITY: <span className="text-slate-300">{formatMoney(balance, currencyCode)}</span>
                                    </p>
                                </div>

                                <button type="submit" className="w-full bg-indigo-600 hover:bg-indigo-500 text-white font-black py-5 rounded-xl shadow-xl shadow-indigo-600/20 active:scale-[0.98] transition-all flex items-center justify-center gap-3 disabled:opacity-50" disabled={loading}>
                                    {loading ? <RefreshCcw className="animate-spin" size={24} /> : <><Send size={20} /> Authorize Transaction</>}
                                </button>
                            </form>
                        </div>
                    )}

                    {/* CONVERT */}
                    {activeTab === 'convert' && (
                        <div className="glass p-8 max-w-2xl mx-auto">
                            <h3 className="text-2xl font-black text-white mb-8">Instant FX Liquidity</h3>
                            <form onSubmit={handleConvert} className="space-y-6">
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-6 items-center">
                                    <div className="space-y-2">
                                        <label className="text-xs font-bold text-slate-400 uppercase tracking-widest">Source Asset</label>
                                        <div className="bg-slate-800/50 border border-white/10 rounded-xl p-4 flex items-center gap-3">
                                            <span className="text-2xl">{currencyConfig.flag}</span>
                                            <div>
                                                <p className="font-bold text-white leading-none">{currencyCode}</p>
                                                <p className="text-[10px] text-slate-500 uppercase font-black">Current Wallet</p>
                                            </div>
                                        </div>
                                    </div>
                                    <div className="space-y-2">
                                        <label className="text-xs font-bold text-slate-400 uppercase tracking-widest">Target Asset</label>
                                        <select
                                            className="w-full bg-slate-900/50 border border-white/10 rounded-xl p-4 text-white font-bold outline-none focus:border-indigo-500 appearance-none"
                                            value={convertData.to_currency}
                                            onChange={e => { setConvertData(d => ({ ...d, to_currency: parseInt(e.target.value) })); setConvertResult(null); }}
                                        >
                                            {ALL_CURRENCIES.filter(c => c.id !== wallet.currency).map(c => (
                                                <option key={c.id} value={c.id}>{c.flag} {c.code} — {c.name}</option>
                                            ))}
                                        </select>
                                    </div>
                                </div>

                                <div className="space-y-2">
                                    <label className="text-xs font-bold text-slate-400 uppercase tracking-widest">Liquidating Amount</label>
                                    <div className="relative group">
                                        <div className="absolute inset-y-0 left-0 pl-5 flex items-center text-2xl font-black text-slate-400 focus-within:text-indigo-400">
                                            {currencySymbol}
                                        </div>
                                        <input
                                            className="w-full bg-slate-900/50 border border-white/10 rounded-xl py-6 pl-12 pr-4 text-3xl font-black text-white outline-none"
                                            type="number" placeholder="0.00" step="0.01" min="0.01"
                                            value={convertData.amount} onChange={e => { setConvertData(d => ({ ...d, amount: e.target.value })); setConvertResult(null); }}
                                            required
                                        />
                                    </div>
                                </div>

                                <button type="submit" className="w-full py-5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-black shadow-xl shadow-emerald-500/20 transition-all active:scale-[0.98] disabled:opacity-50" disabled={convertLoading}>
                                    {convertLoading ? <RefreshCcw className="animate-spin" /> : 'Request Quote'}
                                </button>
                            </form>

                            {convertResult && (
                                <motion.div initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} className="mt-8 p-6 bg-emerald-500/10 border border-emerald-500/20 rounded-2xl relative overflow-hidden">
                                    <div className="absolute top-0 right-0 w-32 h-32 bg-emerald-500/10 blur-3xl pointer-events-none" />
                                    <div className="relative z-10">
                                        <p className="text-[10px] font-black text-emerald-400 uppercase tracking-[0.2em] mb-4">Guaranteed Quote</p>
                                        <div className="flex items-center justify-between">
                                            <div>
                                                <p className="text-xs text-slate-500 font-bold mb-1 uppercase">You Convert</p>
                                                <p className="text-2xl font-black text-white">{formatMoney(convertResult.amount_original, convertResult.from_currency)}</p>
                                            </div>
                                            <ChevronRight size={32} className="text-slate-700" />
                                            <div className="text-right">
                                                <p className="text-xs text-slate-500 font-bold mb-1 uppercase">You Receive</p>
                                                <p className="text-3xl font-black text-emerald-400">
                                                    {CURRENCY_BY_ID[convertResult.to_currency]?.symbol || ''}{convertResult.amount_converted.toFixed(2)}
                                                </p>
                                            </div>
                                        </div>
                                        <div className="mt-6 pt-6 border-t border-white/5 flex justify-between text-[10px] font-black text-slate-500 uppercase">
                                            <span>Rate: 1 {convertResult.from_currency} = {convertResult.rate.toFixed(4)} {convertResult.to_currency}</span>
                                            <span>Official Rate Locked</span>
                                        </div>
                                    </div>
                                </motion.div>
                            )}
                        </div>
                    )}

                    {/* HISTORY */}
                    {activeTab === 'history' && (
                        <div className="glass p-8">
                            <div className="flex justify-between items-center mb-8">
                                <h3 className="text-2xl font-black text-white">Transaction Logs</h3>
                                <button className="text-indigo-400 text-xs font-bold uppercase tracking-widest flex items-center gap-1 hover:text-indigo-300">
                                    <Globe size={14} /> Download Ledger
                                </button>
                            </div>
                            {transactions.length === 0 ? (
                                <div className="text-center py-20 opacity-30">
                                    <div className="text-6xl mb-4">🗄️</div>
                                    <p className="font-bold">No historical data available</p>
                                </div>
                            ) : (
                                <div className="overflow-x-auto">
                                    <table className="w-full text-left">
                                        <thead>
                                            <tr className="text-[10px] font-black text-slate-500 uppercase tracking-widest border-b border-white/5 pb-4">
                                                <th className="pb-4 pt-1">Timestamp</th>
                                                <th className="pb-4 pt-1">Activity</th>
                                                <th className="pb-4 pt-1">Status</th>
                                                <th className="pb-4 pt-1 text-right">Volume</th>
                                            </tr>
                                        </thead>
                                        <tbody className="divide-y divide-white/5">
                                            {transactions.map(txn => {
                                                const isSent = txn.from_wallet_id === wallet.wallet_id;
                                                return (
                                                    <tr key={txn.transaction_id} className="group hover:bg-white/[0.02] transition-colors">
                                                        <td className="py-4 text-xs font-bold text-slate-400">
                                                            {new Date(txn.timestamp * 1000).toLocaleDateString()}
                                                        </td>
                                                        <td className="py-4">
                                                            <div className="flex items-center gap-2">
                                                                <div className={`w-1.5 h-1.5 rounded-full ${isSent ? 'bg-red-400' : 'bg-emerald-400'}`} />
                                                                <span className="text-sm font-semibold text-slate-200">{isSent ? 'Outgoing Transfer' : 'Incoming Credit'}</span>
                                                            </div>
                                                        </td>
                                                        <td className="py-4">
                                                            <span className="px-2 py-0.5 rounded-md bg-white/5 text-[10px] font-black text-slate-400 border border-white/5">
                                                                {txn.status}
                                                            </span>
                                                        </td>
                                                        <td className={`py-4 text-right font-black ${isSent ? 'text-red-400' : 'text-emerald-400'}`}>
                                                            {isSent ? '-' : '+'}{formatMoney(txn.amount, currencyCode)}
                                                        </td>
                                                    </tr>
                                                );
                                            })}
                                        </tbody>
                                    </table>
                                </div>
                            )}
                        </div>
                    )}

                    {/* ANALYTICS */}
                    {activeTab === 'analytics' && (
                        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="space-y-6">
                            <Analytics transactions={transactions} walletId={wallet.wallet_id} />
                        </motion.div>
                    )}
                </motion.div>
            </AnimatePresence>
        </div>
    );
};

export default WalletDashboard;
