# ABHEDYA console

React and Vite console for the ABHEDYA API. The UI uses real API responses, the API's secure session cookie and CSRF token, and the authenticated activity SSE stream. It contains no seeded credentials or simulated environment, job, or activity data.

## Local frontend development

1. In `web/`, install the exact lockfile with `npm ci` after reviewing `DEPENDENCIES.md` and the repository's dependency approval status.
2. Start the real ABHEDYA API on `127.0.0.1:8000` with its configured database and secrets.
3. Run `npm run dev` and open the Vite URL. The server binds to `127.0.0.1` and proxies `/api/*` to the API on port 8000.

The API sets a `Secure` session cookie. Use HTTPS for a browser origin that does not treat loopback as a secure context. After login the console calls `/auth/me` before entering the authenticated view; a blocked cookie therefore produces an API error instead of a misleading signed-in screen. Refreshing the page restores the session only when the API accepts the actual cookie.

`npm run build` runs strict TypeScript compilation and creates the static bundle in `dist/`. The console does not fetch fonts or other runtime assets from a public CDN. Production TLS and static serving belong to the planned `proxy` service.

## Implemented UI behavior

- Login, logout and session restoration through `/auth/login`, `/auth/logout` and `/auth/me`.
- API health status, environment list/create/stop/delete/exec, jobs, activity list and admin overview from implemented API routes.
- Activity updates from the API's authenticated SSE `/stream` endpoint, with the list endpoint refreshed as part of regular console refreshes.
- Configured isolation runtime and degraded-mode indication are taken from the API overview response; the UI labels host proof as pending.
- File-analysis and AI-scan submission are not offered while their required runtime targets remain unavailable or unapproved.

## Integration status

The current repository Compose file defines PostgreSQL only. It does not yet start the API, runner, notary or proxy, so a complete login-to-environment journey is not currently available from this checkout. The Vite frontend still builds locally; API-dependent views require a real, configured API. Provisioning and command execution require a real runner and approved local sandbox images. A successful frontend build is not host acceptance or an objective pass.
