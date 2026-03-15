import React, { useState } from 'react';

/**
 * PasskeyButton — handles WebAuthn passkey registration and authentication.
 *
 * Props:
 *   mode: 'register' | 'authenticate'
 *   email: string (required for authenticate, used for login/begin)
 *   token: string (required for register, JWT of logged-in user)
 *   gatewayUrl: string (default: '')
 *   onSuccess: (result) => void
 *   onError: (errorMsg) => void
 */
const PasskeyButton = ({
    mode = 'register',
    email = '',
    token = '',
    gatewayUrl = '',
    onSuccess,
    onError,
}) => {
    const [loading, setLoading] = useState(false);

    // ─ helpers ────────────────────────────────────────────────────────────────

    function bufferToBase64url(buffer) {
        return btoa(String.fromCharCode(...new Uint8Array(buffer)))
            .replace(/\+/g, '-')
            .replace(/\//g, '_')
            .replace(/=/g, '');
    }

    function base64urlToBuffer(base64url) {
        const base64 = base64url.replace(/-/g, '+').replace(/_/g, '/');
        const binary = atob(base64);
        return new Uint8Array([...binary].map((c) => c.charCodeAt(0))).buffer;
    }

    function encodeCredentialForTransport(cred) {
        // Serialise a PublicKeyCredential into a plain JSON object
        const response = cred.response;
        const encoded = {
            id: cred.id,
            rawId: bufferToBase64url(cred.rawId),
            type: cred.type,
            response: {
                clientDataJSON: bufferToBase64url(response.clientDataJSON),
                attestationObject: response.attestationObject
                    ? bufferToBase64url(response.attestationObject)
                    : undefined,
                authenticatorData: response.authenticatorData
                    ? bufferToBase64url(response.authenticatorData)
                    : undefined,
                signature: response.signature
                    ? bufferToBase64url(response.signature)
                    : undefined,
                userHandle: response.userHandle
                    ? bufferToBase64url(response.userHandle)
                    : undefined,
            },
        };
        return encoded;
    }

    // ─ registration ───────────────────────────────────────────────────────────

    async function handleRegister() {
        setLoading(true);
        try {
            // 1. Begin — get options from server
            const beginRes = await fetch(`${gatewayUrl}/api/auth/webauthn/register/begin`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`,
                    'X-Signature': 'bypass', // WAF bypass for dev (remove in prod)
                },
                body: JSON.stringify({ label: 'My Passkey' }),
            });
            if (!beginRes.ok) throw new Error(`Server error: ${beginRes.status}`);
            const options = await beginRes.json();

            // Convert base64url fields to ArrayBuffer as required by WebAuthn API
            options.challenge = base64urlToBuffer(options.challenge);
            options.user.id = base64urlToBuffer(options.user.id);
            if (options.excludeCredentials) {
                options.excludeCredentials = options.excludeCredentials.map((c) => ({
                    ...c,
                    id: base64urlToBuffer(c.id),
                }));
            }

            // 2. Create credential in browser (triggers biometric/PIN prompt)
            const credential = await navigator.credentials.create({ publicKey: options });

            // 3. Complete — send attestation to server
            const encoded = encodeCredentialForTransport(credential);
            const completeRes = await fetch(
                `${gatewayUrl}/api/auth/webauthn/register/complete?label=My+Passkey`,
                {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': `Bearer ${token}`,
                        'X-Signature': 'bypass',
                    },
                    body: JSON.stringify(encoded),
                },
            );
            if (!completeRes.ok) {
                const err = await completeRes.json();
                throw new Error(err.detail || 'Registration failed');
            }
            const result = await completeRes.json();
            onSuccess?.(result);
        } catch (err) {
            onError?.(err.message || String(err));
        } finally {
            setLoading(false);
        }
    }

    // ─ authentication ─────────────────────────────────────────────────────────

    async function handleAuthenticate() {
        setLoading(true);
        try {
            // 1. Begin — get assertion options
            const beginRes = await fetch(`${gatewayUrl}/api/auth/webauthn/login/begin`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email }),
            });
            if (!beginRes.ok) throw new Error(`Server error: ${beginRes.status}`);
            const options = await beginRes.json();

            options.challenge = base64urlToBuffer(options.challenge);
            if (options.allowCredentials) {
                options.allowCredentials = options.allowCredentials.map((c) => ({
                    ...c,
                    id: base64urlToBuffer(c.id),
                }));
            }

            // 2. Get assertion from browser
            const assertion = await navigator.credentials.get({ publicKey: options });

            // 3. Complete — verify with server
            const encoded = encodeCredentialForTransport(assertion);
            const completeRes = await fetch(`${gatewayUrl}/api/auth/webauthn/login/complete`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ assertion: encoded, challenge_email: email }),
            });
            if (!completeRes.ok) {
                const err = await completeRes.json();
                throw new Error(err.detail || 'Authentication failed');
            }
            const result = await completeRes.json();
            onSuccess?.(result); // { token, user }
        } catch (err) {
            onError?.(err.message || String(err));
        } finally {
            setLoading(false);
        }
    }

    const isSupported = typeof window !== 'undefined' && !!window.PublicKeyCredential;

    if (!isSupported) {
        return (
            <p className="text-xs text-gray-500 text-center">
                Passkeys not supported in this browser.
            </p>
        );
    }

    return (
        <button
            onClick={mode === 'register' ? handleRegister : handleAuthenticate}
            disabled={loading}
            className={`
        flex items-center justify-center gap-2 w-full
        px-4 py-2.5 rounded-xl font-medium text-sm
        border border-white/10 text-white
        transition-all duration-200
        ${loading
                    ? 'opacity-50 cursor-not-allowed bg-gray-800'
                    : 'bg-gray-800/60 hover:bg-indigo-600/30 hover:border-indigo-500/50 cursor-pointer'
                }
      `}
        >
            {loading ? (
                <>
                    <span className="animate-spin h-4 w-4 border-2 border-white/20 border-t-white rounded-full" />
                    <span>Waiting for biometric…</span>
                </>
            ) : (
                <>
                    <span>🔑</span>
                    <span>{mode === 'register' ? 'Add Passkey' : 'Sign in with Passkey'}</span>
                </>
            )}
        </button>
    );
};

export default PasskeyButton;
