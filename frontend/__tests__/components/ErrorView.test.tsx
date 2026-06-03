import React from 'react';
import { render, fireEvent } from '@testing-library/react-native';
import { ErrorView } from '../../components/ErrorView';

describe('ErrorView', () => {
  it('renders the error message', () => {
    const { getByText } = render(<ErrorView message="Something went wrong" />);
    expect(getByText('Something went wrong')).toBeTruthy();
  });

  it('shows the warning icon', () => {
    const { getByText } = render(<ErrorView message="Oops" />);
    expect(getByText('⚠️')).toBeTruthy();
  });

  it('renders retry button when onRetry is provided', () => {
    const { getByTestId } = render(<ErrorView message="Oops" onRetry={() => {}} />);
    expect(getByTestId('error-retry-button')).toBeTruthy();
  });

  it('does not render retry button when onRetry is omitted', () => {
    const { queryByTestId } = render(<ErrorView message="Oops" />);
    expect(queryByTestId('error-retry-button')).toBeNull();
  });

  it('calls onRetry when "Try Again" is pressed', () => {
    const onRetry = jest.fn();
    const { getByTestId } = render(<ErrorView message="Oops" onRetry={onRetry} />);
    fireEvent.press(getByTestId('error-retry-button'));
    expect(onRetry).toHaveBeenCalledTimes(1);
  });

  it('uses custom testID', () => {
    const { getByTestId } = render(<ErrorView message="x" testID="my-error" />);
    expect(getByTestId('my-error')).toBeTruthy();
  });
});
