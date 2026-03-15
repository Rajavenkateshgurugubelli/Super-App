import Badge from '../components/Badge';

export default {
    title: 'Design System/Badge',
    component: Badge,
    parameters: {
        layout: 'centered',
        backgrounds: { default: 'dark', values: [{ name: 'dark', value: '#111827' }] },
    },
    argTypes: {
        variant: {
            control: 'select',
            options: ['success', 'warning', 'error', 'info', 'neutral', 'USD', 'EUR', 'INR'],
        },
        size: { control: 'select', options: ['sm', 'md', 'lg'] },
        dot: { control: 'boolean' },
    },
};

const Template = (args) => <Badge {...args} />;

export const Success = Template.bind({});
Success.args = { variant: 'success', children: 'Active' };

export const Warning = Template.bind({});
Warning.args = { variant: 'warning', children: 'Pending KYC' };

export const Error = Template.bind({});
Error.args = { variant: 'error', children: 'Failed' };

export const Info = Template.bind({});
Info.args = { variant: 'info', children: 'Processing' };

export const WithLiveDot = Template.bind({});
WithLiveDot.args = { variant: 'success', dot: true, children: 'Live' };

export const CurrencyVariants = () => (
    <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
        <Badge variant="USD">USD</Badge>
        <Badge variant="EUR">EUR</Badge>
        <Badge variant="INR">INR</Badge>
    </div>
);

export const AllSizes = () => (
    <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center' }}>
        <Badge variant="info" size="sm">Small</Badge>
        <Badge variant="info" size="md">Medium</Badge>
        <Badge variant="info" size="lg">Large</Badge>
    </div>
);

export const StatusGallery = () => (
    <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
        <Badge variant="success">Completed</Badge>
        <Badge variant="warning" dot>Pending</Badge>
        <Badge variant="error">Failed</Badge>
        <Badge variant="info">Processing</Badge>
        <Badge variant="neutral">Unknown</Badge>
    </div>
);
