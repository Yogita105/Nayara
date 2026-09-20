const js = require("@eslint/js");
const globals = require("globals");
const react = require("eslint-plugin-react");
const reactHooks = require("eslint-plugin-react-hooks");
const jsxA11y = require("eslint-plugin-jsx-a11y");

module.exports = [
  {
    ignores: ["build/**", "node_modules/**", "public/**", "*.config.js"],
  },
  js.configs.recommended,
  {
    files: ["src/**/*.{js,jsx}"],
    languageOptions: {
      ecmaVersion: 2022,
      sourceType: "module",
      globals: { ...globals.browser, ...globals.jest, process: "readonly" },
      parserOptions: { ecmaFeatures: { jsx: true } },
    },
    plugins: {
      react,
      "react-hooks": reactHooks,
      "jsx-a11y": jsxA11y,
    },
    settings: { react: { version: "detect" } },
    rules: {
      ...react.configs.flat.recommended.rules,
      ...reactHooks.configs.recommended.rules,
      // The JSX transform makes the React import unnecessary, and prop types
      // duplicate what the components already document by usage.
      "react/react-in-jsx-scope": "off",
      "react/prop-types": "off",
      // Apostrophes and quotation marks belong in customer-facing copy;
      // escaping them makes the text harder to read and to edit.
      "react/no-unescaped-entities": "off",
      // cmdk marks its own wrapper with this attribute.
      "react/no-unknown-property": ["error", { ignore: ["cmdk-input-wrapper"] }],
      "no-unused-vars": ["error", { argsIgnorePattern: "^_", varsIgnorePattern: "^_" }],
    },
  },
];
