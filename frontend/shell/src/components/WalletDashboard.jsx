import React, { useState, useEffect } from 'react';
import Analytics from './Analytics';

const WalletDashboard = ({ user }) => {
    const [wallet, setWallet] = useState(null);
    const [balance, setBalance] = useState(0);
    const [loading, setLoading] = useState(false);
    const [transferData, setTransferData] = useState({ to_wallet_id: '', to_phone_number: '', amount: '' });
    const [transferType, setTransferType] = useState('phone'); // 'phone' or 'wallet'

    const [transactions, setTransactions] = useState([]);

    useEffect(() => {
        if (!user) return;
        const fetchWallet = async () => {
            try {
                const response = await fetch('/api/wallets');
                const data = await response.json();
                if (data.wallets && data.wallets.length > 0) {
                    setWallet(data.wallets[0]);
                    setBalance(data.wallets[0].balance);
                }
            } catch (err) {
                console.error("Failed to fetch wallet", err);
            }
        };
        fetchWallet();
    }, [user]);

    const refreshBalance = async () => {
        if (!wallet) return;
        try {
            const response = await fetch(`/api/wallets/${wallet.wallet_id}/balance`);
            const data = await response.json();
            setBalance(data.balance);
            fetchTransactions(); // Also refresh transactions
        } catch (err) {
            console.error("Failed to refresh balance", err);
        }
    };

    const fetchTransactions = async () => {
        if (!wallet) return;
        try {
            const response = await fetch(`/api/wallets/${wallet.wallet_id}/transactions`);
            const data = await response.json();
            setTransactions(data.transactions || []);
        } catch (err) {
            console.error("Failed to fetch history", err);
        }
    };

    useEffect(() => {
        if (wallet) {
            fetchTransactions();
            const interval = setInterval(fetchTransactions, 5000);
            return () => clearInterval(interval);
        }
    }, [wallet]);

    const handleTransfer = async (e) => {
        // ... (existing logic, keep refreshBalance)
        e.preventDefault();
        if (!wallet) return;
        setLoading(true);
        try {
            const payload = {
                from_wallet_id: wallet.wallet_id,
                amount: parseFloat(transferData.amount),
                to_wallet_id: transferType === 'wallet' ? transferData.to_wallet_id : undefined,
                to_phone_number: transferType === 'phone' ? transferData.to_phone_number : undefined
            };

            const response = await fetch('/api/transfer', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            const result = await response.json();
            if (result.success) {
                alert(`Transfer Successful! Transaction ID: ${result.transaction_id}`);
                refreshBalance();
                setTransferData({ to_wallet_id: '', to_phone_number: '', amount: '' });
            } else {
                alert(`Transfer Failed: ${result.message}`);
            }
        } catch (err) {
            alert("Transfer Error");
        } finally {
            setLoading(false);
        }
    };


    if (!user) return null;
    if (!wallet) return <div className="text-center p-4">Loading Wallet...</div>;

    return (
        <div className="bg-white p-6 rounded-xl shadow-lg w-full max-w-2xl mt-6">
            <div className="flex justify-between items-center mb-6">
                <div>
                    <h2 className="text-2xl font-bold text-gray-800">Wallet Dashboard</h2>
                    <p className="text-gray-500">Welcome, {user.name}</p>
                </div>
                <div className="text-right">
                    <div className="text-sm text-gray-500">Current Balance</div>
                    <div className="text-3xl font-bold text-green-600">
                        ${balance.toFixed(2)}
                    </div>
                    <div className="text-xs text-gray-400">Wallet ID: {wallet.wallet_id}</div>
                </div>
            </div>

            <Analytics transactions={transactions} walletId={wallet.wallet_id} />

            <div className="border-t pt-6 mt-6">
                <h3 className="text-lg font-semibold mb-4">Transfer Funds</h3>
                <div className="flex space-x-4 mb-4">
                    <button
                        className={`px-3 py-1 rounded-full text-sm ${transferType === 'phone' ? 'bg-indigo-100 text-indigo-700' : 'text-gray-500'}`}
                        onClick={() => setTransferType('phone')}
                    >
                        By Phone
                    </button>
                    <button
                        className={`px-3 py-1 rounded-full text-sm ${transferType === 'wallet' ? 'bg-indigo-100 text-indigo-700' : 'text-gray-500'}`}
                        onClick={() => setTransferType('wallet')}
                    >
                        By Wallet ID
                    </button>
                </div>
                <form onSubmit={handleTransfer} className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div className="md:col-span-2">
                        {transferType === 'phone' ? (
                            <input
                                type="tel"
                                placeholder="Recipient Phone Number"
                                className="w-full rounded-md border border-gray-300 p-2"
                                value={transferData.to_phone_number}
                                onChange={(e) => setTransferData({ ...transferData, to_phone_number: e.target.value })}
                                required
                            />
                        ) : (
                            <input
                                type="text"
                                placeholder="Recipient Wallet ID"
                                className="w-full rounded-md border border-gray-300 p-2"
                                value={transferData.to_wallet_id}
                                onChange={(e) => setTransferData({ ...transferData, to_wallet_id: e.target.value })}
                                required
                            />
                        )}
                    </div>
                    <div>
                        <input
                            type="number"
                            placeholder="Amount"
                            className="w-full rounded-md border border-gray-300 p-2"
                            value={transferData.amount}
                            onChange={(e) => setTransferData({ ...transferData, amount: e.target.value })}
                            required
                        />
                    </div>
                    <div className="md:col-span-3">
                        <button
                            type="submit"
                            disabled={loading}
                            className="w-full bg-indigo-600 text-white py-2 rounded-md hover:bg-indigo-700 disabled:opacity-50"
                        >
                            {loading ? 'Processing...' : 'Send Money'}
                        </button>
                    </div>
                </form>
            </div>

            <div className="border-t pt-6 mt-6">
                <h3 className="text-lg font-semibold mb-4">Recent Transactions</h3>
                <TransactionHistory transactions={transactions} walletId={wallet.wallet_id} />
            </div>

            <div className="border-t pt-6 mt-6">
                <ConversionHistory walletId={wallet.wallet_id} />
            </div>
        </div >
    );
};

const TransactionHistory = ({ transactions, walletId }) => {
    if (!transactions || transactions.length === 0) return <div className="text-gray-500 text-sm">No recent transactions</div>;

    return (
        <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
                <thead>
                    <tr className="bg-gray-50">
                        <th className="px-4 py-2 text-left">Type</th>
                        <th className="px-4 py-2 text-left">Amount</th>
                        <th className="px-4 py-2 text-left">Status</th>
                    </tr>
                </thead>
                <tbody>
                    {transactions.map((txn) => (
                        <tr key={txn.transaction_id} className="border-b">
                            <td className="px-4 py-2">
                                {txn.from_wallet_id === walletId ?
                                    <span className="text-red-500">Sent to ...{txn.to_wallet_id.slice(-4)}</span> :
                                    <span className="text-green-500">Received from ...{txn.from_wallet_id.slice(-4)}</span>
                                }
                            </td>
                            <td className="px-4 py-2 font-medium">
                                {txn.from_wallet_id === walletId ? '-' : '+'}{txn.amount.toFixed(2)}
                            </td>
                            <td className="px-4 py-2 text-gray-500">{txn.status}</td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    );
};



const ConversionHistory = ({ walletId }) => {
    const [conversions, setConversions] = useState([]);

    useEffect(() => {
        const fetchHistory = async () => {
            try {
                const response = await fetch(`/api/wallets/${walletId}/conversions`);
                if (response.ok) {
                    const data = await response.json();
                    setConversions(data.records || []);
                }
            } catch (err) {
                console.error("Failed to fetch conversion history", err);
            }
        };
        fetchHistory();
        const interval = setInterval(fetchHistory, 10000);
        return () => clearInterval(interval);
    }, [walletId]);

    if (conversions.length === 0) return <div className="text-gray-500 text-sm">No currency conversions recorded</div>;

    return (
        <div className="overflow-x-auto mt-4">
            <h4 className="text-sm font-semibold mb-2 text-gray-600">Currency Conversions</h4>
            <table className="min-w-full text-sm">
                <thead>
                    <tr className="bg-blue-50">
                        <th className="px-4 py-2 text-left">From</th>
                        <th className="px-4 py-2 text-left">To</th>
                        <th className="px-4 py-2 text-left">Rate</th>
                        <th className="px-4 py-2 text-left">Original</th>
                        <th className="px-4 py-2 text-left">Converted</th>
                    </tr>
                </thead>
                <tbody>
                    {conversions.map((rec) => (
                        <tr key={rec.transaction_id} className="border-b">
                            <td className="px-4 py-2">{rec.from_currency}</td>
                            <td className="px-4 py-2">{rec.to_currency}</td>
                            <td className="px-4 py-2 font-mono">{rec.rate.toFixed(4)}</td>
                            <td className="px-4 py-2">{rec.amount_original.toFixed(2)}</td>
                            <td className="px-4 py-2">{rec.amount_converted.toFixed(2)}</td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    );
};

export default WalletDashboard;
