import { Colors, Spacing, Radius, Shadow, Typography } from '../../constants/theme';

describe('theme constants', () => {
  describe('Colors', () => {
    it('has required semantic color keys', () => {
      const required = ['primary', 'success', 'warning', 'danger', 'background', 'surface', 'text', 'textSecondary'] as const;
      for (const key of required) {
        expect(Colors[key]).toMatch(/^#[0-9a-f]{6}$/i);
      }
    });

    it('all values are valid hex colors', () => {
      for (const value of Object.values(Colors)) {
        expect(value).toMatch(/^#[0-9a-fA-F]{3,8}$/);
      }
    });
  });

  describe('Spacing', () => {
    it('has required spacing keys in ascending order', () => {
      expect(Spacing.xs).toBeLessThan(Spacing.sm);
      expect(Spacing.sm).toBeLessThan(Spacing.md);
      expect(Spacing.md).toBeLessThan(Spacing.lg);
      expect(Spacing.lg).toBeLessThan(Spacing.xl);
      expect(Spacing.xl).toBeLessThan(Spacing.xxl);
    });

    it('all values are positive numbers', () => {
      for (const value of Object.values(Spacing)) {
        expect(typeof value).toBe('number');
        expect(value).toBeGreaterThan(0);
      }
    });
  });

  describe('Radius', () => {
    it('has sm < md < lg < xl', () => {
      expect(Radius.sm).toBeLessThan(Radius.md);
      expect(Radius.md).toBeLessThan(Radius.lg);
      expect(Radius.lg).toBeLessThan(Radius.xl);
    });
  });

  describe('Shadow', () => {
    it('sm and md shadows have required shape', () => {
      for (const shadow of [Shadow.sm, Shadow.md]) {
        expect(shadow).toHaveProperty('shadowColor');
        expect(shadow).toHaveProperty('shadowOpacity');
        expect(shadow).toHaveProperty('elevation');
      }
    });

    it('md shadow is stronger than sm', () => {
      expect(Shadow.md.elevation).toBeGreaterThan(Shadow.sm.elevation);
      expect(Shadow.md.shadowOpacity).toBeGreaterThan(Shadow.sm.shadowOpacity);
    });
  });

  describe('Typography', () => {
    it('has all heading and body variants', () => {
      expect(Typography.h1.fontSize).toBeGreaterThan(Typography.h2.fontSize);
      expect(Typography.h2.fontSize).toBeGreaterThan(Typography.h3.fontSize);
      expect(Typography.h3.fontSize).toBeGreaterThanOrEqual(Typography.body.fontSize);
    });

    it('heading variants are bold', () => {
      expect(['700', '800']).toContain(Typography.h1.fontWeight);
      expect(['700', '800']).toContain(Typography.h2.fontWeight);
    });
  });
});
