import React, { useState, useEffect, useMemo, Suspense } from 'react';
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
    Search,
    ArrowRightLeft
} from 'lucide-react';
import {
    CURRENCIES,
    CURRENCY_BY_ID,
    ALL_CURRENCIES,
    formatMoney,
} from '../payments/config/currencies.js';

/* ── Spinner Utility ────────────────────────────────────────────────────────── */
const Spinner = ({ size = 16 }) => (
    <div className="animate-spin rounded-full border-2 border-indigo-500/20 border-t-indigo-500" style={{ width: size, height: size }} />
);

/* ── Wallet Dashboard ───────────────────────────────────────────────────────── */
const WalletDashboard = ({ user }) => {
    const [wallets, setWallets] = useState([]);
    const [activeWalletIdx, setActiveWalletIdx] = useState(0);
    const [transactions, setTransactions] = useState([]);
    const [fxRates, setFxRates] = useState(null);
    const [activeTab, setActiveTab] = useState('overview');
    const [loading, setLoading] = useState(false);
    const [toast, setToast] = useState(null);

    const wallet = wallets[activeWalletIdx] || null;
    const balance = wallet ? wallet.balance : 0;

    const globalNetWorth = useMemo(() => {
        if (!wallets.length || !fxRates) return 0;
        return wallets.reduce((total, w) => {
            const code = CURRENCY_BY_ID[w.currency]?.code || 'USD';
            const rateToUSD = fxRates[code]?.['USD'] || 1;
            return total + (w.balance * rateToUSD);
        }, 0);
    }, [wallets, fxRates]);

    const [transferData, setTransferData] = useState({ to_phone_number: '', to_wallet_id: '', amount: '' });
    const [convertData, setConvertData] = useState({ to_currency: 2, amount: '' });
    const [convertResult, setConvertResult] = useState(null);
    const [convertLoading, setConvertLoading] = useState(false);

    const showToast = (msg, type = 'success') => {
        setToast({ msg, type });
        setTimeout(() => setToast(null), 3800);
    };

    useEffect(() => {
        if (!user) return;
        fetch('/api/wallets')
            .then(r => r.ok ? r.json() : null)
            .then(data => { if (data?.wallets?.length > 0) setWallets(data.wallets); })
            .catch(console.error);
    }, [user]);

    useEffect(() => {
        fetch('/api/fx/rates')
            .then(r => r.json())
            .then(data => setFxRates(data.rates))
            .catch(() => { });
    }, []);

    const fetchTxns = () => {
        if (!wallet) return;
        fetch(`/api/wallets/${wallet.wallet_id}/transactions`)
            .then(r => r.json())
            .then(d => setTransactions(d.transactions || []))
            .catch(console.error);
    };

    useEffect(() => { if (wallet) fetchTxns(); }, [wallet?.wallet_id]);

    const refreshBalance = async () => {
        setLoading(true);
        try {
            const r = await fetch('/api/wallets');
            if (r.ok) {
                const data = await r.json();
                if (data?.wallets?.length > 0) setWallets(data.wallets);
                showToast('Financial state synchronized');
            }
        } catch (e) { console.error(e); }
        finally { setLoading(false); if (wallet) fetchTxns(); }
    };

    const handleTransfer = async (e) => {
        e.preventDefault();
        if (!wallet) return;
        setLoading(true);
        try {
            const payload = {
                from_wallet_id: wallet.wallet_id,
                amount: parseFloat(transferData.amount),
                to_phone_number: transferData.to_phone_number // Simplified for v3
            };
            const res = await fetch('/api/transfer', {
                method: 'POST', headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            const result = await res.json();
            if (result.success) {
                showToast('Settlement Authorized');
                refreshBalance();
                setTransferData({ to_phone_number: '', to_wallet_id: '', amount: '' });
            } else showToast(result.detail || 'Access Denied', 'error');
        } catch { showToast('Network Error', 'error'); }
        finally { setLoading(false); }
    };

    const handleConvert = async (e) => {
        e.preventDefault();
        if (!wallet || !convertData.amount) return;
        setConvertLoading(true);
        setConvertResult(null);
        try {
            const res = await fetch('/api/convert', {
                method: 'POST', headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ wallet_id: wallet.wallet_id, to_currency: convertData.to_currency, amount: parseFloat(convertData.amount) })
            });
            const data = await res.json();
            if (res.ok) setConvertResult(data);
            else showToast(data.detail || 'FX Node Error', 'error');
        } catch { showToast('Conversion failed', 'error'); }
        finally { setConvertLoading(false); }
    };

    if (!user) return null;
    if (wallets.length === 0) return (
        <div className="flex flex-col items-center justify-center p-20 gap-8 animate-premium-in">
            <Spinner size={48} />
            <div className="text-center">
                <h3 className="text-2xl font-black text-premium-gradient">Allocating Shards</h3>
                <p className="text-slate-500 font-bold uppercase tracking-widest text-[10px] mt-2">Connecting to distributed financial nodes</p>
            </div>
        </div>
    );

    const currencyConfig = wallet ? CURRENCY_BY_ID[wallet.currency] || CURRENCIES.USD : CURRENCIES.USD;
    const currencyCode = currencyConfig.code;

    const tabs = [
        { id: 'overview', icon: <Globe size={18} />, label: 'Market' },
        { id: 'send', icon: <Send size={18} />, label: 'Transfer' },
        { id: 'convert', icon: <RefreshCcw size={18} />, label: 'Swap' },
        { id: 'history', icon: <History size={18} />, label: 'Ledger' },
        { id: 'analytics', icon: <TrendingUp size={18} />, label: 'Insights' },
    ];

    return (
        <div className="w-full space-y-12 animate-premium-in">
            {/* ── Dashboard Header ─────────────────────────────────────────────────────────── */}
            <div className="flex flex-col xl:flex-row xl:items-end justify-between gap-12">
                <div className="space-y-4">
                    <div className="flex items-center gap-3">
                        <div className="px-3 py-1 bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-[10px] font-black uppercase tracking-widest rounded-full">Secure Node</div>
                        <div className="text-slate-600 font-black text-[10px] uppercase tracking-widest">Genesis ID: {user.user_id.substring(0, 8)}</div>
                    </div>
                    <h1 className="text-6xl md:text-8xl font-black tracking-tighter text-white leading-none">
                        Financial <span className="text-accent-gradient">Command</span>
                    </h1>
                </div>

                <div className="flex items-center gap-6">
                    <button onClick={refreshBalance} className="premium-btn px-8 flex items-center gap-3 py-4">
                        {loading ? <RefreshCcw size={18} className="animate-spin" /> : <RefreshCcw size={18} />}
                        Sync Cloud State
                    </button>
                </div>
            </div>

            {/* ── Main Bento Grid ─────────────────────────────────────────────────────────── */}
            <div className="bento-grid">
                {/* Total Liquidity Node */}
                <div className="bento-item-8 premium-glass p-12 relative overflow-hidden group">
                    <div className="absolute top-0 right-0 w-64 h-64 bg-indigo-500/10 blur-[120px] rounded-full -mr-20 -mt-20 group-hover:bg-indigo-500/20 transition-all duration-700" />
                    <div className="relative z-10 space-y-8">
                        <div>
                            <p className="text-[10px] font-black text-slate-500 uppercase tracking-[0.4em] mb-4">Total Aggregated Liquidity</p>
                            <div className="flex items-baseline gap-4">
                                <h2 className="text-7xl md:text-8xl font-black text-white tracking-tighter tabular-nums">
                                    {formatMoney(globalNetWorth, 'USD')}
                                </h2>
                                <span className="text-2xl font-black text-slate-600 uppercase">USD</span>
                            </div>
                        </div>
                        <div className="flex gap-3">
                            {wallets.map((w, idx) => (
                                <button key={w.wallet_id} onClick={() => setActiveWalletIdx(idx)}
                                    className={`px-5 py-3 rounded-2xl text-[10px] font-black uppercase tracking-widest border-2 transition-all ${activeWalletIdx === idx ? 'bg-indigo-500 border-indigo-400 text-white shadow-xl shadow-indigo-500/20' : 'bg-white/5 border-white/5 text-slate-500 hover:border-white/10'}`}>
                                    {CURRENCY_BY_ID[w.currency]?.code} • {formatMoney(w.balance, CURRENCY_BY_ID[w.currency]?.code)}
                                </button>
                            ))}
                        </div>
                    </div>
                </div>

                {/* Shard Status Node */}
                <div className="bento-item-4 premium-glass p-10 flex flex-col border-white/5">
                    <h3 className="text-[10px] font-black text-slate-500 uppercase tracking-widest mb-8">Infrastructure Shards</h3>
                    <div className="space-y-4 flex-1">
                        {[1, 2, 3].map(id => {
                            const names = { 1: 'IN-SHARD-01', 2: 'EU-SHARD-02', 3: 'US-SHARD-03' };
                            const active = wallets.some(w => w.region === id);
                            return (
                                <div key={id} className="p-4 rounded-2xl bg-white/5 border border-white/5 flex items-center justify-between">
                                    <div className="flex items-center gap-4">
                                        <div className={`w-2 h-2 rounded-full ${active ? 'bg-emerald-500 shadow-lg shadow-emerald-500/40 animate-pulse' : 'bg-slate-700'}`} />
                                        <span className="text-xs font-black text-slate-200">{names[id]}</span>
                                    </div>
                                    <span className="text-[9px] font-black text-slate-600 uppercase tracking-widest">{active ? 'Connected' : 'Standby'}</span>
                                </div>
                            );
                        })}
                    </div>
                </div>

                {/* Navigation Hub */}
                <div className="bento-item-12 premium-glass p-3 flex items-center justify-between gap-3 border-indigo-500/10">
                    {tabs.map(tab => (
                        <button key={tab.id} onClick={() => setActiveTab(tab.id)}
                            className={`flex-1 flex items-center justify-center gap-4 py-6 rounded-2xl text-[11px] font-black uppercase tracking-[0.2em] transition-all duration-300 relative overflow-hidden group ${activeTab === tab.id ? 'bg-indigo-600 text-white shadow-2xl shadow-indigo-600/30' : 'text-slate-500 hover:text-white hover:bg-white/5'}`}>
                            {tab.icon}
                            <span className="hidden sm:inline">{tab.label}</span>
                        </button>
                    ))}
                </div>

                {/* Tab Content Node */}
                <div className="bento-item-12 min-h-[500px]">
                    <AnimatePresence mode="wait">
                        <motion.div key={activeTab} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -10 }} className="h-full">
                            {activeTab === 'overview' && (
                                <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 h-full">
                                    <div className="lg:col-span-8 premium-card border-white/5 bg-slate-900/20">
                                        <div className="flex items-center justify-between mb-12">
                                            <h3 className="text-3xl font-black text-white uppercase tracking-tighter">Current Shard</h3>
                                            <div className="text-4xl">{currencyConfig.flag}</div>
                                        </div>
                                        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                                            <div className="p-8 rounded-3xl bg-white/5 border border-white/5 group transition-all hover:bg-indigo-500/5 hover:border-indigo-500/20">
                                                <p className="text-[10px] font-black text-slate-500 uppercase tracking-widest mb-4">Liquidity</p>
                                                <p className="text-5xl font-black text-white group-hover:text-indigo-400 transition-colors">{formatMoney(balance, currencyCode)}</p>
                                            </div>
                                            <div className="p-8 rounded-3xl bg-white/5 border border-white/5">
                                                <p className="text-[10px] font-black text-slate-500 uppercase tracking-widest mb-4">Location</p>
                                                <p className="text-xl font-black text-slate-200">{currencyConfig.region} Primary Node</p>
                                            </div>
                                        </div>
                                    </div>

                                    <div className="lg:col-span-4 premium-card border-white/5">
                                        <h3 className="text-[10px] font-black text-slate-500 uppercase tracking-widest mb-8">Exchange Projections</h3>
                                        <div className="space-y-6">
                                            {fxRates && Object.entries(fxRates).map(([code, rates]) => (
                                                <div key={code} className="flex justify-between items-center group">
                                                    <div className="flex items-center gap-3">
                                                        <span className="text-xs font-black text-slate-400">{code}</span>
                                                    </div>
                                                    <div className="text-right">
                                                        <div className="text-sm font-black text-white tabular-nums group-hover:text-indigo-400 transition-colors">{(rates['USD'] || 1).toFixed(4)}</div>
                                                        <div className="text-[9px] font-black text-slate-600 uppercase tracking-tighter">Relative to USD</div>
                                                    </div>
                                                </div>
                                            ))}
                                        </div>
                                    </div>
                                </div>
                            )}

                            {activeTab === 'send' && (
                                <div className="max-w-4xl mx-auto premium-glass p-12 border-indigo-500/20">
                                    <h3 className="text-4xl font-black text-white uppercase tracking-tighter mb-12 text-center">Liquidity Settlement</h3>
                                    <div className="grid grid-cols-1 md:grid-cols-2 gap-10">
                                        <div className="space-y-4">
                                            <label className="text-[10px] font-black text-slate-500 uppercase tracking-[0.2em] px-1">Recipient Identifier</label>
                                            <input placeholder="Phone Number" value={transferData.to_phone_number} onChange={e => setTransferData(p => ({ ...p, to_phone_number: e.target.value }))} className="premium-input h-16 text-lg font-black" />
                                        </div>
                                        <div className="space-y-4">
                                            <label className="text-[10px] font-black text-slate-500 uppercase tracking-[0.2em] px-1">Allocation ({currencyCode})</label>
                                            <input type="number" placeholder="0.00" value={transferData.amount} onChange={e => setTransferData(p => ({ ...p, amount: e.target.value }))} className="premium-input h-16 text-lg font-black" />
                                        </div>
                                    </div>
                                    <button onClick={handleTransfer} disabled={loading} className="premium-btn w-full h-16 mt-12 text-lg">
                                        {loading ? <Spinner size={24} /> : 'Authorize Settlement'}
                                    </button>
                                </div>
                            )}

                            {activeTab === 'convert' && (
                                <div className="max-w-4xl mx-auto premium-glass p-12 border-emerald-500/20">
                                    <h3 className="text-4xl font-black text-white uppercase tracking-tighter mb-12 text-center">FX Propagation</h3>
                                    <div className="space-y-12">
                                        <div className="flex flex-col md:flex-row items-center gap-8">
                                            <div className="flex-1 w-full p-8 rounded-3xl bg-white/5 border border-white/5 text-center">
                                                <p className="text-[10px] font-black text-slate-500 uppercase mb-4 tracking-widest">From Node</p>
                                                <p className="text-3xl font-black text-white">{currencyCode}</p>
                                            </div>
                                            <div className="w-12 h-12 rounded-full border border-white/10 flex items-center justify-center text-indigo-400 bg-white/5">
                                                <ArrowRightLeft size={20} />
                                            </div>
                                            <div className="flex-1 w-full space-y-4">
                                                <p className="text-[10px] font-black text-slate-500 uppercase mb-4 tracking-widest text-center">To Node</p>
                                                <select value={convertData.to_currency} onChange={e => setConvertData(p => ({ ...p, to_currency: parseInt(e.target.value) }))} className="premium-input h-16 text-xl font-black appearance-none text-center">
                                                    {Object.values(CURRENCY_BY_ID).map(c => c.id !== wallet.currency && <option key={c.id} value={c.id}>{c.code}</option>)}
                                                </select>
                                            </div>
                                        </div>
                                        <div className="space-y-4 max-w-md mx-auto">
                                            <label className="text-[10px] font-black text-slate-500 uppercase tracking-widest text-center block w-full">Input Liquidity</label>
                                            <input type="number" placeholder="0.00" value={convertData.amount} onChange={e => setConvertData(p => ({ ...p, amount: e.target.value }))} className="premium-input h-16 text-center text-3xl font-black" />
                                        </div>
                                        <button onClick={handleConvert} disabled={convertLoading} className="premium-btn w-full h-16 bg-gradient-to-r from-emerald-500 to-cyan-500 shadow-emerald-500/20">
                                            {convertLoading ? 'Calculating Propagation...' : 'Initiate Swap'}
                                        </button>

                                        {convertResult && (
                                            <motion.div initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} className="mt-8 p-10 bg-emerald-500/5 border border-emerald-500/20 rounded-3xl relative overflow-hidden">
                                                <div className="flex items-center justify-between relative z-10">
                                                    <div>
                                                        <p className="text-[10px] font-black text-slate-500 uppercase mb-2">Source Output</p>
                                                        <p className="text-2xl font-black text-white">{formatMoney(convertResult.amount_original, convertResult.from_currency)}</p>
                                                    </div>
                                                    <div className="h-12 w-[1px] bg-white/10" />
                                                    <div className="text-right">
                                                        <p className="text-[10px] font-black text-emerald-400 uppercase mb-2">Target Yield</p>
                                                        <p className="text-4xl font-black text-emerald-400">
                                                            {CURRENCY_BY_ID[convertResult.to_currency]?.symbol}{convertResult.amount_converted.toFixed(2)}
                                                        </p>
                                                    </div>
                                                </div>
                                                <div className="mt-8 pt-8 border-t border-white/5 text-[9px] font-black text-slate-600 uppercase tracking-widest text-center">
                                                    Quantum-Locked Swap Rate: 1 {convertResult.from_currency} = {convertResult.rate.toFixed(6)} {CURRENCY_BY_ID[convertResult.to_currency]?.code}
                                                </div>
                                            </motion.div>
                                        )}
                                    </div>
                                </div>
                            )}

                            {activeTab === 'history' && (
                                <div className="premium-glass p-12 border-white/5 space-y-10">
                                    <h3 className="text-4xl font-black text-white uppercase tracking-tighter">Immutable Ledger</h3>
                                    <div className="space-y-4">
                                        {transactions.length === 0 ? (
                                            <div className="py-32 text-center border-2 border-dashed border-white/5 rounded-3xl opacity-20">Null Dataset</div>
                                        ) : (
                                            transactions.map((tx, i) => {
                                                const isSent = tx.from_wallet_id === wallet.wallet_id;
                                                return (
                                                    <div key={i} className="flex items-center justify-between p-6 rounded-2xl bg-white/5 border border-white/5 hover:bg-white/10 transition-all group">
                                                        <div className="flex items-center gap-6">
                                                            <div className={`p-4 rounded-xl ${isSent ? 'text-rose-400 bg-rose-400/10' : 'text-emerald-400 bg-emerald-400/10'}`}>
                                                                {isSent ? <ArrowUpRight size={24} /> : <ArrowDownLeft size={24} />}
                                                            </div>
                                                            <div>
                                                                <p className="text-sm font-black text-slate-200 uppercase tracking-tight">{isSent ? 'Settlement Out' : 'Settlement In'}</p>
                                                                <p className="text-[10px] font-black text-slate-600 font-mono tracking-widest uppercase mt-1">H: {tx.transaction_id.substring(0, 12)}</p>
                                                            </div>
                                                        </div>
                                                        <p className={`text-2xl font-black tabular-nums ${isSent ? 'text-rose-400' : 'text-emerald-400'}`}>
                                                            {isSent ? '-' : '+'}{formatMoney(tx.amount, currencyCode)}
                                                        </p>
                                                    </div>
                                                );
                                            })
                                        )}
                                    </div>
                                </div>
                            )}

                            {activeTab === 'analytics' && (
                                <div className="h-full">
                                    <Analytics transactions={transactions} walletId={wallet?.wallet_id} />
                                </div>
                            )}
                        </motion.div>
                    </AnimatePresence>
                </div>
            </div>
        </div>
    );
};

export default WalletDashboard;
