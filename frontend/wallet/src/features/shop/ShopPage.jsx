import React from 'react';
import Button from '../../components/Button';

const ShopPage = () => {
  const demoProducts = [
    { id: 1, name: 'Antigravity Card', price: '$9.99 / mo' },
    { id: 2, name: 'Premium FX Pack', price: '$19.00' },
    { id: 3, name: 'Priority Support', price: '$5.00 / mo' },
  ];

  return (
    <div className="space-y-4 md:space-y-6">
      <h1 className="text-2xl md:text-3xl font-semibold tracking-tight text-slate-50">
        Shopping
      </h1>
      <p className="text-sm md:text-base text-slate-400 max-w-2xl">
        A demo Shopping domain that mirrors how a production super app would
        surface products and plans. The data is static today but the UX is
        structured for real catalog APIs.
      </p>

      <section className="rounded-2xl border border-slate-800 bg-slate-900/60 shadow-xl overflow-hidden">
        <header className="px-6 py-4 border-b border-slate-800/80">
          <h2 className="text-base font-semibold text-slate-100">
            Featured products
          </h2>
        </header>
        <div className="p-6">
          <div className="grid gap-4 md:grid-cols-3">
            {demoProducts.map((p) => (
              <div
                key={p.id}
                className="rounded-2xl border border-slate-800 bg-slate-900/40 p-4 flex flex-col justify-between"
              >
                <div>
                  <div className="text-sm font-medium text-slate-100">
                    {p.name}
                  </div>
                  <div className="text-xs text-slate-500 mt-1">
                    Enterprise-style pricing layout · demo only
                  </div>
                </div>
                <div className="mt-3 flex items-center justify-between">
                  <div className="text-sm font-semibold text-slate-50">
                    {p.price}
                  </div>
                  <Button className="text-xs px-3 py-1.5">Add to cart</Button>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>
    </div>
  );
};

export default ShopPage;

