import React, { useMemo } from 'react';
import {
    LineChart,
    Line,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    ResponsiveContainer,
    BarChart,
    Bar,
    Legend
} from 'recharts';
import { motion } from 'framer-motion';

const Analytics = ({ transactions, walletId }) => {
    const data = useMemo(() => {
        if (!transactions || transactions.length === 0) return [];

        // Sort transactions by time ascending for chart
        const sorted = [...transactions].sort((a, b) => a.timestamp - b.timestamp);

        // Calculate running balance or daily totals
        // Let's do daily In/Out for simplicity
        const dailyData = {};

        sorted.forEach(txn => {
            const date = new Date(txn.timestamp * 1000).toLocaleDateString();
            if (!dailyData[date]) {
                dailyData[date] = { date, income: 0, expense: 0, net: 0 };
            }

            if (txn.to_wallet_id === walletId) {
                dailyData[date].income += txn.amount;
                dailyData[date].net += txn.amount;
            } else {
                dailyData[date].expense += txn.amount;
                dailyData[date].net -= txn.amount;
            }
        });

        return Object.values(dailyData);
    }, [transactions, walletId]);

    if (transactions.length === 0) {
        return (
            <div className="p-6 bg-white rounded-xl shadow-md text-center text-gray-400">
                No data for analytics yet.
            </div>
        );
    }

    return (
        <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
            className="bg-white p-6 rounded-xl shadow-lg mt-6"
        >
            <h3 className="text-xl font-bold text-gray-800 mb-6 flex items-center gap-2">
                📊 Financial Insights
            </h3>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                <div className="h-64">
                    <h4 className="text-sm font-semibold text-gray-500 mb-4">Daily Activity</h4>
                    <ResponsiveContainer width="100%" height="100%">
                        <BarChart data={data}>
                            <CartesianGrid strokeDasharray="3 3" vertical={false} />
                            <XAxis dataKey="date" fontSize={12} tickLine={false} axisLine={false} />
                            <YAxis fontSize={12} tickLine={false} axisLine={false} tickFormatter={(value) => `$${value}`} />
                            <Tooltip
                                contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}
                                cursor={{ fill: '#f3f4f6' }}
                            />
                            <Legend />
                            <Bar dataKey="income" name="Received" fill="#10B981" radius={[4, 4, 0, 0]} />
                            <Bar dataKey="expense" name="Sent" fill="#EF4444" radius={[4, 4, 0, 0]} />
                        </BarChart>
                    </ResponsiveContainer>
                </div>

                <div className="h-64">
                    <h4 className="text-sm font-semibold text-gray-500 mb-4">Net Cash Flow Trend</h4>
                    <ResponsiveContainer width="100%" height="100%">
                        <LineChart data={data}>
                            <CartesianGrid strokeDasharray="3 3" vertical={false} />
                            <XAxis dataKey="date" fontSize={12} tickLine={false} axisLine={false} />
                            <YAxis fontSize={12} tickLine={false} axisLine={false} />
                            <Tooltip
                                contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}
                            />
                            <Line
                                type="monotone"
                                dataKey="net"
                                name="Net Change"
                                stroke="#6366f1"
                                strokeWidth={3}
                                dot={{ r: 4, fill: '#6366f1', strokeWidth: 2, stroke: '#fff' }}
                                activeDot={{ r: 6 }}
                            />
                        </LineChart>
                    </ResponsiveContainer>
                </div>
            </div>
        </motion.div>
    );
};

export default Analytics;
