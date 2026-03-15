import React, { useEffect, useCallback } from 'react';
import { CheckCircle, XCircle, AlertTriangle, Info, X } from 'lucide-react';

const variantConfig = {
    success: {
        icon: CheckCircle,
        bar: 'bg-emerald-500',
        bg: 'bg-gray-900/95 border-emerald-500/30',
        icon_color: 'text-emerald-400',
        title_color: 'text-emerald-300',
    },
    error: {
        icon: XCircle,
        bar: 'bg-red-500',
        bg: 'bg-gray-900/95 border-red-500/30',
        icon_color: 'text-red-400',
        title_color: 'text-red-300',
    },
    warning: {
        icon: AlertTriangle,
        bar: 'bg-amber-500',
        bg: 'bg-gray-900/95 border-amber-500/30',
        icon_color: 'text-amber-400',
        title_color: 'text-amber-300',
    },
    info: {
        icon: Info,
        bar: 'bg-indigo-500',
        bg: 'bg-gray-900/95 border-indigo-500/30',
        icon_color: 'text-indigo-400',
        title_color: 'text-indigo-300',
    },
};

/**
 * Toast — temporary notification overlay.
 *
 * @param {boolean}  isOpen
 * @param {function} onClose
 * @param {string}   variant   success | error | warning | info
 * @param {string}   title
 * @param {string}   message
 * @param {number}   duration  ms before auto-dismiss (default 4000, 0 = no auto-dismiss)
 */
const Toast = ({
    isOpen,
    onClose,
    variant = 'info',
    title,
    message,
    duration = 4000,
}) => {
    const dismiss = useCallback(() => onClose?.(), [onClose]);

    useEffect(() => {
        if (!isOpen || duration === 0) return;
        const t = setTimeout(dismiss, duration);
        return () => clearTimeout(t);
    }, [isOpen, duration, dismiss]);

    if (!isOpen) return null;

    const cfg = variantConfig[variant] ?? variantConfig.info;
    const Icon = cfg.icon;

    return (
        <div
            role="alert"
            aria-live="assertive"
            className="fixed bottom-6 right-6 z-[9999] flex min-w-[300px] max-w-sm flex-col overflow-hidden rounded-xl border shadow-2xl backdrop-blur-xl animate-in slide-in-from-bottom-4 fade-in duration-300"
            style={{ willChange: 'transform' }}
        >
            {/* coloured top bar */}
            <div className={`h-1 w-full ${cfg.bar}`} />

            <div className={`flex items-start gap-3 p-4 ${cfg.bg}`}>
                <Icon className={`mt-0.5 h-5 w-5 shrink-0 ${cfg.icon_color}`} />

                <div className="flex-1 min-w-0">
                    {title && (
                        <p className={`text-sm font-semibold leading-5 ${cfg.title_color}`}>
                            {title}
                        </p>
                    )}
                    {message && (
                        <p className="mt-0.5 text-sm text-gray-400 leading-5">
                            {message}
                        </p>
                    )}
                </div>

                <button
                    onClick={dismiss}
                    aria-label="Dismiss"
                    className="shrink-0 text-gray-500 hover:text-gray-300 transition-colors p-0.5 rounded"
                >
                    <X className="h-4 w-4" />
                </button>
            </div>

            {/* countdown bar */}
            {duration > 0 && (
                <div className={`h-0.5 w-full ${cfg.bar} opacity-40`}>
                    <div
                        className={`h-full ${cfg.bar}`}
                        style={{
                            animation: `shrink ${duration}ms linear forwards`,
                        }}
                    />
                </div>
            )}

            <style>{`
        @keyframes shrink {
          from { width: 100%; }
          to   { width: 0%; }
        }
      `}</style>
        </div>
    );
};

export default Toast;
