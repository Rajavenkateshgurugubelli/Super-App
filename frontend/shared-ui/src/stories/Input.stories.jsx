import React, { useState } from 'react';
import Input from '../components/Input';
import { Mail, Lock, Phone } from 'lucide-react';

export default {
    title: 'Design System/Input',
    component: Input,
    parameters: {
        layout: 'centered',
        backgrounds: { default: 'dark', values: [{ name: 'dark', value: '#111827' }] },
    },
};

export const Default = () => {
    const [val, setVal] = useState('');
    return (
        <div style={{ width: '320px' }}>
            <Input
                label="Email address"
                placeholder="you@example.com"
                value={val}
                onChange={(e) => setVal(e.target.value)}
            />
        </div>
    );
};

export const WithIcon = () => (
    <div style={{ width: '320px', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
        <Input label="Email" placeholder="you@example.com" icon={Mail} />
        <Input label="Password" placeholder="••••••••" type="password" icon={Lock} />
        <Input label="Phone" placeholder="+1 (555) 000-0000" icon={Phone} />
    </div>
);

export const WithError = () => (
    <div style={{ width: '320px' }}>
        <Input
            label="Email"
            placeholder="you@example.com"
            icon={Mail}
            error="Please enter a valid email address."
            defaultValue="not-an-email"
        />
    </div>
);

export const Disabled = () => (
    <div style={{ width: '320px' }}>
        <Input label="Readonly field" value="read-only value" disabled />
    </div>
);
