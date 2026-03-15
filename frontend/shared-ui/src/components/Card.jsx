import React from 'react';

const Card = ({ children, className = '' }) => {
    return (
        <div className={`bg-gray-800/50 backdrop-blur-xl border border-white/10 rounded-2xl shadow-xl overflow-hidden ${className}`}>
            {children}
        </div>
    );
};

export const CardHeader = ({ children, className = '' }) => (
    <div className={`px-6 py-5 border-b border-white/5 ${className}`}>
        {children}
    </div>
);

export const CardTitle = ({ children, className = '' }) => (
    <h3 className={`text-lg font-medium text-white ${className}`}>
        {children}
    </h3>
);

export const CardContent = ({ children, className = '' }) => (
    <div className={`p-6 ${className}`}>
        {children}
    </div>
);

export default Card;
