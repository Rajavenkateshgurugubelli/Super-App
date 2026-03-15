import React from 'react';
import WalletDashboard from '../../components/WalletDashboard.jsx';
import { useI18n } from '../../i18n/I18nProvider.jsx';

const PaymentsPage = () => {
  // In a full app this would come from auth/session.
  const demoUser = { name: 'Demo User' };
  const { t } = useI18n();

  return (
    <div className="space-y-4 md:space-y-6">
      <h1 className="text-2xl md:text-3xl font-semibold tracking-tight text-slate-50">
        {t('payments.title')}
      </h1>
      <p className="text-sm md:text-base text-slate-400 max-w-2xl">
        {t('payments.subtitle')}
      </p>

      <section className="rounded-2xl border border-slate-800 bg-slate-900/60 shadow-xl overflow-hidden">
        <header className="px-6 py-4 border-b border-slate-800/80">
          <h2 className="text-base font-semibold text-slate-100">
            Wallet experience
          </h2>
        </header>
        <div className="p-4 md:p-6 flex justify-center">
          <WalletDashboard user={demoUser} />
        </div>
      </section>
    </div>
  );
};

export default PaymentsPage;

