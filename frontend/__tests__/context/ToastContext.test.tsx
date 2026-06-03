import React from 'react';
import { TouchableOpacity, Text } from 'react-native';
import { render, fireEvent, waitFor, act } from '@testing-library/react-native';
import { ToastProvider, useToast } from '../../context/ToastContext';

function TestConsumer({ type }: { type?: 'success' | 'error' | 'info' }) {
  const { showToast } = useToast();
  return (
    <TouchableOpacity
      testID="trigger"
      onPress={() => showToast('Hello Toast', type)}
    />
  );
}

function wrap(ui: React.ReactElement) {
  return render(<ToastProvider>{ui}</ToastProvider>);
}

describe('ToastContext', () => {
  beforeEach(() => {
    jest.useFakeTimers();
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  it('does not show toast initially', () => {
    const { queryByTestId } = wrap(<TestConsumer />);
    expect(queryByTestId('toast')).toBeNull();
  });

  it('shows toast after showToast is called', async () => {
    const { getByTestId, queryByTestId } = wrap(<TestConsumer />);
    await act(async () => { fireEvent.press(getByTestId('trigger')); });
    expect(getByTestId('toast')).toBeTruthy();
  });

  it('displays the correct message', async () => {
    const { getByTestId, getByText } = wrap(<TestConsumer />);
    await act(async () => { fireEvent.press(getByTestId('trigger')); });
    expect(getByText('Hello Toast')).toBeTruthy();
  });

  it('throws when useToast is used outside ToastProvider', () => {
    const spy = jest.spyOn(console, 'error').mockImplementation(() => {});
    expect(() => render(<TestConsumer />)).toThrow('useToast must be used inside <ToastProvider>');
    spy.mockRestore();
  });
});
