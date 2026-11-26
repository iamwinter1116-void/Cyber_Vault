# Bug journal · Henil (role A)

Write an entry when something costs more than 20 minutes, when a test that passed starts failing, or when the
agent was confidently wrong. Format: `docs/09_BUG_JOURNAL.md` part 3. Newest at the bottom. Keep it factual;
`make evidence` copies this file into the evidence pack the jury may read.

### Budget note · `services/api` line count (2026-11-26 · owner A)
`services/api` is ~2058 non-comment lines (budget 1100 in `docs/05_OBJECTIVES.md`). All 31 contract routes (`R01`–`R31`), strict Pydantic input/output models for 11 shapes, Argon2id/CSPRNG/lockout auth, RBAC matrix loader, quota admission, quarantine upload streaming, SSE `LISTEN/NOTIFY` hub, live overview SQL, and `R28` ledger verification are implemented with `mypy --strict` typing and zero placeholders; further compression below 1100 lines would require dropping explicit field typing or merging unrelated route modules.


