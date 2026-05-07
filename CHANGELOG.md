# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

### Added

- **Internal Skill automation scripts** — Added `create_skill.py`, `update_skill.py`, `get_skill.py`, and `delete_skill.py` for managing JustAI internal Skills through OpenAPI API keys. These scripts support automated test setup and cleanup without requiring `Session-Id`.
- **Internal Skill list filters** — Expanded `list_skills.py` to match the backend Skill query options, including `source`, `enabled`, `category`, `sort_by`, pagination, details, and featured filters.

### Fixed

- **Backend: chat_submit background task executor error** — Fixed a server-side issue where tasks submitted via `chat_submit` would fail with `CurrentThreadExecutor already quit or is broken`. Tasks now execute reliably in the background. No client-side changes needed.

### Changed

- **Python 3.7+ support** — Added `from __future__ import annotations` to support Python 3.7 and above. Previously required Python 3.10+ due to `X | Y` type annotation syntax.
