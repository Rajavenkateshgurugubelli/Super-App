import React from 'react';
import { NavLink } from 'react-router-dom';
import { useI18n } from '../i18n/I18nProvider.jsx';

const navItems = [
  { to: '/', key: 'home' },
  { to: '/payments', key: 'payments' },
  { to: '/shop', key: 'shop' },
  { to: '/services', key: 'services' },
  { to: '/profile', key: 'profile' },
];

const AppLayout = ({ children }) => {
  const { t, locale, setLocale, supportedLocales } = useI18n();

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col">
      {/* Top app bar */}
      <header className="h-16 border-b border-slate-800 flex items-center justify-between px-4 md:px-8 bg-slate-950/80 backdrop-blur">
        <div className="flex items-center gap-2">
          <div className="h-8 w-8 rounded-xl bg-indigo-500/20 border border-indigo-400/40 flex items-center justify-center text-lg">
            $
          </div>
          <div className="flex flex-col leading-tight">
            <span className="text-sm font-semibold text-slate-100">
              Antigravity Super App
            </span>
            <span className="text-[11px] text-slate-500">
              {t('app.tagline')}
            </span>
          </div>
        </div>

        <div className="hidden md:flex items-center gap-3 text-xs text-slate-400">
          <span className="px-2 py-1 rounded-full border border-emerald-500/40 bg-emerald-500/10 text-emerald-300 font-medium">
            {t('app.envBadge')}
          </span>
          <span className="px-2 py-1 rounded-full border border-indigo-500/40 bg-indigo-500/10">
            {t('app.superAppLabel')} · v0
          </span>
          <select
            value={locale}
            onChange={(e) => setLocale(e.target.value)}
            className="bg-slate-900 border border-slate-700 rounded-lg px-2 py-1 text-[11px] text-slate-300 focus:outline-none focus:ring-1 focus:ring-indigo-500"
          >
            {supportedLocales.map((l) => (
              <option key={l.code} value={l.code}>
                {l.label}
              </option>
            ))}
          </select>
        </div>
      </header>

      {/* Content area with sidebar + main */}
      <div className="flex-1 flex">
        {/* Sidebar on desktop */}
        <aside className="hidden md:flex w-56 border-r border-slate-800 flex-col py-4 bg-slate-950/70">
          <nav className="flex-1 px-3 space-y-1">
            {navItems.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.to === '/'}
                className={({ isActive }) =>
                  [
                    'flex items-center justify-between px-3 py-2 rounded-xl text-sm transition-colors cursor-pointer',
                    isActive
                      ? 'bg-slate-900 text-slate-50 border border-slate-700'
                      : 'text-slate-400 hover:bg-slate-900/60 hover:text-slate-100',
                  ].join(' ')
                }
              >
                <span>{t(`nav.${item.key}`)}</span>
                <span className="text-[10px] uppercase tracking-wide text-slate-500">
                  {item.to === '/' ? 'Hub' : 'Domain'}
                </span>
              </NavLink>
            ))}
          </nav>

          <div className="px-3 pt-2 pb-4 text-xs text-slate-500 border-t border-slate-800">
            <div className="font-semibold text-slate-300 mb-1">
              Session: Demo User
            </div>
            <div>Enterprise-ready UX sandbox</div>
          </div>
        </aside>

        {/* Main content */}
        <main className="flex-1 flex flex-col">
          <div className="flex-1 px-4 md:px-8 py-4 md:py-6 overflow-y-auto">
            {children}
          </div>

          {/* Bottom nav on mobile */}
          <nav className="md:hidden border-t border-slate-800 bg-slate-950/90 backdrop-blur px-1 py-1 flex justify-around text-xs">
            {navItems.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.to === '/'}
                className={({ isActive }) =>
                  [
                    'flex-1 flex flex-col items-center justify-center py-1.5 rounded-xl mx-0.5',
                    isActive
                      ? 'bg-slate-900 text-slate-50'
                      : 'text-slate-400 hover:bg-slate-900/60 hover:text-slate-100',
                  ].join(' ')
                }
              >
                <span className="text-[11px] font-medium">
                  {t(`nav.${item.key}`)}
                </span>
              </NavLink>
            ))}
          </nav>
        </main>
      </div>
    </div>
  );
};

export default AppLayout;

