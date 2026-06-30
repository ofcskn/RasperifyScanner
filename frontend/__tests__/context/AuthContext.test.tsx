import React from 'react';
import { Text, TouchableOpacity } from 'react-native';
import { render, fireEvent, waitFor, act } from '@testing-library/react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { AuthProvider, useAuth } from '../../context/AuthContext';

jest.mock('../../services/api', () => ({
  login: jest.fn(),
  setTokens: jest.fn(),
  clearTokens: jest.fn(),
  setAuthEvents: jest.fn(),
}));

const { login: mockLogin, setTokens: mockSetTokens } = require('../../services/api');

function TestConsumer() {
  const { isAuthenticated, username, isLoading, login, logout } = useAuth();
  return (
    <>
      <Text testID="loading">{String(isLoading)}</Text>
      <Text testID="auth">{String(isAuthenticated)}</Text>
      <Text testID="user">{username ?? 'none'}</Text>
      <TouchableOpacity testID="login-btn" onPress={() => login('admin', 'pass')} />
      <TouchableOpacity testID="logout-btn" onPress={logout} />
    </>
  );
}

function wrap(ui: React.ReactElement) {
  return render(<AuthProvider>{ui}</AuthProvider>);
}

describe('AuthContext', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    (AsyncStorage.clear as jest.Mock)();
  });

  it('starts as loading while restoring session', async () => {
    const { getByTestId } = wrap(<TestConsumer />);
    // isLoading starts true
    expect(getByTestId('loading').props.children).toBe('true');
    await waitFor(() => expect(getByTestId('loading').props.children).toBe('false'));
  });

  it('is unauthenticated when no stored tokens', async () => {
    const { getByTestId } = wrap(<TestConsumer />);
    await waitFor(() => expect(getByTestId('loading').props.children).toBe('false'));
    expect(getByTestId('auth').props.children).toBe('false');
  });

  it('restores session when valid tokens are in AsyncStorage', async () => {
    await AsyncStorage.multiSet([
      ['rasperify_access_token', 'tok_access'],
      ['rasperify_refresh_token', 'tok_refresh'],
      ['rasperify_username', 'alice'],
    ]);
    const { getByTestId } = wrap(<TestConsumer />);
    await waitFor(() => expect(getByTestId('auth').props.children).toBe('true'));
    expect(getByTestId('user').props.children).toBe('alice');
    expect(mockSetTokens).toHaveBeenCalledWith('tok_access', 'tok_refresh');
  });

  it('authenticates on successful login', async () => {
    mockLogin.mockResolvedValueOnce({
      access_token: 'new_access',
      refresh_token: 'new_refresh',
      token_type: 'bearer',
    });
    const { getByTestId } = wrap(<TestConsumer />);
    await waitFor(() => expect(getByTestId('loading').props.children).toBe('false'));

    await act(async () => {
      fireEvent.press(getByTestId('login-btn'));
    });

    await waitFor(() => expect(getByTestId('auth').props.children).toBe('true'));
    expect(getByTestId('user').props.children).toBe('admin');
  });

  it('persists tokens to AsyncStorage on login', async () => {
    mockLogin.mockResolvedValueOnce({
      access_token: 'a',
      refresh_token: 'r',
      token_type: 'bearer',
    });
    const { getByTestId } = wrap(<TestConsumer />);
    await waitFor(() => expect(getByTestId('loading').props.children).toBe('false'));
    await act(async () => { fireEvent.press(getByTestId('login-btn')); });
    await waitFor(() => expect(getByTestId('auth').props.children).toBe('true'));

    const access = await AsyncStorage.getItem('rasperify_access_token');
    const refresh = await AsyncStorage.getItem('rasperify_refresh_token');
    expect(access).toBe('a');
    expect(refresh).toBe('r');
  });

  it('clears auth state and storage on logout', async () => {
    mockLogin.mockResolvedValueOnce({ access_token: 'a', refresh_token: 'r', token_type: 'bearer' });
    const { getByTestId } = wrap(<TestConsumer />);
    await waitFor(() => expect(getByTestId('loading').props.children).toBe('false'));
    await act(async () => { fireEvent.press(getByTestId('login-btn')); });
    await waitFor(() => expect(getByTestId('auth').props.children).toBe('true'));

    await act(async () => { fireEvent.press(getByTestId('logout-btn')); });
    await waitFor(() => expect(getByTestId('auth').props.children).toBe('false'));

    const token = await AsyncStorage.getItem('rasperify_access_token');
    expect(token).toBeNull();
  });

  it('throws when useAuth is used outside AuthProvider', () => {
    const spy = jest.spyOn(console, 'error').mockImplementation(() => {});
    expect(() => render(<TestConsumer />)).toThrow('useAuth must be used inside <AuthProvider>');
    spy.mockRestore();
  });
});
