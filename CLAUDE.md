# CLAUDE.md

Project-specific guidance for Claude Code. Inherits the global `~/.claude/CLAUDE.md`.

## Project overview

Twitter Bulk Blocker is a Python CLI that bulk-blocks users on Twitter/X using cookie
authentication. It uses the GraphQL API (user lookup) and REST API v1.1 (block execution),
a three-layer cache (Lookup / Profile / Relationship), SQLite in WAL mode, and batch
processing to stay within rate limits. It runs standalone or in Docker.

## Development commands

```bash
# Syntax check for all modules (the main local quality gate; there is no committed test suite)
python3 -m py_compile twitter_blocker/*.py

# Run (default = test mode, first few users only)
python3 -m twitter_blocker                       # dry test run
python3 -m twitter_blocker --stats               # show statistics only
python3 -m twitter_blocker --all                 # full run
python3 -m twitter_blocker --all --auto-retry    # full run + retry pass
python3 -m twitter_blocker --test-user <name> --debug   # debug a single user
python3 -m twitter_blocker --debug-errors        # inspect stored error samples
python3 -m twitter_blocker --version             # print version

# Docker
docker build -t twitter-blocker .
docker run --rm -v ./data:/data twitter-blocker --stats
```

`black`, `flake8`, `mypy`, and `pytest` are installed in the Copilot dev environment
(`.github/workflows/copilot-setup-steps.yml`) but are **not** enforced by CI and there are
no committed test files. Do not claim tests pass; verify changes by running the CLI against
a single user in `--debug` mode.

### Key CLI defaults (see `twitter_blocker/__main__.py`)

- `--users-file` default: `video_misuse_detecteds.json` (env `TWITTER_USERS_FILE`)
- `--cache-dir` default: `/data/cache` (env `CACHE_DIR`)
- `--delay` default: `1.0` seconds between requests
- Header flags: `--disable-header-enhancement`, `--enable-forwarded-for`

## Architecture

```
twitter_blocker/
├── __main__.py            # CLI entry point (argparse)
├── api.py                 # Twitter GraphQL/REST client + 3-layer cache
├── database.py            # SQLite (WAL) + permanent-failure cache + batch reads
├── manager.py             # Workflow / batch / session control (BulkBlockManager)
├── config.py              # Env + CLI + default config, schema, cookie handling
├── retry.py               # Permanent vs. temporary failure classification
├── stats.py               # Statistics / analysis / reporting
├── version.py             # Version resolution (git → env → .app-version → "development")
├── error_analytics.py     # Error aggregation and analysis
├── performance_monitor.py # Throughput / cache-efficiency monitoring
└── user_status_monitor.py # Account status tracking
```

## Coding conventions

- Python: `snake_case` for functions/variables, `PascalCase` for classes, 4-space indent,
  ~100-char lines. Docstrings in Japanese.
- **Always batch DB/API access; never introduce N+1 patterns.**

  ```python
  # Recommended: batch fetch + pre-check
  permanent_failures = self.database.get_permanent_failures_batch(batch_ids, user_format)
  for user_id in batch_ids:
      if user_id in permanent_failures:
          continue  # skip API call

  # Avoid: per-user DB call inside a loop (N+1)
  for user in users:
      if self.database.is_permanent_failure(user):
          continue
  ```

- Manage SQLite connections with a context manager (`with sqlite3.connect(...) as conn:`).
- Pre-check permanent failures to avoid wasted API calls.
- Monitoring/utility scripts (e.g. `.claude/commands/check-cinnamon`): keep a **single**
  version, prioritize correctness over speed, and switch behavior via CLI options rather
  than creating "fast"/"optimized" variants.

### Error classification (`retry.py`)

- Permanent (do not call the API, not retried): `suspended`, `not_found`, `deactivated`.
- Temporary (retried): `unavailable`, `rate_limit` (429), `server_error` (500/502/503/504).
- Auth errors: reload cookies and run the recovery flow.

## Communication and commits

- Conversation, code comments, and error messages: **Japanese**. Insert a half-width space
  between Japanese and alphanumeric characters (e.g. `Twitter API v2 の仕様`).
- Commits: [Conventional Commits](https://www.conventionalcommits.org/) —
  `<type>(<scope>): <description>` with the **description in English**.
- Branches: [Conventional Branch](https://conventional-branch.github.io) short form
  (`feat/…`, `fix/…`).
- PR title in English (Conventional Commits); PR body and review comments in Japanese.

## Decision records

When making a technical decision, record: (1) the decision, (2) alternatives considered,
(3) why the alternatives were rejected, (4) assumptions and uncertainties, (5) whether
another agent should review it. Do not present assumptions as facts.

## Repository-specific rules

- **Prefer adding commits to an existing open PR** over opening a new one when the change
  touches the same files, the same functional area, or a related bug fix. Only create a new
  PR for a fully independent feature. This avoids merge conflicts and keeps review coherent.
- **Cinnamon production server access**: connect only with `ssh Cinnamon` (the SSH config
  alias). Do not use `ssh ope@cinnamon.oimo.io` or the raw IP — both fail. See
  `.claude/cinnamon-connection.md`.

### Operational targets and limits

- Throughput target ≥ 50 users/sec; cache hit rate ≥ 80%; batch size 50; cache TTL 30 days.
- GraphQL rate limit: 150 req / 15 min. REST rate limit: 300 blocks / 15 min.

## Security

- Never commit `cookies.json` or any credential; keep them in the data dir (git-ignored).
- Never log credentials or personal data; mask cookie values in output.
- Respect rate limits, skip users you follow / who follow you, and never re-block a user
  already blocked.

## Detailed docs

Deeper knowledge lives under `.claude/` — read the relevant file when the situation applies:

- `guides/` — API patterns, performance, error handling, caching strategy.
- `patterns/` — recommended patterns, anti-patterns, code-review checklist.
- `workflows/` — issue handling, emergency response.
- `operations/cinnamon-server.md`, `troubleshooting/common-issues.md`, `quality/testing-guide.md`.
- `commands/` — Cinnamon monitoring and release commands (invoked as Claude Code slash commands).

## Documentation update rules

- Adding/renaming a CLI flag → update the "Development commands" section here and `README.md`.
- Adding/removing a module under `twitter_blocker/` → update the "Architecture" section.
- Changing rate limits, batch size, or performance targets → update "Operational targets".
