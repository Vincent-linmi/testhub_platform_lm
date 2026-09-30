module.exports = {
  root: true,
  env: {
    browser: true,
    es2022: true,
  },
  extends: ['eslint:recommended', 'plugin:vue/vue3-essential'],
  parserOptions: {
    ecmaVersion: 'latest',
    sourceType: 'module',
    // Vue SFCs can contain either JavaScript or TypeScript scripts.
    parser: {
      js: 'espree',
      ts: '@typescript-eslint/parser',
    },
  },
  rules: {
    // Existing page names include Login, Register and Layout.
    'vue/multi-word-component-names': 'off',
    // Surface cleanup opportunities without requiring unrelated code changes.
    'no-unused-vars': ['warn', { args: 'none', caughtErrors: 'none', varsIgnorePattern: '^_' }],
    'vue/no-unused-vars': 'warn',
  },
  overrides: [
    {
      files: ['**/*.ts'],
      parser: '@typescript-eslint/parser',
      // Type names are resolved by TypeScript rather than JavaScript's scope rules.
      rules: { 'no-undef': 'off' },
    },
    {
      files: ['*.config.js', '**/*.cjs', '**/*.test.mjs'],
      env: { node: true },
    },
  ],
}
