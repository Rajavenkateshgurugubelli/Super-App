import React from 'react';
import { Button } from 'shared-ui';

const ServicesPage = () => {
  const demoServices = [
    {
      id: 1,
      name: 'Bill payments',
      description: 'Electricity, internet, and utilities in one place.',
    },
    {
      id: 2,
      name: 'Subscriptions',
      description: 'Track and manage recurring subscriptions.',
    },
    {
      id: 3,
      name: 'Bookings',
      description: 'Schedule and pay for services from partners.',
    },
  ];

  return (
    <div className="space-y-4 md:space-y-6">
      <h1 className="text-2xl md:text-3xl font-semibold tracking-tight text-slate-50">
        Services
      </h1>
      <p className="text-sm md:text-base text-slate-400 max-w-2xl">
        This Services domain illustrates how you would cluster bill payments,
        recurring subscriptions, and partner bookings within the super app.
      </p>

      <section className="rounded-2xl border border-slate-800 bg-slate-900/60 shadow-xl overflow-hidden">
        <header className="px-6 py-4 border-b border-slate-800/80">
          <h2 className="text-base font-semibold text-slate-100">
            Service categories
          </h2>
        </header>
        <div className="p-6">
          <div className="grid gap-4 md:grid-cols-3">
            {demoServices.map((s) => (
              <div
                key={s.id}
                className="rounded-2xl border border-slate-800 bg-slate-900/40 p-4 flex flex-col justify-between"
              >
                <div>
                  <div className="text-sm font-medium text-slate-100">
                    {s.name}
                  </div>
                  <div className="text-xs text-slate-500 mt-1">
                    {s.description}
                  </div>
                </div>
                <Button variant="secondary" className="mt-4 text-xs px-3 py-1.5">
                  View sample journey
                </Button>
              </div>
            ))}
          </div>
        </div>
      </section>
    </div>
  );
};

export default ServicesPage;

