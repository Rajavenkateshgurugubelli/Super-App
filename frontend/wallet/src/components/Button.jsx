import React from 'react';

// Vendored from shared-ui — kept local to avoid cross-package Rollup resolution issues
const Button = ({ children, onClick, variant = 'primary', className = '', ...props }) => {
    const baseStyles = "px-4 py-2 rounded font-semibold transition-colors duration-200 focus:outline-none focus:ring-2 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed";
    const variants = {
        primary: "bg-blue-600 text-white hover:bg-blue-700 focus:ring-blue-500",
        secondary: "bg-gray-200 text-gray-800 hover:bg-gray-300 focus:ring-gray-500",
        danger: "bg-red-600 text-white hover:bg-red-700 focus:ring-red-500",
    };

    return (
        <button
            onClick={onClick}
            className={`${baseStyles} ${variants[variant] || ''} ${className}`}
            {...props}
        >
            {children}
        </button>
    );
};

export default Button;
