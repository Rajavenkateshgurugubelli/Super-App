import React from 'react';

const sizeMap = {
    sm: { outer: 'h-4 w-4', inner: 'h-2.5 w-2.5', border: 'border-2' },
    md: { outer: 'h-8 w-8', inner: 'h-5 w-5', border: 'border-2' },
    lg: { outer: 'h-12 w-12', inner: 'h-7 w-7', border: 'border-[3px]' },
};

const colorMap = {
    indigo: 'border-indigo-500',
    violet: 'border-violet-500',
    cyan: 'border-cyan-500',
    white: 'border-white',
};

/**
 * Spinner — animated loading indicator.
 *
 * @param {string} size    sm | md | lg
 * @param {string} color   indigo | violet | cyan | white
 * @param {string} label   Accessible label (screen readers)
 * @param {string} className
 */
const Spinner = ({
    size = 'md',
    color = 'indigo',
    label = 'Loading…',
    className = '',
}) => {
    const s = sizeMap[size] ?? sizeMap.md;
    const c = colorMap[color] ?? colorMap.indigo;

    return (
        <span
            role="status"
            aria-label={label}
            className={`inline-flex items-center justify-center ${s.outer} ${className}`}
        >
            <span
                className={`
          ${s.inner} rounded-full border-transparent ${s.border} ${c}
          animate-spin border-t-current
        `}
                style={{ borderTopColor: 'currentColor' }}
            />
            <span className="sr-only">{label}</span>
        </span>
    );
};

export default Spinner;
