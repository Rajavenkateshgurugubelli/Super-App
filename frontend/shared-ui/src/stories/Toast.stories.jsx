import React, { useState } from 'react';
import Toast from '../components/Toast';
import Button from '../components/Button';

export default {
    title: 'Design System/Toast',
    component: Toast,
    parameters: {
        layout: 'padded',
        backgrounds: { default: 'dark', values: [{ name: 'dark', value: '#0f172a' }] },
    },
    argTypes: {
        variant: {
            control: 'select',
            options: ['success', 'error', 'warning', 'info'],
        },
        duration: { control: 'number' },
    },
};

export const Success = () => {
    const [open, setOpen] = useState(true);
    return (
        <div>
            <Button onClick={() => setOpen(true)}>Show Toast</Button>
            <Toast
                isOpen={open}
                onClose={() => setOpen(false)}
                variant="success"
                title="Transfer complete"
                message="$250.00 USD sent to alice@example.com"
                duration={5000}
            />
        </div>
    );
};

export const Error = () => {
    const [open, setOpen] = useState(true);
    return (
        <div>
            <Button variant="danger" onClick={() => setOpen(true)}>Trigger Error</Button>
            <Toast
                isOpen={open}
                onClose={() => setOpen(false)}
                variant="error"
                title="Transfer failed"
                message="Insufficient balance in your USD wallet."
                duration={6000}
            />
        </div>
    );
};

export const Warning = () => {
    const [open, setOpen] = useState(true);
    return (
        <div>
            <Button variant="secondary" onClick={() => setOpen(true)}>Show Warning</Button>
            <Toast
                isOpen={open}
                onClose={() => setOpen(false)}
                variant="warning"
                title="KYC required"
                message="Complete KYC to transfer amounts above $1,000."
                duration={8000}
            />
        </div>
    );
};

export const Info = () => {
    const [open, setOpen] = useState(true);
    return (
        <div>
            <Button variant="secondary" onClick={() => setOpen(true)}>Show Info</Button>
            <Toast
                isOpen={open}
                onClose={() => setOpen(false)}
                variant="info"
                title="Rate updated"
                message="Live FX rates refreshed. USD/EUR: 0.918"
                duration={4000}
            />
        </div>
    );
};

export const PersistentNoAutoDismiss = () => {
    const [open, setOpen] = useState(true);
    return (
        <div>
            <Button onClick={() => setOpen(true)}>Show Persistent</Button>
            <Toast
                isOpen={open}
                onClose={() => setOpen(false)}
                variant="warning"
                title="Action required"
                message="Please review your account settings."
                duration={0}
            />
        </div>
    );
};
