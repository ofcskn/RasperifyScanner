import React from 'react';
import { Text } from 'react-native';
import { render } from '@testing-library/react-native';
import { Card } from '../../components/Card';
import { Colors, Radius, Spacing } from '../../constants/theme';

describe('Card', () => {
  it('renders children', () => {
    const { getByText } = render(<Card><Text>Hello</Text></Card>);
    expect(getByText('Hello')).toBeTruthy();
  });

  it('uses default testID "card"', () => {
    const { getByTestId } = render(<Card><Text>x</Text></Card>);
    expect(getByTestId('card')).toBeTruthy();
  });

  it('accepts custom testID', () => {
    const { getByTestId } = render(<Card testID="my-card"><Text>x</Text></Card>);
    expect(getByTestId('my-card')).toBeTruthy();
  });

  it('applies default padding from theme', () => {
    const { getByTestId } = render(<Card><Text>x</Text></Card>);
    const style = getByTestId('card').props.style;
    const flat = Array.isArray(style) ? Object.assign({}, ...style) : style;
    expect(flat.padding).toBe(Spacing.lg);
  });

  it('applies custom padding', () => {
    const { getByTestId } = render(<Card padding={8}><Text>x</Text></Card>);
    const style = getByTestId('card').props.style;
    const flat = Array.isArray(style) ? Object.assign({}, ...style) : style;
    expect(flat.padding).toBe(8);
  });

  it('merges custom style', () => {
    const { getByTestId } = render(<Card style={{ marginTop: 20 }}><Text>x</Text></Card>);
    const style = getByTestId('card').props.style;
    const flat = Array.isArray(style) ? Object.assign({}, ...style) : style;
    expect(flat.marginTop).toBe(20);
  });

  it('has white background by default', () => {
    const { getByTestId } = render(<Card><Text>x</Text></Card>);
    const style = getByTestId('card').props.style;
    const flat = Array.isArray(style) ? Object.assign({}, ...style) : style;
    expect(flat.backgroundColor).toBe(Colors.surface);
  });
});
