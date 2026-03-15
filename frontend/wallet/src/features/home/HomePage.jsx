import React from 'react';
import Button from '../../components/Button';
import { useI18n } from '../../i18n/I18nProvider.jsx';

const HomePage = () => {
  const { t } = useI18n();

  return (
    <div className="space-y-4 md:space-y-6">
      <h1 className="text-2xl md:text-3xl font-semibold tracking-tight text-slate-50">
        {t('home.title')}
      </h1>
      <p className="text-sm md:text-base text-slate-400 max-w-2xl">
        {t('home.subtitle')}
      </p>

      <div className="grid gap-4 md:gap-6 md:grid-cols-3">
        <section className="md:col-span-2 rounded-2xl border border-slate-800 bg-slate-900/60 shadow-xl overflow-hidden">
          <header className="px-6 py-4 border-b border-slate-800/80">
            <h2 className="text-base font-semibold text-slate-100">
              {t('home.overviewTitle')}
            </h2>
          </header>
          <div className="p-6">
            <div className="grid gap-4 md:grid-cols-3 text-sm">
              <div>
                <div className="text-slate-400 text-xs uppercase tracking-wide mb-1">
                  {t('home.walletBalance')}
                </div>
                <div className="text-xl font-semibold">$12,340.00</div>
                <div className="text-xs text-emerald-400 mt-1">
                  +$420 today · demo data
                </div>
              </div>
              <div>
                <div className="text-slate-400 text-xs uppercase tracking-wide mb-1">
                  {t('home.openOrders')}
                </div>
                <div className="text-xl font-semibold">3</div>
                <div className="text-xs text-slate-500 mt-1">
                  {t('home.openOrdersHint')}
                </div>
              </div>
              <div>
                <div className="text-slate-400 text-xs uppercase tracking-wide mb-1">
                  {t('home.upcomingServices')}
                </div>
                <div className="text-xl font-semibold">2</div>
                <div className="text-xs text-slate-500 mt-1">
                  {t('home.upcomingServicesHint')}
                </div>
              </div>
            </div>
          </div>
        </section>

        <section className="rounded-2xl border border-slate-800 bg-slate-900/60 shadow-xl overflow-hidden">
          <header className="px-6 py-4 border-b border-slate-800/80">
            <h2 className="text-base font-semibold text-slate-100">
              {t('home.quickActions')}
            </h2>
          </header>
          <div className="p-6 space-y-2">
            <Button className="w-full text-sm mb-1">
              {t('home.actionSendMoney')}
            </Button>
            <Button variant="secondary" className="w-full text-sm mb-1">
              {t('home.actionPayBill')}
            </Button>
            <Button variant="secondary" className="w-full text-sm mb-1">
              {t('home.actionBrowseOffers')}
            </Button>
          </div>
        </section>
      </div>
    </div>
  );
};

export default HomePage;

