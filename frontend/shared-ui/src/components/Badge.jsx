import React from 'react';

const variantStyles = {
    success: 'bg-emerald-500/15 text-emerald-400 ring-emerald-500/25',
    warning: 'bg-amber-500/15 text-amber-400 ring-amber-500/25',
    error: 'bg-red-500/15 text-red-400 ring-red-500/25',
    info: 'bg-indigo-500/15 text-indigo-400 ring-indigo-500/25',
    neutral: 'bg-gray-500/15 text-gray-300 ring-gray-500/25',
    // Currency variants
    USD: 'bg-emerald-500/15 text-emerald-300 ring-emerald-500/25',
    EUR: 'bg-blue-500/15 text-blue-300 ring-blue-500/25',
    INR: 'bg-orange-500/15 text-orange-300 ring-orange-500/25',
};

const sizeStyles = {
    sm: 'px-1.5 py-0.5 text-xs',
    md: 'px-2.5 py-1 text-xs',
    lg: 'px-3 py-1.5 text-sm',
};

const dotColors = {
    success: 'bg-emerald-400',
    warning: 'bg-amber-400',
    error: 'bg-red-400',
    info: 'bg-indigo-400',
    neutral: 'bg-gray-400',
    USD: 'bg-emerald-400',
    EUR: 'bg-blue-400',
    INR: 'bg-orange-400',
};

/**
 * Badge — status, currency, and label indicator.
 *
 * @param {string}  variant   success | warning | error | info | neutral | USD | EUR | INR
 * @param {string}  size      sm | md | lg
 * @param {boolean} dot       Show pulsing dot indicator
 * @param {string}  className Extra Tailwind classes
 */
const Badge = ({
    children,
    variant = 'neutral',
    size = 'md',
    dot = false,
    className = '',
}) => {
    const vStyle = variantStyles[variant] ?? variantStyles.neutral;
    const sStyle = sizeStyles[size] ?? sizeStyles.md;
    const dColor = dotColors[variant] ?? dotColors.neutral;

    return (
        <span
            className={`
        inline-flex items-center gap-1.5 rounded-full font-medium
        ring-1 ring-inset whitespace-nowrap
        ${vStyle} ${sStyle} ${className}
      `}
        >
            {dot && (
                <span className="relative flex h-2 w-2 shrink-0">
                    <span
                        className={`absolute inline-flex h-full w-full animate-ping rounded-full opacity-75 ${dColor}`}
                    />
                    <span className={`relative inline-flex h-2 w-2 rounded-full ${dColor}`} />
                </span>
            )}
            {children}
        </span>
    );
};

export default Badge;
