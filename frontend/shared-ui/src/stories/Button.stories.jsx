import Button from '../components/Button';

export default {
    title: 'Design System/Button',
    component: Button,
    parameters: {
        layout: 'centered',
        backgrounds: { default: 'dark', values: [{ name: 'dark', value: '#111827' }] },
    },
    argTypes: {
        variant: {
            control: 'select',
            options: ['primary', 'secondary', 'danger'],
        },
        onClick: { action: 'clicked' },
    },
};

const Template = (args) => <Button {...args} />;

export const Primary = Template.bind({});
Primary.args = { variant: 'primary', children: 'Primary Action' };

export const Secondary = Template.bind({});
Secondary.args = { variant: 'secondary', children: 'Secondary Action' };

export const Danger = Template.bind({});
Danger.args = { variant: 'danger', children: 'Delete Account' };

export const Disabled = Template.bind({});
Disabled.args = { variant: 'primary', children: 'Disabled', disabled: true };

export const AllVariants = () => (
    <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap' }}>
        <Button variant="primary">Primary</Button>
        <Button variant="secondary">Secondary</Button>
        <Button variant="danger">Danger</Button>
        <Button variant="primary" disabled>Disabled</Button>
    </div>
);
