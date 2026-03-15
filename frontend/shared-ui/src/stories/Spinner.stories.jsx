import Spinner from '../components/Spinner';

export default {
    title: 'Design System/Spinner',
    component: Spinner,
    parameters: {
        layout: 'centered',
        backgrounds: { default: 'dark', values: [{ name: 'dark', value: '#111827' }] },
    },
    argTypes: {
        size: { control: 'select', options: ['sm', 'md', 'lg'] },
        color: { control: 'select', options: ['indigo', 'violet', 'cyan', 'white'] },
    },
};

const Template = (args) => <Spinner {...args} />;

export const Default = Template.bind({});
Default.args = { size: 'md', color: 'indigo' };

export const Small = Template.bind({});
Small.args = { size: 'sm', color: 'indigo' };

export const Large = Template.bind({});
Large.args = { size: 'lg', color: 'cyan' };

export const AllSizes = () => (
    <div style={{ display: 'flex', gap: '1.5rem', alignItems: 'center' }}>
        <Spinner size="sm" color="indigo" />
        <Spinner size="md" color="violet" />
        <Spinner size="lg" color="cyan" />
    </div>
);

export const AllColors = () => (
    <div style={{ display: 'flex', gap: '1.5rem', alignItems: 'center' }}>
        <Spinner size="md" color="indigo" />
        <Spinner size="md" color="violet" />
        <Spinner size="md" color="cyan" />
        <Spinner size="md" color="white" />
    </div>
);

export const InlineWithText = () => (
    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: '#9ca3af' }}>
        <Spinner size="sm" color="indigo" />
        <span>Loading wallet data…</span>
    </div>
);
