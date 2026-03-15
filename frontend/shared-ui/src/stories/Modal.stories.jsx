import React, { useState } from 'react';
import Modal from '../components/Modal';
import Button from '../components/Button';

export default {
    title: 'Design System/Modal',
    component: Modal,
    parameters: {
        backgrounds: { default: 'dark', values: [{ name: 'dark', value: '#0f172a' }] },
    },
};

export const Default = () => {
    const [open, setOpen] = useState(false);
    return (
        <div>
            <Button onClick={() => setOpen(true)}>Open Modal</Button>
            <Modal isOpen={open} onClose={() => setOpen(false)} title="Confirm Transfer">
                <p style={{ color: '#9ca3af' }}>
                    Are you sure you want to transfer $500.00 USD to Alice?
                </p>
                <div style={{ marginTop: '1.5rem', display: 'flex', gap: '0.75rem', justifyContent: 'flex-end' }}>
                    <Button variant="secondary" onClick={() => setOpen(false)}>Cancel</Button>
                    <Button variant="primary" onClick={() => setOpen(false)}>Confirm</Button>
                </div>
            </Modal>
        </div>
    );
};

export const DangerConfirm = () => {
    const [open, setOpen] = useState(false);
    return (
        <div>
            <Button variant="danger" onClick={() => setOpen(true)}>Delete Account</Button>
            <Modal isOpen={open} onClose={() => setOpen(false)} title="Delete Account">
                <p style={{ color: '#9ca3af' }}>
                    This is irreversible. All wallets and transactions will be permanently deleted.
                </p>
                <div style={{ marginTop: '1.5rem', display: 'flex', gap: '0.75rem', justifyContent: 'flex-end' }}>
                    <Button variant="secondary" onClick={() => setOpen(false)}>Cancel</Button>
                    <Button variant="danger" onClick={() => setOpen(false)}>Yes, Delete</Button>
                </div>
            </Modal>
        </div>
    );
};
