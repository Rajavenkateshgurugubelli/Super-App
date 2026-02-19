import React, { useState, useEffect } from 'react';

const WalletDashboard = ({ user }) => {
    const [wallet, setWallet] = useState(null);
    const [balance, setBalance] = useState(0);
    const [loading, setLoading] = useState(false);
    const [transferData, setTransferData] = useState({ to_wallet_id: '', amount: '' });

    // Create Wallet on mount if not exists (Simplified for demo)
    useEffect(() => {
        const createWallet = async () => {
            try {
                const response = await fetch('/api/wallets', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ user_id: user.user_id, currency: 1 }) // Default USD
                });
                const data = await response.json();
                setWallet(data);
                setBalance(data.balance);
            } catch (err) {
                console.error("Failed to fetch/create wallet", err);
            }
        };
        if (user) createWallet();
    }, [user]);

    const refreshBalance = async () => {
        if (!wallet) return;
        const response = await fetch(`/api/wallets/${wallet.wallet_id}`);
        const data = await response.json();
        setBalance(data.balance);
    };

    const handleTransfer = async (e) => {
        e.preventDefault();
        if (!wallet) return;
        setLoading(true);
        try {
            const response = await fetch('/api/transfer', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    from_wallet_id: wallet.wallet_id,
                    to_wallet_id: transferData.to_wallet_id,
                    amount: parseFloat(transferData.amount)
                })
            });
            const result = await response.json();
            if (result.success) {
                alert(`Transfer Successful! Transaction ID: ${result.transaction_id}`);
                refreshBalance();
                setTransferData({ to_wallet_id: '', amount: '' });
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

            <div className="border-t pt-6">
                <h3 className="text-lg font-semibold mb-4">Transfer Funds</h3>
                <form onSubmit={handleTransfer} className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div className="md:col-span-2">
                        <input
                            type="text"
                            placeholder="Recipient Wallet ID"
                            className="w-full rounded-md border border-gray-300 p-2"
                            value={transferData.to_wallet_id}
                            onChange={(e) => setTransferData({ ...transferData, to_wallet_id: e.target.value })}
                            required
                        />
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
                <TransactionHistory walletId={wallet.wallet_id} />
            </div>
        </div>
    );
};

const TransactionHistory = ({ walletId }) => {
    const [transactions, setTransactions] = useState([]);

    useEffect(() => {
        const fetchHistory = async () => {
            try {
                const response = await fetch(`/api/wallets/${walletId}/transactions`);
                const data = await response.json();
                setTransactions(data.transactions || []);
            } catch (err) {
                console.error("Failed to fetch history", err);
            }
        };
        fetchHistory();
        // Poll every 5 seconds for updates
        const interval = setInterval(fetchHistory, 5000);
        return () => clearInterval(interval);
    }, [walletId]);

    if (transactions.length === 0) return <div className="text-gray-500 text-sm">No recent transactions</div>;

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

export default WalletDashboard;
