# Repository Guidelines

## Project Structure & Module Organization
This repository is currently minimal and does not yet include application source, test, or deployment files. Keep future additions organized from the start:

- `src/`: application logic and integrations
- `tests/`: automated tests mirroring `src/`
- `public/` or `assets/`: static files if the app serves images or feeds
- `config/`: environment-specific settings that are safe to commit

Example layout:
`src/collector/`, `src/api/`, `tests/collector.test.*`

## Build, Test, and Development Commands
No package manifest or task runner is committed yet, so there are no canonical local commands today. When adding tooling, expose a small standard command set and document it in the project root:

- `npm install`: install dependencies
- `npm run dev`: start local development server
- `npm test`: run the full test suite
- `npm run lint`: run formatting and lint checks
- `npm run build`: create the production build

Prefer predictable script names over custom aliases.

## Coding Style & Naming Conventions
Use 2-space indentation for JSON, YAML, and Markdown. Follow the default formatter for the primary language once one is introduced. Naming should stay consistent:

- directories and utility modules: `kebab-case`
- variables and functions: `camelCase`
- classes and React components: `PascalCase`
- environment variables: `UPPER_SNAKE_CASE`

Keep modules small and single-purpose. Avoid mixing feed collection, parsing, and presentation logic in one file.

## Testing Guidelines
Add tests alongside each feature area under `tests/` or in colocated `*.test.*` files. Name tests after behavior, for example `collector.fetches-latest-items.test.ts`. Cover parsing edge cases, network failures, and duplicate-item handling. Run tests locally before opening a PR.

## Commit & Pull Request Guidelines
This directory is not currently a Git repository, so no local commit history is available to infer conventions. Use Conventional Commits going forward, for example `feat: add rss polling job` or `fix: handle empty feed response`.

Pull requests should include:

- a short summary of the change
- linked issue or task ID when applicable
- setup or rollout notes for config changes
- screenshots or sample payloads if UI or API output changes

## Security & Configuration Tips
Do not commit secrets. Store tokens and API keys in environment variables such as `.env.local`, and provide a sanitized `.env.example` when configuration becomes necessary.
