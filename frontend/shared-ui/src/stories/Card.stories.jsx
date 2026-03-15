import Card, { CardHeader, CardTitle, CardContent } from '../components/Card';

export default {
    title: 'Design System/Card',
    component: Card,
    parameters: {
        layout: 'padded',
        backgrounds: { default: 'dark', values: [{ name: 'dark', value: '#0f172a' }] },
    },
};

export const Default = () => (
    <div style={{ width: '360px' }}>
        <Card>
            <CardHeader>
                <CardTitle>Wallet Balance</CardTitle>
            </CardHeader>
            <CardContent>
                <p style={{ color: '#9ca3af', margin: 0 }}>$1,234.56 USD</p>
            </CardContent>
        </Card>
    </div>
);

export const WithCustomContent = () => (
    <div style={{ width: '360px' }}>
        <Card>
            <CardContent>
                <p style={{ color: 'white', margin: 0 }}>A card with only content, no header.</p>
            </CardContent>
        </Card>
    </div>
);

export const Stacked = () => (
    <div style={{ width: '360px', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
        {['USD Wallet', 'EUR Wallet', 'INR Wallet'].map((title) => (
            <Card key={title}>
                <CardHeader>
                    <CardTitle>{title}</CardTitle>
                </CardHeader>
                <CardContent>
                    <p style={{ color: '#9ca3af', margin: 0 }}>Active</p>
                </CardContent>
            </Card>
        ))}
    </div>
);
