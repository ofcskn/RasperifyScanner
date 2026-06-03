import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { Colors, Radius, Spacing } from '../constants/theme';

type BadgeSize = 'sm' | 'md';
type BadgeVariant = 'primary' | 'success' | 'warning' | 'danger' | 'info' | 'neutral';

const VARIANT_COLORS: Record<BadgeVariant, { bg: string; text: string }> = {
  primary: { bg: Colors.primaryLight, text: Colors.primary },
  success: { bg: Colors.successLight, text: Colors.success },
  warning: { bg: Colors.warningLight, text: Colors.warning },
  danger: { bg: Colors.dangerLight, text: Colors.danger },
  info: { bg: Colors.infoLight, text: Colors.info },
  neutral: { bg: Colors.borderLight, text: Colors.textSecondary },
};

interface BadgeProps {
  label: string;
  variant?: BadgeVariant;
  color?: string;
  textColor?: string;
  size?: BadgeSize;
  testID?: string;
}

export function Badge({
  label,
  variant = 'primary',
  color,
  textColor,
  size = 'md',
  testID,
}: BadgeProps) {
  const palette = VARIANT_COLORS[variant];
  const bg = color ?? palette.bg;
  const fg = textColor ?? palette.text;
  const isSmall = size === 'sm';

  return (
    <View
      style={[styles.badge, { backgroundColor: bg, paddingHorizontal: isSmall ? 6 : 8, paddingVertical: isSmall ? 2 : 4 }]}
      testID={testID ?? 'badge'}
    >
      <Text style={[styles.text, { color: fg, fontSize: isSmall ? 10 : 12 }]}>{label}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  badge: {
    borderRadius: Radius.xl,
    alignSelf: 'flex-start',
  },
  text: {
    fontWeight: '700',
    letterSpacing: 0.3,
  },
});
