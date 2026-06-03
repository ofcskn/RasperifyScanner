import React from 'react';
import { render, fireEvent } from '@testing-library/react-native';
import { PrimaryButton } from '../../components/PrimaryButton';

describe('PrimaryButton', () => {
  it('renders the title text', () => {
    const { getByText } = render(<PrimaryButton title="Save" onPress={() => {}} />);
    expect(getByText('Save')).toBeTruthy();
  });

  it('calls onPress when tapped', () => {
    const onPress = jest.fn();
    const { getByTestId } = render(<PrimaryButton title="Go" onPress={onPress} />);
    fireEvent.press(getByTestId('primary-button'));
    expect(onPress).toHaveBeenCalledTimes(1);
  });

  it('shows spinner and hides title when loading', () => {
    const { getByTestId, queryByText } = render(
      <PrimaryButton title="Submit" onPress={() => {}} loading />
    );
    expect(getByTestId('button-spinner')).toBeTruthy();
    expect(queryByText('Submit')).toBeNull();
  });

  it('does not call onPress when loading', () => {
    const onPress = jest.fn();
    const { getByTestId } = render(<PrimaryButton title="Go" onPress={onPress} loading />);
    fireEvent.press(getByTestId('primary-button'));
    expect(onPress).not.toHaveBeenCalled();
  });

  it('does not call onPress when disabled', () => {
    const onPress = jest.fn();
    const { getByTestId } = render(<PrimaryButton title="Go" onPress={onPress} disabled />);
    fireEvent.press(getByTestId('primary-button'));
    expect(onPress).not.toHaveBeenCalled();
  });

  it('uses custom testID', () => {
    const { getByTestId } = render(<PrimaryButton title="x" onPress={() => {}} testID="my-btn" />);
    expect(getByTestId('my-btn')).toBeTruthy();
  });

  it('marks accessibility state as busy when loading', () => {
    const { getByTestId } = render(<PrimaryButton title="x" onPress={() => {}} loading />);
    expect(getByTestId('primary-button').props.accessibilityState).toMatchObject({ busy: true });
  });

  it('marks accessibility state as disabled when disabled', () => {
    const { getByTestId } = render(<PrimaryButton title="x" onPress={() => {}} disabled />);
    expect(getByTestId('primary-button').props.accessibilityState).toMatchObject({ disabled: true });
  });
});
