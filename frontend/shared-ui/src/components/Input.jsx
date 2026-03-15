import React, { forwardRef } from 'react';
import { AlertCircle } from 'lucide-react';

const Input = forwardRef(({
    label,
    error,
    icon: Icon,
    className = '',
    id,
    ...props
}, ref) => {
    const inputId = id || label?.toLowerCase().replace(/\s+/g, '-');

    return (
        <div className={`flex flex-col gap-1.5 ${className}`}>
            {label && (
                <label htmlFor={inputId} className="text-sm font-medium text-gray-300">
                    {label}
                </label>
            )}

            <div className="relative">
                {Icon && (
                    <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                        <Icon className="h-5 w-5 text-gray-400" />
                    </div>
                )}

                <input
                    ref={ref}
                    id={inputId}
                    className={`
            w-full bg-gray-900/50 border rounded-xl px-4 py-2.5 
            text-white placeholder-gray-500 focus:outline-none focus:ring-2 
            transition-all duration-200
            ${Icon ? 'pl-10' : ''}
            ${error
                            ? 'border-red-500 focus:ring-red-500/20'
                            : 'border-white/10 focus:border-indigo-500 focus:ring-indigo-500/20'
                        }
          `}
                    {...props}
                />

                {error && (
                    <div className="absolute inset-y-0 right-0 pr-3 flex items-center pointer-events-none">
                        <AlertCircle className="h-5 w-5 text-red-500" />
                    </div>
                )}
            </div>

            {error && (
                <p className="text-sm text-red-500 mt-1 animate-in fade-in slide-in-from-top-1">
                    {error}
                </p>
            )}
        </div>
    );
});

Input.displayName = 'Input';
export default Input;
