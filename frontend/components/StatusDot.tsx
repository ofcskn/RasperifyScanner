import React from 'react';
import { View, StyleSheet } from 'react-native';
import { Colors } from '../constants/theme';

interface StatusDotProps {
  active: boolean;
  size?: number;
  testID?: string;
}

export function StatusDot({ active, size = 10, testID }: StatusDotProps) {
  return (
    <View
      style={[
        styles.dot,
        {
          width: size,
          height: size,
          borderRadius: size / 2,
          backgroundColor: active ? Colors.success : Colors.danger,
        },
      ]}
      testID={testID ?? 'status-dot'}
      accessibilityLabel={active ? 'active' : 'inactive'}
    />
  );
}

const styles = StyleSheet.create({
  dot: {
    alignSelf: 'center',
  },
});
