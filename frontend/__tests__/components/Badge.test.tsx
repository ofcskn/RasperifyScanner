import React from 'react';
import { render } from '@testing-library/react-native';
import { Badge } from '../../components/Badge';
import { Colors } from '../../constants/theme';

describe('Badge', () => {
  it('renders the label text', () => {
    const { getByText } = render(<Badge label="GEMINI" />);
    expect(getByText('GEMINI')).toBeTruthy();
  });

  it('uses default testID "badge"', () => {
    const { getByTestId } = render(<Badge label="test" />);
    expect(getByTestId('badge')).toBeTruthy();
  });

  it('accepts custom testID', () => {
    const { getByTestId } = render(<Badge label="test" testID="my-badge" />);
    expect(getByTestId('my-badge')).toBeTruthy();
  });

  it('applies success variant background', () => {
    const { getByTestId } = render(<Badge label="OK" variant="success" />);
    const style = getByTestId('badge').props.style;
    const flat = Array.isArray(style) ? Object.assign({}, ...style) : style;
    expect(flat.backgroundColor).toBe(Colors.successLight);
  });

  it('applies danger variant background', () => {
    const { getByTestId } = render(<Badge label="ERR" variant="danger" />);
    const style = getByTestId('badge').props.style;
    const flat = Array.isArray(style) ? Object.assign({}, ...style) : style;
    expect(flat.backgroundColor).toBe(Colors.dangerLight);
  });

  it('overrides background with custom color prop', () => {
    const { getByTestId } = render(<Badge label="X" color="#ff0000" />);
    const style = getByTestId('badge').props.style;
    const flat = Array.isArray(style) ? Object.assign({}, ...style) : style;
    expect(flat.backgroundColor).toBe('#ff0000');
  });

  it('renders smaller font for size="sm"', () => {
    const { getByText } = render(<Badge label="sm" size="sm" />);
    const style = getByText('sm').props.style;
    const flat = Array.isArray(style) ? Object.assign({}, ...style) : style;
    expect(flat.fontSize).toBe(10);
  });
});
