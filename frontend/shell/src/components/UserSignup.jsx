import React, { useState } from 'react';

const REGIONS = [
    { value: 1, label: '🇮🇳 India' },
    { value: 2, label: '🇪🇺 Europe' },
    { value: 3, label: '🇺🇸 United States' },
];

const UserSignup = ({ onUserCreated }) => {
    const [formData, setFormData] = useState({
        name: '', email: '', phone_number: '', password: '', confirm_password: '', region: 1
    });
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const [success, setSuccess] = useState(null);

    const set = (field, val) => setFormData(prev => ({ ...prev, [field]: val }));

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError(null);
        if (formData.password !== formData.confirm_password) {
            setError('Passwords do not match'); return;
        }
        if (formData.password.length < 6) {
            setError('Password must be at least 6 characters'); return;
        }
        setLoading(true);
        try {
            const response = await fetch('/api/users', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    name: formData.name,
                    email: formData.email,
                    phone_number: formData.phone_number,
                    password: formData.password,
                    region: formData.region,
                }),
            });
            const data = await response.json();
            if (!response.ok) {
                throw new Error(data.detail || 'Failed to create account');
            }
            setSuccess(`🎉 Welcome, ${data.name}! Your account and wallet are ready.`);
            setTimeout(() => onUserCreated(data), 2000);
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div>
            {/* Hero */}
            <div style={{ textAlign: 'center', marginBottom: 28 }}>
                <div style={{
                    display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
                    width: 52, height: 52, borderRadius: 14,
                    background: 'linear-gradient(135deg, #10b981, #06b6d4)',
                    fontSize: 22, marginBottom: 14,
                    boxShadow: '0 8px 32px rgba(16,185,129,0.35)'
                }}>✦</div>
                <h1 style={{ fontSize: 24, fontWeight: 800, letterSpacing: '-0.5px', marginBottom: 6 }}
                    className="glow-text">Create Your Account</h1>
                <p style={{ color: 'var(--text-secondary)', fontSize: 13 }}>
                    Join Global Genesis — your wallet is created automatically
                </p>
            </div>

            <div className="glass" style={{ padding: '28px 24px' }}>
                {error && (
                    <div style={{
                        background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.2)',
                        borderRadius: 10, padding: '10px 14px', marginBottom: 18,
                        color: '#f87171', fontSize: 13, display: 'flex', alignItems: 'center', gap: 8
                    }}>⚠ {error}</div>
                )}
                {success && (
                    <div style={{
                        background: 'rgba(16,185,129,0.1)', border: '1px solid rgba(16,185,129,0.2)',
                        borderRadius: 10, padding: '10px 14px', marginBottom: 18,
                        color: '#34d399', fontSize: 13, textAlign: 'center', fontWeight: 600
                    }}>{success}</div>
                )}

                <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
                    {/* Row: Name */}
                    <div>
                        <label className="field-label">Full Name</label>
                        <input className="input-field" type="text" placeholder="Raja Venkatesh"
                            value={formData.name} onChange={e => set('name', e.target.value)} required />
                    </div>

                    {/* Row: Email */}
                    <div>
                        <label className="field-label">Email Address</label>
                        <input className="input-field" type="email" placeholder="you@example.com"
                            value={formData.email} onChange={e => set('email', e.target.value)} required />
                    </div>

                    {/* Row: Phone */}
                    <div>
                        <label className="field-label">Phone Number</label>
                        <input className="input-field" type="tel" placeholder="+1 555 000 0000"
                            value={formData.phone_number} onChange={e => set('phone_number', e.target.value)} required />
                        <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 5 }}>
                            Used for peer-to-peer transfers by phone number
                        </div>
                    </div>

                    {/* Row: Region */}
                    <div>
                        <label className="field-label">Region</label>
                        <select className="input-field" value={formData.region}
                            onChange={e => set('region', parseInt(e.target.value))}>
                            {REGIONS.map(r => <option key={r.value} value={r.value}>{r.label}</option>)}
                        </select>
                    </div>

                    {/* Row: Passwords */}
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
                        <div>
                            <label className="field-label">Password</label>
                            <input className="input-field" type="password" placeholder="Min 6 chars"
                                value={formData.password} onChange={e => set('password', e.target.value)} required />
                        </div>
                        <div>
                            <label className="field-label">Confirm</label>
                            <input className="input-field" type="password" placeholder="Repeat"
                                value={formData.confirm_password} onChange={e => set('confirm_password', e.target.value)} required />
                        </div>
                    </div>

                    <button type="submit" disabled={loading || !!success}
                        style={{
                            background: 'linear-gradient(135deg, #10b981, #06b6d4)',
                            color: 'white', border: 'none', borderRadius: 12,
                            padding: '13px', fontSize: 15, fontWeight: 700,
                            cursor: loading || success ? 'not-allowed' : 'pointer',
                            opacity: loading || success ? 0.7 : 1,
                            marginTop: 4, transition: 'all .2s',
                            boxShadow: '0 4px 24px rgba(16,185,129,0.3)'
                        }}>
                        {loading ? (
                            <span style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8 }}>
                                <span style={{ width: 16, height: 16, border: '2px solid rgba(255,255,255,0.3)', borderTopColor: 'white', borderRadius: '50%', display: 'inline-block', animation: 'spin .7s linear infinite' }} />
                                Creating account...
                                <style>{`@keyframes spin{to{transform:rotate(360deg)}}`}</style>
                            </span>
                        ) : 'Create Account & Wallet ✦'}
                    </button>
                </form>
            </div>
        </div>
    );
};

export default UserSignup;
