# Copilot code review instructions — Twitter Bulk Blocker

Guidance for reviewing pull requests in this repository. Write review feedback in
**Japanese** (this project's convention). Keep comments concrete and actionable.

## What this project is

A Python CLI that bulk-blocks Twitter/X users via the GraphQL API (lookup) and REST API
v1.1 (block), backed by SQLite (WAL mode) and a three-layer cache. Code lives in
`twitter_blocker/`; the entry point is `twitter_blocker/__main__.py`.

## Review priorities

### 1. Batch access — no N+1

The most important rule in this codebase. Flag any per-user database or API call placed
inside a loop when a batch method exists.

```python
# Flag this:
for user in users:
    if self.database.is_permanent_failure(user):  # per-user DB call
        ...

# Expected instead:
permanent_failures = self.database.get_permanent_failures_batch(batch_ids, user_format)
for user_id in batch_ids:
    if user_id in permanent_failures:
        continue
```

### 2. Failure classification (`retry.py`)

Errors must be classified correctly, because the class controls whether the API is called
again:

- Permanent (must NOT be retried, must NOT trigger another API call): `suspended`,
  `not_found`, `deactivated`.
- Temporary (retryable): `unavailable`, `rate_limit` (429), `server_error`
  (500/502/503/504).

Flag new error handling that retries a permanent failure, or that treats a temporary
failure as permanent.

### 3. Resource management

- SQLite connections must use a context manager (`with sqlite3.connect(...) as conn:`).
  Flag connections that can leak on an exception path.
- Flag unbounded reads of large tables where a batched/paginated read is expected.

### 4. Security and privacy

- No secrets in the diff: never `cookies.json`, tokens, or auth values committed or
  hard-coded.
- No credentials or personal data written to logs; cookie values must be masked.
- Rate limits must be respected (GraphQL 150 req/15 min, REST 300 blocks/15 min); flag
  changes that could exceed them or remove the inter-request delay (default 1.0s).
- Safety invariants: users you follow / who follow you are skipped, and an
  already-blocked user is never re-blocked. Flag changes that weaken these.

### 5. Conventions

- Python: `snake_case` functions/variables, `PascalCase` classes, 4-space indent, ~100-char
  lines. Code comments and docstrings in Japanese.
- Commit/PR titles follow Conventional Commits with an English description.

## Do not flag (known, intentional patterns)

- Japanese comments, docstrings, and user-facing/error strings — this is the project
  standard, not a defect.
- Emoji in CLI output strings (e.g. `print("✅ …")`) — intentional UX.
- Scripts under `.claude/` (monitoring/ops helpers) — not application code; do not review
  for application conventions.
- Absence of unit tests in a PR: there is no committed test suite and CI does not run one,
  so do not request tests as a blocker (still welcome, but not required).
- Default users-file name `video_misuse_detecteds.json` — intentional project default.
