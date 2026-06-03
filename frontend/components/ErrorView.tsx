import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { Colors, Spacing, Typography } from '../constants/theme';
import { PrimaryButton } from './PrimaryButton';

interface ErrorViewProps {
  message: string;
  onRetry?: () => void;
  testID?: string;
}

export function ErrorView({ message, onRetry, testID }: ErrorViewProps) {
  return (
    <View style={styles.container} testID={testID ?? 'error-view'}>
      <Text style={styles.icon}>⚠️</Text>
      <Text style={styles.message}>{message}</Text>
      {onRetry && (
        <PrimaryButton
          title="Try Again"
          onPress={onRetry}
          style={styles.retryButton}
          testID="error-retry-button"
        />
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    padding: Spacing.xl,
  },
  icon: {
    fontSize: 36,
    marginBottom: Spacing.md,
  },
  message: {
    ...Typography.body,
    color: Colors.textSecondary,
    textAlign: 'center',
    marginBottom: Spacing.lg,
    lineHeight: 22,
  },
  retryButton: {
    minWidth: 140,
  },
});
