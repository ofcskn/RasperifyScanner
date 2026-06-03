import React from 'react';
import { View, ViewStyle, StyleSheet } from 'react-native';
import { Colors, Radius, Shadow, Spacing } from '../constants/theme';

interface CardProps {
  children: React.ReactNode;
  style?: ViewStyle;
  padding?: number;
  testID?: string;
}

export function Card({ children, style, padding = Spacing.lg, testID }: CardProps) {
  return (
    <View style={[styles.card, { padding }, style]} testID={testID ?? 'card'}>
      {children}
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: Colors.surface,
    borderRadius: Radius.lg,
    marginBottom: Spacing.lg,
    ...Shadow.md,
  },
});
