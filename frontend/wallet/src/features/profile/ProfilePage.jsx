import React from 'react';
import Input from '../../components/Input';
import Button from '../../components/Button';

const ProfilePage = () => {
  return (
    <div className="space-y-4 md:space-y-6">
      <h1 className="text-2xl md:text-3xl font-semibold tracking-tight text-slate-50">
        Profile & Settings
      </h1>
      <p className="text-sm md:text-base text-slate-400 max-w-2xl">
        Enterprise-style profile and preferences shell. The fields here are
        static today, but the layout mirrors a production account experience.
      </p>

      <div className="grid gap-4 md:gap-6 md:grid-cols-2">
        <section className="rounded-2xl border border-slate-800 bg-slate-900/60 shadow-xl overflow-hidden">
          <header className="px-6 py-4 border-b border-slate-800/80">
            <h2 className="text-base font-semibold text-slate-100">
              Profile details
            </h2>
          </header>
          <div className="p-6 space-y-4">
            <Input label="Full name" placeholder="Demo User" />
            <Input label="Email" type="email" placeholder="demo@example.com" />
            <Input label="Phone" type="tel" placeholder="+1 555 000 0000" />
            <div className="flex justify-end">
              <Button className="text-sm px-4">Save changes</Button>
            </div>
          </div>
        </section>

        <section className="rounded-2xl border border-slate-800 bg-slate-900/60 shadow-xl overflow-hidden">
          <header className="px-6 py-4 border-b border-slate-800/80">
            <h2 className="text-base font-semibold text-slate-100">
              Security & notifications
            </h2>
          </header>
          <div className="p-6 space-y-3 text-sm text-slate-300">
            <div className="flex items-center justify-between">
              <div>
                <div className="font-medium">Two-factor authentication</div>
                <div className="text-xs text-slate-500">
                  Designed for OTP / app-based 2FA integrations.
                </div>
              </div>
              <Button variant="secondary" className="text-xs px-3 py-1.5">
                Configure
              </Button>
            </div>
            <div className="flex items-center justify-between">
              <div>
                <div className="font-medium">New device alerts</div>
                <div className="text-xs text-slate-500">
                  Email and in-app alerts when your account is accessed from a
                  new device.
                </div>
              </div>
              <Button variant="secondary" className="text-xs px-3 py-1.5">
                Manage
              </Button>
            </div>
          </div>
        </section>
      </div>
    </div>
  );
};

export default ProfilePage;

