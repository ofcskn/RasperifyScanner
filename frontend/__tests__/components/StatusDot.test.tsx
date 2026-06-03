import React from 'react';
import { render } from '@testing-library/react-native';
import { StatusDot } from '../../components/StatusDot';
import { Colors } from '../../constants/theme';

describe('StatusDot', () => {
  it('renders without crashing', () => {
    const { getByTestId } = render(<StatusDot active />);
    expect(getByTestId('status-dot')).toBeTruthy();
  });

  it('uses green background when active', () => {
    const { getByTestId } = render(<StatusDot active />);
    const style = getByTestId('status-dot').props.style;
    const flat = Array.isArray(style) ? Object.assign({}, ...style) : style;
    expect(flat.backgroundColor).toBe(Colors.success);
  });

  it('uses red background when inactive', () => {
    const { getByTestId } = render(<StatusDot active={false} />);
    const style = getByTestId('status-dot').props.style;
    const flat = Array.isArray(style) ? Object.assign({}, ...style) : style;
    expect(flat.backgroundColor).toBe(Colors.danger);
  });

  it('defaults to size 10', () => {
    const { getByTestId } = render(<StatusDot active />);
    const style = getByTestId('status-dot').props.style;
    const flat = Array.isArray(style) ? Object.assign({}, ...style) : style;
    expect(flat.width).toBe(10);
    expect(flat.height).toBe(10);
  });

  it('respects custom size', () => {
    const { getByTestId } = render(<StatusDot active size={16} />);
    const style = getByTestId('status-dot').props.style;
    const flat = Array.isArray(style) ? Object.assign({}, ...style) : style;
    expect(flat.width).toBe(16);
    expect(flat.height).toBe(16);
    expect(flat.borderRadius).toBe(8);
  });

  it('has descriptive accessibility label', () => {
    const { getByLabelText } = render(<StatusDot active />);
    expect(getByLabelText('active')).toBeTruthy();
  });

  it('has inactive accessibility label when not active', () => {
    const { getByLabelText } = render(<StatusDot active={false} />);
    expect(getByLabelText('inactive')).toBeTruthy();
  });
});
