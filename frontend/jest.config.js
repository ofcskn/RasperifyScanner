module.exports = {
  preset: 'jest-expo',
  setupFiles: ['./jest.setup.ts'],
  testMatch: ['**/__tests__/**/*.(test|spec).(ts|tsx)'],
  collectCoverageFrom: [
    'components/**/*.{ts,tsx}',
    'context/**/*.{ts,tsx}',
    'constants/**/*.ts',
  ],
};
