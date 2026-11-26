# Frontend dependency evidence

Registry: npm registry metadata queried with `npm view` on 2026-11-26. Direct versions are exact-pinned in `package.json`; the resolved transitive graph and integrity hashes are in `package-lock.json` (lockfileVersion 3).

| Package | Direct version | npm registry check |
| --- | ---: | --- |
| `react` | 19.3.1 | `npm view react version` -> 19.3.1 |
| `react-dom` | 19.3.1 | `npm view react-dom version` -> 19.3.1 |
| `vite` | 8.4.0 | `npm view vite version` -> 8.4.0 |
| `typescript` | 7.0.2 | `npm view typescript version` -> 7.0.2 |
| `@types/react` | 19.2.14 | Exact-pinned type declarations; `npm ci` resolves using lock integrity |
| `@types/react-dom` | 19.2.3 | Exact-pinned type declarations; `npm ci` resolves using lock integrity |

All direct packages are named in the docs/03 frontend allowlist. No Next.js, router, chart, CSS framework, or Vite React plugin is installed. The app uses Vite's built-in JSX transform. npm audit on the locked graph reported zero vulnerabilities at install time. Transitive package permission follows the still-pending dependency CR; no transitive package is manually added outside the lock.
