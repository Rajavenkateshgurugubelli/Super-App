import React, { useState, useEffect } from 'react';

const WalletDashboard = ({ user }) => {
    const [wallets, setWallets] = useState([]);
    const [selectedWallet, setSelectedWallet] = useState(null);
    const [loading, setLoading] = useState(false);
    const [transferData, setTransferData] = useState({ to_wallet_id: '', to_phone_number: '', amount: '', memo: '' });
    const [transferType, setTransferType] = useState('phone');
    const [transactions, setTransactions] = useState([]);
    const [conversions, setConversions] = useState([]);
    const [showQR, setShowQR] = useState(false);
    const [qrPayload, setQrPayload] = useState(null);

    const fetchAllData = async () => {
        if (!user) return;
        try {
            // 1. Fetch all wallets for the user
            const wResp = await fetch('/api/wallets');
            if (!wResp.ok) throw new Error("Failed to fetch wallets");
            const wData = await wResp.json();
            setWallets(wData.wallets || []);
            
            if (wData.wallets?.length > 0 && !selectedWallet) {
                setSelectedWallet(wData.wallets[0]);
            }
        } catch (err) {
            console.error(err);
        }
    };

    const fetchWalletSpecifics = async () => {
        if (!selectedWallet) return;
        try {
            // 2. Fetch specific balance (refreshed from shard)
            const bResp = await fetch(`/api/balance/${selectedWallet.wallet_id}`);
            if (bResp.ok) {
                const bData = await bResp.json();
                setSelectedWallet(prev => prev ? ({ ...prev, balance: bData.balance }) : null);
            }

            // 3. Fetch Transactions
            const tResp = await fetch(`/api/wallets/${selectedWallet.wallet_id}/transactions`);
            if (tResp.ok) {
                const tData = await tResp.json();
                setTransactions(tData.transactions || []);
            }

            // 4. Fetch Conversions
            const cResp = await fetch(`/api/balance/${selectedWallet.wallet_id}/history/conversions`);
            if (cResp.ok) {
                const cData = await cResp.json();
                setConversions(cData.records || []);
            }
        } catch (err) {
            console.error(err);
        }
    };

    useEffect(() => { fetchAllData(); }, [user]);
    useEffect(() => { 
        fetchWalletSpecifics();
        const interval = setInterval(fetchWalletSpecifics, 8000);
        return () => clearInterval(interval);
    }, [selectedWallet?.wallet_id]);

    const handleTransfer = async (e) => {
        e.preventDefault();
        if (!selectedWallet) return;
        setLoading(true);
        try {
            const payload = {
                from_wallet_id: selectedWallet.wallet_id,
                amount: parseFloat(transferData.amount),
                to_wallet_id: transferType === 'wallet' ? transferData.to_wallet_id : undefined,
                to_phone_number: transferType === 'phone' ? transferData.to_phone_number : undefined,
                memo: transferData.memo
            };

            const response = await fetch('/api/transfer', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            
            const result = await response.json();
            if (response.ok) {
                setTransferData({ to_wallet_id: '', to_phone_number: '', amount: '', memo: '' });
                fetchWalletSpecifics();
                alert(`Success: ${result.status}`);
            } else {
                alert(`Failed: ${result.detail || 'Transfer error'}`);
            }
        } catch (err) {
            alert("Network Rail Error");
        } finally {
            setLoading(false);
        }
    };

    const generateQR = async () => {
        if (!selectedWallet) return;
        // Mocking the backend call to generate_cross_border_qr
        const did = `did:superapp:${user.user_id}`;
        const mockQR = {
            ver: "3.0",
            id: user.user_id,
            did: did,
            reg: user.region,
            ts: Date.now(),
            fallbacks: user.region === 1 ? [{ type: 'upi', uri: `upi://pay?pa=${user.user_id}@superapp&cu=INR` }] : []
        };
        setQrPayload(JSON.stringify(mockQR));
        setShowQR(true);
    };

    if (!selectedWallet) return (
        <div className="flex flex-col items-center justify-center p-20 gap-4">
             <div className="w-12 h-12 rounded-full border-4 border-indigo-500/20 border-t-indigo-500 animate-spin" />
             <div className="text-[10px] font-black uppercase text-slate-500 tracking-widest">Resolving Ledger Shards...</div>
        </div>
    );

    return (
        <div className="w-full max-w-6xl mx-auto grid grid-cols-1 lg:grid-cols-12 gap-8 animate-premium-in">
            {/* ── LEFT: Wallet Summary & Multi-Wallet Selector ────────────────── */}
            <div className="lg:col-span-4 space-y-6">
                <div className="premium-glass p-8 relative overflow-hidden group">
                    <div className="absolute top-0 right-0 p-4 opacity-10 group-hover:opacity-20 transition-opacity">
                         <svg width="120" height="120" viewBox="0 0 24 24" fill="white"><path d="M21 18l2 2H1l2-2h18zM12 2l10 10-1.41 1.41L12 4.83 3.41 13.41 2 12 12 2z"/></svg>
                    </div>
                    <div className="relative z-10">
                        <div className="text-[10px] font-black text-slate-500 uppercase tracking-widest mb-1">Active Liquidity</div>
                        <div className="text-5xl font-black text-white mb-2 tracking-tighter">
                            {selectedWallet.balance?.toLocaleString('en-US', { minimumFractionDigits: 2 })}
                            <span className="text-xl text-indigo-400 ml-2">{selectedWallet.currency}</span>
                        </div>
                        <div className="flex items-center gap-2 mb-8">
                             <div className="px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 text-[10px] font-black uppercase">Shard Synced</div>
                             <div className="text-[10px] text-slate-500 font-bold">...{selectedWallet.wallet_id.slice(-8)}</div>
                        </div>

                        <div className="grid grid-cols-2 gap-3">
                            <button onClick={generateQR} className="premium-btn py-4 flex items-center justify-center gap-2 group">
                                <span className="text-lg">📱</span>
                                <span className="text-xs font-black uppercase tracking-widest">Show QR</span>
                            </button>
                            <button className="premium-glass bg-white/5 border-white/5 py-4 flex items-center justify-center gap-2 hover:bg-white/10 transition-all group">
                                <span className="text-lg">📷</span>
                                <span className="text-xs font-black uppercase tracking-widest text-slate-300">Scan</span>
                            </button>
                        </div>
                    </div>
                </div>

                <div className="premium-glass p-6">
                    <h3 className="text-[10px] font-black text-slate-500 uppercase tracking-widest mb-4">Multi-Currency Shards</h3>
                    <div className="space-y-2">
                        {wallets.map(w => (
                            <button 
                                key={w.wallet_id} 
                                onClick={() => setSelectedWallet(w)}
                                className={`w-full flex items-center justify-between p-4 rounded-2xl transition-all border ${selectedWallet.wallet_id === w.wallet_id ? 'bg-indigo-500/20 border-indigo-500/30' : 'bg-white/5 border-transparent hover:border-white/10'}`}
                            >
                                <div className="flex items-center gap-3">
                                    <div className={`w-10 h-10 rounded-xl flex items-center justify-center font-black ${selectedWallet.wallet_id === w.wallet_id ? 'bg-indigo-500 text-white shadow-lg' : 'bg-slate-800 text-slate-400'}`}>
                                        {w.currency.charAt(0)}
                                    </div>
                                    <div className="text-left">
                                        <div className="text-sm font-black text-slate-200">{w.currency} Wallet</div>
                                        <div className="text-[9px] text-slate-500 font-bold uppercase">...{w.wallet_id.slice(-4)}</div>
                                    </div>
                                </div>
                                <div className="text-right">
                                    <div className="text-sm font-black text-white">{w.balance?.toFixed(2)}</div>
                                </div>
                            </button>
                        ))}
                    </div>
                </div>
            </div>

            {/* ── RIGHT: Transfer & Activity ────────────────────────────────── */}
            <div className="lg:col-span-8 space-y-8">
                <div className="premium-glass p-8">
                    <div className="flex items-center justify-between mb-8">
                         <h2 className="text-2xl font-black text-white tracking-tight uppercase tracking-widest">Atomic Transfer</h2>
                         <div className="flex bg-black/20 p-1 rounded-xl border border-white/5">
                             <button onClick={() => setTransferType('phone')} className={`px-4 py-1.5 rounded-lg text-[10px] font-black uppercase tracking-widest transition-all ${transferType === 'phone' ? 'bg-indigo-500 text-white shadow-lg shadow-indigo-500/20' : 'text-slate-500 hover:text-white'}`}>Phone</button>
                             <button onClick={() => setTransferType('wallet')} className={`px-4 py-1.5 rounded-lg text-[10px] font-black uppercase tracking-widest transition-all ${transferType === 'wallet' ? 'bg-indigo-500 text-white shadow-lg shadow-indigo-500/20' : 'text-slate-500 hover:text-white'}`}>Wallet ID</button>
                         </div>
                    </div>

                    <form onSubmit={handleTransfer} className="space-y-6">
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                            <div className="space-y-2">
                                <label className="text-[10px] font-black text-slate-500 uppercase tracking-[0.2em] px-1">Recipient</label>
                                <input 
                                    type={transferType === 'phone' ? 'tel' : 'text'}
                                    placeholder={transferType === 'phone' ? '+91 0000 0000 00' : 'Recipient Public Key'}
                                    className="premium-input h-14 w-full"
                                    value={transferType === 'phone' ? transferData.to_phone_number : transferData.to_wallet_id}
                                    onChange={(e) => setTransferData(prev => ({ ...prev, [transferType === 'phone' ? 'to_phone_number' : 'to_wallet_id']: e.target.value }))}
                                    required
                                />
                            </div>
                            <div className="space-y-2">
                                <label className="text-[10px] font-black text-slate-500 uppercase tracking-[0.2em] px-1">Amount ({selectedWallet.currency})</label>
                                <input 
                                    type="number"
                                    placeholder="0.00"
                                    className="premium-input h-14 w-full font-black text-lg"
                                    value={transferData.amount}
                                    onChange={(e) => setTransferData(prev => ({ ...prev, amount: e.target.value }))}
                                    required
                                />
                            </div>
                        </div>

                        <div className="space-y-2">
                            <label className="text-[10px] font-black text-slate-500 uppercase tracking-[0.2em] px-1">Transaction Memo</label>
                            <input 
                                type="text"
                                placeholder="E.g. Dinner Settlement, Marketplace Purchase"
                                className="premium-input h-14 w-full"
                                value={transferData.memo}
                                onChange={(e) => setTransferData(prev => ({ ...prev, memo: e.target.value }))}
                            />
                        </div>

                        <button 
                            type="submit" 
                            disabled={loading || !transferData.amount}
                            className="premium-btn w-full h-16 text-md font-black shadow-2xl shadow-indigo-500/20 disabled:opacity-20 transition-all hover:scale-[1.01] active:scale-[0.99]"
                        >
                            {loading ? 'Finalizing Distributed Settlement...' : 'Establish Atomic Settlement'}
                        </button>
                    </form>
                </div>

                <div className="premium-glass overflow-hidden">
                    <div className="px-8 py-6 border-b border-white/5 flex items-center justify-between">
                         <h3 className="text-sm font-black text-white uppercase tracking-widest">Unified Audit Trail</h3>
                         <div className="text-[9px] font-black text-slate-500 uppercase">Last 20 Movements</div>
                    </div>
                    {transactions.length === 0 ? (
                        <div className="p-16 text-center text-slate-600 font-bold uppercase text-[10px] tracking-widest">No transaction state found</div>
                    ) : (
                        <div className="overflow-x-auto">
                            <table className="w-full text-left">
                                <thead>
                                    <tr className="bg-white/2 px-8 py-3 text-[10px] font-black text-slate-500 uppercase tracking-widest">
                                        <th className="px-8 py-4">Status</th>
                                        <th className="px-8 py-4">Reference</th>
                                        <th className="px-8 py-4 text-right">Magnitude</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {transactions.map(t => (
                                        <tr key={t.transaction_id} className="border-t border-white/5 hover:bg-white/2 transition-colors">
                                            <td className="px-8 py-5">
                                                <div className="flex items-center gap-2">
                                                     <div className={`w-1.5 h-1.5 rounded-full ${t.status === 'SUCCESS' ? 'bg-emerald-500' : 'bg-rose-500 animate-pulse'}`} />
                                                     <span className={`text-[10px] font-black ${t.status === 'SUCCESS' ? 'text-emerald-500' : 'text-rose-500'}`}>{t.status}</span>
                                                </div>
                                            </td>
                                            <td className="px-8 py-5">
                                                <div className="text-xs font-black text-slate-200">...{t.transaction_id.slice(-8)}</div>
                                                <div className="text-[9px] text-slate-500 font-bold uppercase">{t.from_wallet_id === selectedWallet.wallet_id ? 'OUTBOUND' : 'INBOUND'}</div>
                                            </td>
                                            <td className="px-8 py-5 text-right">
                                                <div className={`text-sm font-black ${t.from_wallet_id === selectedWallet.wallet_id ? 'text-white' : 'text-emerald-400'}`}>
                                                    {t.from_wallet_id === selectedWallet.wallet_id ? '-' : '+'}{t.amount?.toLocaleString()}
                                                </div>
                                                <div className="text-[9px] text-slate-600 font-bold">{new Date(t.timestamp * 1000).toLocaleString()}</div>
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    )}
                </div>
            </div>

            {/* ── QR OVERLAY ──────────────────────────────────────────────────── */}
            {showQR && (
                <div className="fixed inset-0 bg-black/95 backdrop-blur-2xl z-[2000] flex items-center justify-center p-6 animate-premium-in" onClick={() => setShowQR(false)}>
                    <div className="premium-glass p-12 max-w-sm w-full text-center" onClick={e => e.stopPropagation()}>
                        <h3 className="text-xl font-black text-white mb-2 uppercase tracking-tighter">Smart Identity QR</h3>
                        <p className="text-[10px] text-slate-500 font-bold uppercase tracking-widest mb-10">Regional Routing: {user.region === 1 ? 'UPI Enabled' : 'Native Shard'}</p>
                        
                        <div className="bg-white p-6 rounded-3xl mx-auto mb-10 shadow-[0_0_50px_rgba(255,255,255,0.1)]">
                             {/* Mocking QR code rendering */}
                             <div className="aspect-square bg-slate-100 rounded-xl flex items-center justify-center relative overflow-hidden">
                                 <div className="absolute inset-0 bg-gradient-to-br from-indigo-500/10 to-violet-500/10" />
                                 <svg viewBox="0 0 100 100" width="100%" height="100%" className="text-slate-900 p-2">
                                     <rect x="10" y="10" width="20" height="20" fill="currentColor"/>
                                     <rect x="70" y="10" width="20" height="20" fill="currentColor"/>
                                     <rect x="10" y="70" width="20" height="20" fill="currentColor"/>
                                     <rect x="40" y="40" width="20" height="20" fill="currentColor"/>
                                     <path d="M40 10h10v10H40z M60 40h10v10H60z M10 40h10v10H10z M40 70h10v10H40z" fill="currentColor"/>
                                 </svg>
                             </div>
                        </div>

                        <div className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-8">
                             Scanner matches found in: {user.region === 1 ? 'India, EU, US' : 'Native Network'}
                        </div>

                        <button onClick={() => setShowQR(false)} className="w-full premium-btn py-4">Dismiss</button>
                    </div>
                </div>
            )}
        </div>
    );
};

export default WalletDashboard;
