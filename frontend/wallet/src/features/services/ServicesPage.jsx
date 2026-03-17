import React from 'react';
import { Zap, Layers, Calendar, ArrowRight } from 'lucide-react';

const ServicesPage = () => {
  const demoServices = [
    {
      id: 1,
      name: 'Utility Settlement',
      description: 'Electricity, fiber optics, and water infrastructure management in one secure node.',
      icon: <Zap className="text-amber-400" size={32} />,
      gradient: 'from-amber-500/10 to-transparent'
    },
    {
      id: 2,
      name: 'Yield Management',
      description: 'Track and optimize your automated financial recurring flows and active subscriptions.',
      icon: <Layers className="text-indigo-400" size={32} />,
      gradient: 'from-indigo-500/10 to-transparent'
    },
    {
      id: 3,
      name: 'Resource Bookings',
      description: 'Schedule and authorize high-priority services from certified partner networks.',
      icon: <Calendar className="text-emerald-400" size={32} />,
      gradient: 'from-emerald-500/10 to-transparent'
    },
  ];

  return (
    <div className="w-full space-y-12 animate-premium-in">
      <div className="space-y-4">
        <div className="flex items-center gap-3">
          <div className="px-3 py-1 bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 text-[10px] font-black uppercase tracking-widest rounded-full">Domain: Services</div>
          <div className="w-2 h-2 rounded-full bg-indigo-500 animate-pulse" />
        </div>
        <h1 className="text-6xl md:text-8xl font-black tracking-tighter text-white leading-none">
          Ecosystem <span className="text-accent-gradient">Modules</span>
        </h1>
        <p className="text-slate-500 font-bold uppercase tracking-[0.2em] text-[10px] max-w-xl">
          Unified control interface for distributed bill settlements, recurring yield optimizations, and partner resource allocations.
        </p>
      </div>

      <div className="bento-grid">
        {demoServices.map((s) => (
          <div key={s.id} className={`bento-item-4 premium-glass p-10 group relative overflow-hidden flex flex-col justify-between border-white/5`}>
            {/* Background Accent */}
            <div className={`absolute inset-0 bg-gradient-to-br ${s.gradient} opacity-0 group-hover:opacity-100 transition-opacity duration-500`} />

            <div className="relative z-10 space-y-8">
              <div className="p-4 bg-white/5 rounded-2xl w-fit border border-white/5 group-hover:border-white/20 transition-all group-hover:scale-110">
                {s.icon}
              </div>
              <div className="space-y-3">
                <h3 className="text-2xl font-black text-white tracking-tight">{s.name}</h3>
                <p className="text-sm text-slate-400 leading-relaxed font-medium">{s.description}</p>
              </div>
            </div>

            <button className="relative z-10 mt-12 flex items-center gap-3 text-[10px] font-black uppercase tracking-widest text-indigo-400 group-hover:text-white transition-colors">
              Access Module <ArrowRight size={14} className="group-hover:translate-x-2 transition-transform" />
            </button>
          </div>
        ))}

        <div className="bento-item-12 premium-glass p-12 border-white/5 bg-slate-900/20">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-8">
            <div className="space-y-4">
              <h3 className="text-3xl font-black text-white tracking-tighter">Infrastructure Expansion</h3>
              <p className="text-slate-500 text-sm font-medium max-w-lg">New partner shards are currently being synchronized. Higher-tier modules will be available following the next epoch settlement.</p>
            </div>
            <div className="flex -space-x-3">
              {[1, 2, 3, 4, 5].map(i => (
                <div key={i} className="w-12 h-12 rounded-full border-4 border-[#020617] bg-slate-800 flex items-center justify-center text-xs font-black text-slate-500">
                  P{i}
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ServicesPage;

