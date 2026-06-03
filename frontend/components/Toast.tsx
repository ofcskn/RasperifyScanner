import React, { useEffect, useRef } from 'react';
import { View, Text, Animated, StyleSheet } from 'react-native';
import { Colors, Radius, Spacing, Typography } from '../constants/theme';

export type ToastType = 'success' | 'error' | 'info';

interface ToastProps {
  visible: boolean;
  message: string;
  type?: ToastType;
  onHide: () => void;
}

const TYPE_COLORS: Record<ToastType, string> = {
  success: Colors.success,
  error: Colors.danger,
  info: Colors.primary,
};

const TYPE_ICONS: Record<ToastType, string> = {
  success: '✓',
  error: '✕',
  info: 'ℹ',
};

const AUTO_DISMISS_MS = 3000;

export function Toast({ visible, message, type = 'info', onHide }: ToastProps) {
  const translateY = useRef(new Animated.Value(80)).current;

  useEffect(() => {
    if (visible) {
      Animated.spring(translateY, {
        toValue: 0,
        useNativeDriver: true,
        tension: 80,
        friction: 10,
      }).start();
      const timer = setTimeout(() => {
        hide();
      }, AUTO_DISMISS_MS);
      return () => clearTimeout(timer);
    }
  }, [visible]);

  const hide = () => {
    Animated.timing(translateY, {
      toValue: 80,
      duration: 200,
      useNativeDriver: true,
    }).start(() => onHide());
  };

  if (!visible) return null;

  const bg = TYPE_COLORS[type];

  return (
    <Animated.View
      style={[styles.container, { backgroundColor: bg, transform: [{ translateY }] }]}
      testID="toast"
      pointerEvents="none"
    >
      <Text style={styles.icon}>{TYPE_ICONS[type]}</Text>
      <Text style={styles.message} numberOfLines={2}>{message}</Text>
    </Animated.View>
  );
}

const styles = StyleSheet.create({
  container: {
    position: 'absolute',
    bottom: Spacing.xxl,
    left: Spacing.lg,
    right: Spacing.lg,
    borderRadius: Radius.lg,
    paddingVertical: Spacing.md,
    paddingHorizontal: Spacing.lg,
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.sm,
    zIndex: 9999,
  },
  icon: {
    fontSize: 16,
    color: Colors.white,
    fontWeight: '700',
  },
  message: {
    ...Typography.body,
    color: Colors.white,
    flex: 1,
    fontWeight: '500',
  },
});
