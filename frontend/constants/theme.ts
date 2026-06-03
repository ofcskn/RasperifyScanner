export const Colors = {
  primary: '#2563eb',
  primaryLight: '#eff6ff',
  primaryDark: '#1e3a5f',
  success: '#059669',
  successLight: '#d1fae5',
  warning: '#d97706',
  warningLight: '#fef3c7',
  danger: '#dc2626',
  dangerLight: '#fee2e2',
  info: '#0ea5e9',
  infoLight: '#e0f2fe',
  background: '#f0f4f8',
  surface: '#ffffff',
  border: '#e5e7eb',
  borderLight: '#f3f4f6',
  text: '#111827',
  textSecondary: '#6b7280',
  textMuted: '#9ca3af',
  white: '#ffffff',
} as const;

export const Spacing = {
  xs: 4,
  sm: 8,
  md: 12,
  lg: 16,
  xl: 24,
  xxl: 32,
} as const;

export const Radius = {
  sm: 6,
  md: 10,
  lg: 14,
  xl: 20,
} as const;

export const Shadow = {
  sm: {
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.05,
    shadowRadius: 4,
    elevation: 1,
  },
  md: {
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.08,
    shadowRadius: 8,
    elevation: 3,
  },
} as const;

export const Typography = {
  h1: { fontSize: 22, fontWeight: '800' as const, color: Colors.text },
  h2: { fontSize: 18, fontWeight: '700' as const, color: Colors.text },
  h3: { fontSize: 15, fontWeight: '600' as const, color: Colors.text },
  body: { fontSize: 14, color: Colors.text },
  label: { fontSize: 13, color: Colors.textSecondary },
  caption: { fontSize: 12, color: Colors.textMuted },
} as const;
