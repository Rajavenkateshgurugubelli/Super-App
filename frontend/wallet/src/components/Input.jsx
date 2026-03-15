import React from 'react';

const Input = ({ label, ...props }) => {
    return (
        <div className="space-y-1">
            {label && <label className="text-xs font-bold text-slate-400 uppercase tracking-widest">{label}</label>}
            <input
                className="w-full bg-slate-900/50 border border-white/10 rounded-xl p-3 text-white font-medium outline-none focus:border-indigo-500 transition-colors"
                {...props}
            />
        </div>
    );
};

export default Input;
