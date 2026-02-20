import React, { useState } from 'react';

const Login = ({ onLogin, onSwitchToSignup }) => {
    const [formData, setFormData] = useState({ email: '', password: '' });
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);

    const handleSubmit = async (e) => {
        e.preventDefault();
        setLoading(true);
        setError(null);
        try {
            const response = await fetch('/api/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(formData),
            });
            const data = await response.json();
            if (!response.ok) throw new Error(data.detail || 'Login failed');
            onLogin(data.user, data.token);
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div>
            {/* Hero text */}
            <div style={{ textAlign: 'center', marginBottom: 32 }}>
                <div style={{
                    display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
                    width: 56, height: 56, borderRadius: 16,
                    background: 'linear-gradient(135deg, #6366f1, #8b5cf6)',
                    fontSize: 24, marginBottom: 16,
                    boxShadow: '0 8px 32px rgba(99,102,241,0.4)'
                }}>⚡</div>
                <h1 style={{ fontSize: 26, fontWeight: 800, letterSpacing: '-0.5px', marginBottom: 6 }}
                    className="glow-text">
                    Welcome back
                </h1>
                <p style={{ color: 'var(--text-secondary)', fontSize: 14 }}>
                    Sign in to your financial dashboard
                </p>
            </div>

            {/* Card */}
            <div className="glass" style={{ padding: '32px 28px' }}>
                {error && (
                    <div style={{
                        background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.2)',
                        borderRadius: 10, padding: '10px 14px', marginBottom: 20,
                        color: '#f87171', fontSize: 13, display: 'flex', alignItems: 'center', gap: 8
                    }}>
                        <span>⚠</span> {error}
                    </div>
                )}

                <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 18 }}>
                    <div>
                        <label className="field-label">Email</label>
                        <input
                            type="email"
                            className="input-field"
                            value={formData.email}
                            onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                            required
                            placeholder="you@example.com"
                        />
                    </div>
                    <div>
                        <label className="field-label">Password</label>
                        <input
                            type="password"
                            className="input-field"
                            value={formData.password}
                            onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                            required
                            placeholder="••••••••"
                        />
                    </div>

                    <button type="submit" className="btn-primary" disabled={loading}
                        style={{ width: '100%', padding: '13px', fontSize: 15, marginTop: 4, borderRadius: 12 }}>
                        {loading ? (
                            <span style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8 }}>
                                <span style={{ width: 16, height: 16, border: '2px solid rgba(255,255,255,0.3)', borderTopColor: 'white', borderRadius: '50%', display: 'inline-block', animation: 'spin 0.7s linear infinite' }} />
                                Signing in...
                                <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
                            </span>
                        ) : 'Sign In →'}
                    </button>
                </form>

                <div style={{
                    marginTop: 20, paddingTop: 14,
                    borderTop: '1px solid rgba(255,255,255,0.06)',
                    textAlign: 'center'
                }}>
                    <span style={{ color: 'var(--text-muted)', fontSize: 13 }}>No account? </span>
                    <button onClick={onSwitchToSignup} style={{
                        background: 'none', border: 'none',
                        color: 'var(--accent)', cursor: 'pointer',
                        fontSize: 13, fontWeight: 600
                    }}>
                        Create one free
                    </button>
                </div>
            </div>
        </div>
    );
};

export default Login;
